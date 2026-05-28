"""Lightweight per-IP token bucket middleware for FastAPI."""
import time
from typing import Dict, List

from fastapi import HTTPException, Request

from core.config import RATE_LIMIT_PER_MINUTE

_IP_REQUEST_LOGS: Dict[str, List[float]] = {}


async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    bucket = _IP_REQUEST_LOGS.setdefault(client_ip, [])
    bucket[:] = [t for t in bucket if now - t < 60]

    if len(bucket) >= RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Too many requests. Rate limit exceeded.")

    bucket.append(now)
    return await call_next(request)
