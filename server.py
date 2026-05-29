"""FastAPI entry point. Run with: `uvicorn server:app --reload`."""
import logging
import time
from typing import Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Server")

from api import analytics_router, api_router, webhook_router  # noqa: E402
from core.rate_limit import rate_limit_middleware  # noqa: E402
from core.sandbox import safe_sandbox_compile  # noqa: E402

app = FastAPI(
    title="Auspex",
    description="Reads the omens in every commit. Multi-agent PR review on LangGraph + Groq.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(rate_limit_middleware)

app.include_router(webhook_router)
app.include_router(api_router)
app.include_router(analytics_router)


@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Auspex API",
        "docs": "/docs",
        "local_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


@app.post("/api/sandbox/validate")
async def validate_in_sandbox(payload: Dict[str, str]):
    code = payload.get("code", "")
    if not code:
        raise HTTPException(status_code=400, detail="Missing code string to validate.")
    return safe_sandbox_compile(code)
