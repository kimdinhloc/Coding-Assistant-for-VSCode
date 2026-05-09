# Coding Assistant for VSCode

Production-grade AI autocomplete scaffold theo hướng **Copilot / Cursor / Continue**.

## 1) Mục tiêu hệ thống
Hệ thống này tập trung vào:
- Inline autocomplete độ trễ thấp (first-token ưu tiên)
- Streaming realtime bằng SSE
- Context-aware + AST-aware + repo-aware
- Kiến trúc tách lớp để scale production

## 2) Stack kiến trúc
- **Frontend:** VSCode Extension (TypeScript, InlineCompletion API)
- **Backend:** FastAPI (Python 3.12+, async)
- **Inference:** vLLM (OpenAI-compatible)
- **Model:** Qwen2.5-Coder (FIM prompting)
- **Retrieval:** LanceDB
- **Parser:** tree-sitter (hiện tại có parser facade + incremental contract)
- **Streaming:** SSE

## 3) Repository structure
```text
backend/
  app/
    api/                # SSE completion endpoints
    core/               # auth, rate limiting
    inference/          # vLLM client wrapper
    observability/      # metrics + structured logs
    parsing/            # parser manager / symbol extraction
    prompting/          # FIM prompt builder + prompt cache
    retrieval/          # LanceDB-like retrieval/indexing adapter
    services/           # context engine, lifecycle, queue
  tests/                # unit/integration/streaming/latency tests

deploy/
  backend.Dockerfile
  vllm-docker-compose.yml
  k8s/
    autocomplete.yaml
    observability.yaml

docs/
  architecture.md
  review-and-test-report.md
  testing-roadmap.md

vscode-extension/
  src/
    extension.ts
    provider.ts
    sseClient.ts
  package-extension.sh
```

## 4) Chạy local nhanh
### Backend dev server
```bash
uvicorn app.main:app --app-dir backend --reload --port 8000
```

### Test
```bash
PYTHONPATH=backend python -m pytest backend/tests -q
```

### Compile sanity
```bash
PYTHONPATH=backend python -m compileall backend/app
```

## 5) API chính
### `POST /v1/completions/stream`
- Content-Type: `application/json`
- Trả về: `text/event-stream`
- Request fields chính:
  - `prefix`, `suffix`, `language`
  - `user_id`, `tenant_id`
  - `max_tokens`, `temperature`, `top_p`, `repetition_penalty`

Ví dụ request:
```json
{
  "prefix": "def add(a, b):\n    ",
  "suffix": "\n",
  "language": "python",
  "user_id": "u1",
  "tenant_id": "acme",
  "max_tokens": 64
}
```

Ví dụ response frames:
```text
event: token
data: {"type":"token","request_id":"...","seq":0,"token":"ret"}

event: done
data: {"type":"done","request_id":"...","tokens_out":42}
```

## 6) Production features đã có trong scaffold
- Debounce/throttle/cancellation ở extension
- SSE streaming + heartbeat/error path
- Prompt cache + context compression + budget manager
- Request lifecycle tracking + aggressive dedup cancellation
- Token bucket rate limiting + API key/JWT hooks
- Metrics endpoint (`/metrics`) + structured logging
- Docker/K8s deployment skeleton cho API + vLLM + observability

## 7) Lưu ý quan trọng
Đây là **production-oriented scaffold**. Một số thành phần hiện là adapter/dev implementation để dễ phát triển độc lập:
- vLLM client hiện có fake stream path để local test không cần GPU
- tree-sitter hiện dùng parser facade (regex fallback) với interface incremental
- LanceDB hiện dùng in-memory/dev adapter theo contract indexing/search

## 8) Tài liệu chi tiết
- Kiến trúc tổng thể: `docs/architecture.md`
- Báo cáo review/test: `docs/review-and-test-report.md`
- Testing strategy + implementation phases: `docs/testing-roadmap.md`
