# Testing & Implementation Roadmap (Copilot/Cursor/Continue-style)

## PHẦN 13 — TESTING

### 1) Unit tests
```text
[Prompt Engine] [Context Engine] [Parser] [Retrieval] [RateLimit/Auth]
      |               |             |         |          |
      +--------------------------- pytest ----------------+
```
- Validate FIM prompt formatting, cache hits, compression behavior.
- Validate context truncation/ranking/import extraction.
- Validate parser symbol extraction + incremental cache path.
- Validate retrieval chunking/index/search ranking.

### 2) Integration tests
```text
TestClient -> FastAPI middleware -> /v1/completions/stream -> SSE frames
```
- Health/metrics endpoint checks.
- SSE stream contract checks (`token`, `done`).
- Rate-limit path checks (`429`).

### 3) Load tests
```text
Virtual Users -> API Gateway -> Queue -> vLLM workers
```
- Use k6/Locust for 100-2k concurrent requests.
- Track queue depth, p95 first-token, cancellation rate, cache-hit rate.

### 4) Streaming tests
- Validate SSE parser stability with long streams.
- Validate reconnect behavior and sequence IDs.
- Validate frontend cancellation → backend stop path.

### 5) Latency benchmark
- Benchmark first token, full completion latency.
- Split by cache-hit/miss and prefix reuse.
- Baseline target: p95 first token <150ms in GPU warm path.

---

## PHẦN 14 — IMPLEMENTATION ROADMAP

### Phase 1 — Minimal autocomplete
- FastAPI endpoint + VSCode inline provider + FIM template.
- Static fake stream; local-only.

### Phase 2 — Streaming
- SSE protocol (`token`, `heartbeat`, `done`) + cancellation propagation.
- Debounce/throttle + in-flight cancellation in extension.

### Phase 3 — AST awareness
- Tree-sitter parser manager with incremental parsing.
- Symbol/scope extraction used by context builder.

### Phase 4 — Retrieval
- LanceDB repo indexing + chunk overlap + embedding pipeline.
- Hybrid ranking + context fusion with budget manager.

### Phase 5 — Production scaling
- vLLM GPU deployment + speculative decoding + prefix cache.
- K8s autoscaling, observability stack, auth/quota/multi-tenant isolation.

## Folder structure
```text
backend/
  app/
    api/
    prompting/
    services/
    parsing/
    retrieval/
    inference/
    core/
    observability/
  tests/
docs/
deploy/
  k8s/
vscode-extension/
```

## Example request/response (SSE)
Request:
```json
POST /v1/completions/stream
{"prefix":"def add(a,b):\n    ","suffix":"","language":"python","user_id":"u1","tenant_id":"acme"}
```
Response frames:
```text
event: token
data: {"type":"token","request_id":"...","seq":0,"token":"ret"}

event: done
data: {"type":"done","request_id":"..."}
```
