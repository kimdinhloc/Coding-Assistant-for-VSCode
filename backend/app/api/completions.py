from __future__ import annotations

import asyncio
import json
import time
import uuid
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.rate_limit import RATE_LIMITER
from app.inference.vllm_client import GenerationConfig, VLLMClient
from app.prompting.fim_prompt import build_fim_prompt, hash_prompt_key
from app.retrieval.lancedb_store import LanceDBStore
from app.services.context_engine import build_context
from app.services.queue_manager import REQUEST_QUEUE
from app.services.request_lifecycle import LIFECYCLE
from app.observability.metrics import METRICS
from app.observability.logging import log_event

router = APIRouter()
store = LanceDBStore()
vllm = VLLMClient()
RECENT_REQUESTS: dict[str, str] = {}
MAX_DEDUP_KEYS = 5000


class CompletionRequest(BaseModel):
    prefix: str = Field(min_length=1)
    suffix: str = ""
    language: str = "python"
    max_tokens: int = 128
    user_id: str = "anonymous"
    tenant_id: str = "default"
    priority: int = 10
    temperature: float = 0.2
    top_p: float = 0.95
    repetition_penalty: float = 1.05


@router.post('/stream')
async def stream_completion(req: CompletionRequest, request: Request):
    t0 = time.time()
    if not RATE_LIMITER.allow(f"{req.tenant_id}:{req.user_id}"):
        raise HTTPException(status_code=429, detail="rate limit exceeded")

    request_id = str(uuid.uuid4())
    request_hash = hash_prompt_key(req.language, req.prefix[-512:], req.suffix[:256], req.tenant_id)
    prev = RECENT_REQUESTS.get(request_hash)
    if prev:
        LIFECYCLE.cancel(prev)  # aggressive dedup cancellation
    RECENT_REQUESTS[request_hash] = request_id
    if len(RECENT_REQUESTS) > MAX_DEDUP_KEYS:
        oldest_key = next(iter(RECENT_REQUESTS))
        RECENT_REQUESTS.pop(oldest_key, None)

    LIFECYCLE.begin(request_id, req.user_id)
    await REQUEST_QUEUE.put(request_id, priority=req.priority)

    retrieved = await store.search(req.prefix[-300:], req.language, k=4)
    context = await build_context(req.prefix, req.suffix, req.language, retrieved_chunks=retrieved)
    prompt_payload = build_fim_prompt(req.prefix, req.suffix, context, req.language)

    gen_cfg = GenerationConfig(
        temperature=req.temperature,
        top_p=req.top_p,
        repetition_penalty=req.repetition_penalty,
        max_tokens=req.max_tokens,
        stop=tuple(prompt_payload["stop"]),
        use_speculative=True,
    )

    async def event_gen():
        seq = 0
        buffer = []
        token_count = 0
        try:
            async with asyncio.timeout(30):
                async for tok in vllm.stream_generate(prompt_payload["prompt"], gen_cfg):
                    if await request.is_disconnected() or LIFECYCLE.is_cancelled(request_id):
                        METRICS.inc("cancelled")
                        return
                    buffer.append(tok)
                    token_count += 1
                    if len(buffer) < 3:
                        continue
                    payload = {"type": "token", "request_id": request_id, "seq": seq, "token": "".join(buffer)}
                    yield f"id: {seq}\nevent: token\ndata: {json.dumps(payload)}\n\n"
                    seq += 1
                    buffer.clear()
            if buffer:
                payload = {"type": "token", "request_id": request_id, "seq": seq, "token": "".join(buffer)}
                yield f"id: {seq}\nevent: token\ndata: {json.dumps(payload)}\n\n"
            yield f"event: done\ndata: {json.dumps({'type': 'done', 'request_id': request_id, 'tokens_out': token_count})}\n\n"
            METRICS.inc("requests_ok")
            METRICS.inc("tokens_out", token_count)
        except TimeoutError:
            METRICS.inc("timeout")
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'reason': 'timeout', 'request_id': request_id})}\n\n"
        finally:
            latency_ms = (time.time() - t0) * 1000
            METRICS.observe("request_latency_ms", latency_ms)
            log_event("completion_done", request_id=request_id, tenant_id=req.tenant_id, latency_ms=latency_ms)
            LIFECYCLE.end(request_id)

    headers = {"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    return StreamingResponse(event_gen(), media_type='text/event-stream', headers=headers)
