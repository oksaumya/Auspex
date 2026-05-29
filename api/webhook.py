"""GitHub PR webhook endpoint with HMAC signature verification."""
import hashlib
import hmac
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from api._github import fetch_pr_files
from api.routes import active_pr_ids
from core.config import GITHUB_WEBHOOK_SECRET
from graph import get_graph

logger = logging.getLogger("Webhook")
router = APIRouter()


def verify_signature(payload: bytes, signature: str) -> bool:
    if not GITHUB_WEBHOOK_SECRET:
        logger.warning("GITHUB_WEBHOOK_SECRET not configured. Skipping HMAC verification.")
        return True
    if not signature:
        return False
    parts = signature.split("=")
    if len(parts) != 2 or parts[0] != "sha256":
        return False
    expected = hmac.new(
        key=GITHUB_WEBHOOK_SECRET.encode(),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(parts[1], expected)


def execute_review_pipeline(pr_id: str, repo_name: str, files: list, pr_title: str, pr_body: str) -> None:
    try:
        graph = get_graph()
        config = {"configurable": {"thread_id": pr_id}}
        initial_state = {
            "pr_id": pr_id,
            "repo_name": repo_name,
            "commit_sha": "web-hook-sha-9876",
            "pr_title": pr_title,
            "pr_body": pr_body,
            "changed_files": files,
            "retrieved_context": {},
            "issues": [],
            "fixes": [],
            "evaluations": {},
            "human_decisions": {},
            "applied_fixes": [],
            "status": "pending",
            "tokens_used": 0,
            "cost": 0.0,
            "error": None,
            "metadata": {},
        }
        logger.info("Running LangGraph for webhook PR %s in repo %s", pr_id, repo_name)
        graph.invoke(initial_state, config)
        logger.info("Graph paused at interrupt for PR %s.", pr_id)
    except Exception as exc:
        logger.error("Error executing webhook review pipeline: %s", exc)


@router.post("/webhook/github")
async def github_webhook_handler(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None),
):
    body_bytes = await request.body()

    if not verify_signature(body_bytes, x_hub_signature_256 or ""):
        logger.error("GitHub webhook signature verification failed.")
        raise HTTPException(status_code=401, detail="Invalid webhook HMAC signature.")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    action = payload.get("action")
    pull_request = payload.get("pull_request")
    if not pull_request or action not in ("opened", "synchronize", "reopened"):
        logger.info("Ignoring non-PR action: %s", action)
        return {"status": "ignored", "detail": f"Action '{action}' is not configured for triggers."}

    pr_id = str(pull_request["number"])
    repo_name = payload["repository"]["full_name"]
    pr_title = pull_request.get("title", "")
    pr_body = pull_request.get("body", "") or ""

    if pr_id not in active_pr_ids:
        active_pr_ids.append(pr_id)

    changed_files = []
    if "files" in payload:
        # Test/dev path — payload pre-populates file contents.
        for f in payload["files"]:
            changed_files.append({
                "path": f["filename"],
                "patch": f.get("patch", ""),
                "content": f.get("content", ""),
            })
    else:
        # Real GitHub PR — fetch via PyGithub if a token is configured.
        try:
            pr_number = int(pr_id)
        except ValueError:
            pr_number = -1
        fetched = fetch_pr_files(repo_name, pr_number) if pr_number > 0 else None
        if fetched:
            changed_files = fetched
        else:
            logger.warning(
                "Webhook for %s#%s arrived without inline files and no GITHUB_TOKEN was usable. "
                "Falling back to demo payload.",
                repo_name, pr_id,
            )
            changed_files = [
                {
                    "path": "fixtures/demo_files/auth.py",
                    "patch": '@@ -1,7 +1,9 @@\n def verify_login(username, password):\n+    SECRET_KEY = "SUPER_SECRET_12345"',
                    "content": 'def verify_login(username, password):\n    SECRET_KEY = "SUPER_SECRET_12345"\n    ratio = float(username)\n    if username == "admin" and password == SECRET_KEY:\n        return True\n    return False\n',
                }
            ]

    background_tasks.add_task(
        execute_review_pipeline,
        pr_id,
        repo_name,
        changed_files,
        pr_title,
        pr_body,
    )

    logger.info("Accepted webhook for PR #%s in %s", pr_id, repo_name)
    return {"status": "accepted", "pr_id": pr_id, "repo": repo_name}
