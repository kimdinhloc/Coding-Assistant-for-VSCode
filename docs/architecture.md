# Production-Grade AI Autocomplete Architecture (Copilot/Cursor-style)

## 1. High-level architecture

```text
┌───────────────────────────── VSCode Extension (TypeScript) ─────────────────────────────┐
│ InlineCompletionProvider | Debounce | Cancellation | Prefix Cache | Ghost Text Renderer  │
└──────────────────────────────┬────────────────────────────────────────────────────────────┘
                               │ SSE POST /v1/completions/stream
                               ▼
┌────────────────────────────── FastAPI API Layer (Async) ─────────────────────────────────┐
│ Auth/Rate Limit | Request Queue | Cancellation Registry | SSE Writer | Metrics/Tracing   │
└───────────────┬─────────────────────────────┬──────────────────────────────────────────────┘
                │                             │
                ▼                             ▼
      Context Engine                   Retrieval Service (LanceDB)
 (prefix/suffix + AST + tabs)      (repo chunk index + semantic kNN)
                │                             │
                └──────────── prompt fusion ──┘
                               ▼
                       vLLM Inference Layer
                 (Qwen2.5-Coder FIM, token streaming)
                               ▼
                        SSE token frames to IDE
```

**Latency budget (target p95 first-token < 150ms):**
- IDE request prep: 5–15ms
- API + auth + queue: 5–20ms
- Context + retrieval: 20–50ms
- vLLM first token: 40–70ms
- SSE delivery/render: 5–15ms

## 2. Module boundaries
- **Frontend modules**: `extension.ts` (activation), `provider.ts` (inline completion lifecycle), `sseClient.ts` (stream parser + cancellation).
- **Backend API**: request validation, SSE framing (`token`, `done`, `error`), disconnect detection.
- **Context engine**: token/char budgeting, relevance ranking, context compression.
- **Retrieval service**: embedding search over LanceDB, chunk top-k selection.
- **Parser service**: tree-sitter incremental parse cache, symbol extraction.
- **Inference service**: FIM prompt assembly + vLLM stream orchestration.

Dependency graph:
`API -> (Context Engine -> Parser + Retrieval) -> Prompt Builder -> vLLM Client -> SSE`

## 3. Request lifecycle
1. User types in editor; debounce window opens (e.g., 60ms).
2. Provider cancels previous in-flight request for same file.
3. Prefix/suffix + language sent to backend streaming endpoint.
4. Backend retrieves repo chunks + builds compressed context.
5. FIM prompt is assembled for Qwen2.5-Coder.
6. vLLM streams tokens; backend emits SSE frames.
7. Extension incrementally renders ghost text.
8. On cursor move/edit, cancellation propagates IDE → API → vLLM stream.

## 4. Bottleneck analysis
- **Context overgrowth**: solved with strict budget and ranking.
- **Retrieval latency spikes**: async indexing + warmed vector cache.
- **GPU queue contention**: split short autocomplete queue from long chat queue.
- **SSE buffering by proxy**: send `X-Accel-Buffering: no`, disable reverse-proxy buffering.

## 5. Deployment architecture (Docker/K8s)
- **Pods**:
  - `api-gateway` Deployment (CPU)
  - `retrieval-indexer` Deployment (CPU/background)
  - `vllm-inference` Deployment/StatefulSet (GPU)
- **Autoscaling**:
  - HPA by request rate + latency for API
  - KEDA/queue-based scaler for inference queue depth
- **GPU scheduling**:
  - Node pool with taints/tolerations
  - One model per GPU group, optional MIG partition
- **HA strategy**:
  - ≥2 API replicas across zones
  - Readiness probes + PDB + rolling update
  - Persistent LanceDB volume snapshot/backup

## 6. Tradeoffs
- Higher retrieval `k` increases quality but adds latency and token cost.
- Rich AST extraction improves relevance but costs CPU; run incrementally and cache by file version.
- Aggressive cancellation reduces waste but may drop useful completions when user pauses briefly.
