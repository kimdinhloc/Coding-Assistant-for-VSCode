import asyncio
import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.context_engine import build_context
from app.prompting.fim_prompt import build_fim_prompt

router = APIRouter()

class CompletionRequest(BaseModel):
    prefix: str
    suffix: str
    language: str = "python"

async def fake_vllm_stream(prompt: str):
    sample = "\n# suggested completion\npass\n"
    for ch in sample:
        await asyncio.sleep(0.005)
        yield ch

@router.post('/stream')
async def stream_completion(req: CompletionRequest, request: Request):
    context = await build_context(req.prefix, req.suffix, req.language)
    prompt = build_fim_prompt(req.prefix, req.suffix, context)

    async def event_gen():
      async for tok in fake_vllm_stream(prompt):
        if await request.is_disconnected():
          break
        yield f"data: {json.dumps({'type':'token','token':tok})}\n\n"
      yield f"data: {json.dumps({'type':'done'})}\n\n"

    return StreamingResponse(event_gen(), media_type='text/event-stream')
