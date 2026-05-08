# Coding Assistant for VSCode

Production-grade AI autocomplete scaffold (Copilot/Cursor-style):
- Frontend: VSCode Extension + InlineCompletion API
- Backend: FastAPI async SSE
- Inference target: vLLM OpenAI-compatible endpoint
- Model target: Qwen2.5-Coder (FIM)
- Retrieval target: LanceDB
- Parsing target: tree-sitter

## Documents
- Detailed architecture and implementation notes: `docs/architecture.md`

## Quick start
```bash
uvicorn app.main:app --app-dir backend --reload --port 8000
```

## Current status
This repository now includes a runnable end-to-end scaffold for streaming inline completion, plus production architecture guidance. Replace placeholder retrieval/parser/vLLM modules with full integrations.
