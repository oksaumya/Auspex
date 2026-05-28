"""Thin HTTP client around the FastAPI backend used by every dashboard page."""
import os
from typing import Any, Dict, List, Optional

import requests

BASE_URL = os.getenv("REVIEWER_API_URL", "http://127.0.0.1:8000")
API_URL = f"{BASE_URL}/api"


def _get(path: str, timeout: int = 4) -> Optional[Any]:
    try:
        res = requests.get(f"{API_URL}{path}", timeout=timeout)
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None


def _post(path: str, body: Dict[str, Any], timeout: int = 4) -> Optional[Any]:
    try:
        res = requests.post(f"{API_URL}{path}", json=body, timeout=timeout)
        if res.status_code in (200, 201, 202):
            return res.json()
    except Exception:
        return None
    return None


def server_health() -> Optional[Dict[str, Any]]:
    try:
        res = requests.get(f"{BASE_URL}/", timeout=2)
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None


def list_sessions() -> List[str]:
    data = _get("/sessions")
    return data if isinstance(data, list) else ["demo-101"]


def get_session(pr_id: str) -> Optional[Dict[str, Any]]:
    return _get(f"/session/{pr_id}")


def submit_decision(pr_id: str, fix_id: str, decision: str) -> bool:
    return _post(f"/session/{pr_id}/decide", {"fix_id": fix_id, "decision": decision}) is not None


def resume_session(pr_id: str) -> bool:
    return _post(f"/session/{pr_id}/resume", {}) is not None


def analytics_summary() -> Optional[Dict[str, Any]]:
    return _get("/analytics/summary")
