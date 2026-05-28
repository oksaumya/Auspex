"""8. Learning Node — logs rejections + emits telemetry to LangSmith."""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from core.config import LEARNING_DB_PATH
from graph.state import GraphState
from models.schemas import ReviewSession
from telemetry import get_tracer

logger = logging.getLogger("Node.Learning")


def learning_node(state: GraphState) -> Dict[str, Any]:
    logger.info("Executing Learning Node...")
    decisions = state["human_decisions"]
    rejections = []

    for fix in state["fixes"]:
        if decisions.get(fix.id) != "rejected":
            continue
        evaluation = state["evaluations"].get(fix.id)
        confidence = evaluation.confidence if evaluation else 0
        rejections.append({
            "fix_id": fix.id,
            "issue_id": fix.issue_id,
            "original_code": fix.original_code,
            "proposed_code": fix.proposed_code,
            "confidence_score": confidence,
            "reason": "Human developer rejected the code fix.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    existing_db = []
    if LEARNING_DB_PATH.exists():
        try:
            existing_db = json.loads(LEARNING_DB_PATH.read_text())
        except Exception:
            existing_db = []

    existing_db.extend(rejections)
    try:
        LEARNING_DB_PATH.write_text(json.dumps(existing_db, indent=2))
        logger.info("Persisted %d rejections to %s", len(rejections), LEARNING_DB_PATH)
    except Exception as exc:
        logger.error("Failed to save rejections db: %s", exc)

    tracer = get_tracer()
    session = ReviewSession(
        pr_id=state["pr_id"],
        repo_name=state["repo_name"],
        commit_sha=state.get("commit_sha", "unknown"),
        pr_title=state.get("pr_title", ""),
        pr_body=state.get("pr_body", ""),
        status="completed",
        issues=state["issues"],
        fixes=state["fixes"],
        evaluations=state["evaluations"],
        human_decisions=state["human_decisions"],
        applied_fixes=state["applied_fixes"],
        cost=state.get("cost", 0.0),
        tokens_used=state.get("tokens_used", 0),
    )
    tracer.log_session_run(session)

    return {"status": "completed"}
