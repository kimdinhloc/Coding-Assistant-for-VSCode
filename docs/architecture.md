# AI Autocomplete System (Copilot/Cursor-style)

## 1) High-level architecture

```text
┌─────────────────────── VSCode Extension (TS) ────────────────────────┐
│ InlineCompletionProvider                                               │
│ Debounce + Cancellation + Cache + Partial Accept                      │
└───────────────┬───────────────────────────────┬───────────────────────┘
                │ SSE (text/event-stream)       │ telemetry
                ▼                               ▼
       ┌────────────────────────── FastAPI Gateway ──────────────────────────┐
       │ /v1/completions/stream (SSE)                                        │
       │ Rate limit | Auth | Queue | Cancellation registry | Tracing         │
       └───────────────┬───────────────────────────────────────┬──────────────┘
                       │                                       │
                       ▼                                       ▼
              Context Engine                            Retrieval Engine
      (nearby/open tabs/AST/symbols/FIM)              (LanceDB semantic kNN)
                       │                                       │
                       └────────────── prompt fusion ──────────┘
                                      ▼
                            vLLM (OpenAI-compatible)
                     Qwen2.5-Coder with FIM streaming output
```

## 2) Detailed component architecture
- VSCode extension: inline completion lifecycle, debounce(40-80ms), cancel previous request on cursor move/typing.
- Context engine: weighted relevance scoring with token budget.
- tree-sitter parser manager: incremental parse tree cache by file URI + version.
- Retrieval: LanceDB index per repo, async background incremental indexing.
- Backend API: SSE chunk writer + cancellation propagation.
- Inference: vLLM chat/completions endpoint with FIM prompt template.

## 3) Data flow
```text
Keystroke
  -> provider.provideInlineCompletionItems()
  -> build local context (prefix/suffix/open tabs/symbols)
  -> POST /v1/completions/stream (SSE)
  -> backend enriches with retrieval + AST context
  -> build FIM prompt
  -> stream tokens from vLLM
  -> SSE frames: token/done/error
  -> extension incrementally renders ghost text
```

## 4) Folder structure
```text
vscode-extension/src/
  extension.ts
  provider.ts
  sseClient.ts
backend/app/
  main.py
  api/completions.py
  core/config.py
  services/cancellation.py
  services/context_engine.py
  retrieval/lancedb_store.py
  parsing/tree_sitter_manager.py
  prompting/fim_prompt.py
docs/architecture.md
```

## 5) Performance targets
- First token p95 < 150ms (warm path).
- Full cancellation propagation < 30ms.
- Prompt budget: 2k-4k tokens for autocomplete.

## 6) Deployment
- vLLM on GPU pool; FastAPI autoscaled separately.
- Redis (optional) for distributed cancellation + rate limit.
- Observability: OTEL traces + Prometheus metrics.

## 7) Tradeoffs
- Larger retrieval-k improves accuracy but increases prompt latency.
- Deep AST analysis improves relevance but costs CPU; apply budgeted extraction.
