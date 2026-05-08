from fastapi import FastAPI
from app.api.completions import router as completions_router

app = FastAPI(title="AI Autocomplete Backend")
app.include_router(completions_router, prefix="/v1/completions", tags=["completions"])
