from __future__ import annotations

import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.completions import router as completions_router
from app.core.auth import decode_jwt, validate_api_key
from app.observability.metrics import METRICS

app = FastAPI(title="Autocomplete API", version="0.3.0")


@app.middleware("http")
async def auth_and_timing_middleware(request: Request, call_next):
    if request.url.path not in {"/healthz", "/metrics"}:
        api_key = request.headers.get("x-api-key")
        authz = request.headers.get("authorization", "")
        jwt_token = authz.replace("Bearer ", "") if authz.startswith("Bearer ") else None
        if not (validate_api_key(api_key) or decode_jwt(jwt_token)):
            return JSONResponse({"detail": "unauthorized"}, status_code=401)

    started = time.time()
    response = await call_next(request)
    elapsed = (time.time() - started) * 1000
    response.headers["X-Process-Time-Ms"] = str(int(elapsed))
    METRICS.observe("http_request_ms", elapsed)
    return response


@app.get("/healthz")
async def healthz():
    return JSONResponse({"status": "ok"})


@app.get("/metrics")
async def metrics():
    return JSONResponse(METRICS.snapshot())


app.include_router(completions_router, prefix="/v1/completions", tags=["completions"])
