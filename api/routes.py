"""Session, decision, and resume endpoints used by the dashboard."""
import logging
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from graph import get_graph
from models.schemas import ReviewSession

logger = logging.getLogger("APIRoutes")
router = APIRouter(prefix="/api")

# In-memory roster of active PR IDs (populated by the webhook handler)
active_pr_ids: List[str] = ["demo-101"]


class DecisionRequest(BaseModel):
    fix_id: str
    decision: str  # "approved" or "rejected"


def get_session_by_pr(pr_id: str) -> ReviewSession:
    """Reconstructs a ReviewSession from the LangGraph thread state."""
    graph = get_graph()
    config = {"configurable": {"thread_id": pr_id}}
    state_info = graph.get_state(config)

    if not state_info or not state_info.values:
        logger.info("Thread %s not found in checkpointer. Bootstrapping demo run.", pr_id)
        initial_state = {
            "pr_id": pr_id,
            "repo_name": "sandbox/review-demo",
            "commit_sha": "abc1234def",
            "pr_title": "Feature: Upgrade auth security and refactor utils loops",
            "pr_body": "Resolves login performance bottlenecks and secure connection issues.",
            "changed_files": [],
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
        graph.invoke(initial_state, config)
        state_info = graph.get_state(config)

    state = state_info.values
    return ReviewSession(
        pr_id=state.get("pr_id", pr_id),
        repo_name=state.get("repo_name", "unknown/repo"),
        commit_sha=state.get("commit_sha", "unknown"),
        pr_title=state.get("pr_title", ""),
        pr_body=state.get("pr_body", ""),
        status=state.get("status", "pending"),
        issues=state.get("issues", []),
        fixes=state.get("fixes", []),
        evaluations=state.get("evaluations", {}),
        human_decisions=state.get("human_decisions", {}),
        applied_fixes=state.get("applied_fixes", []),
        cost=state.get("cost", 0.0),
        tokens_used=state.get("tokens_used", 0),
    )


@router.get("/sessions", response_model=List[str])
async def list_active_sessions():
    return active_pr_ids


@router.get("/session/{pr_id}", response_model=ReviewSession)
async def get_session(pr_id: str):
    try:
        return get_session_by_pr(pr_id)
    except Exception as exc:
        logger.error("Error fetching session %s: %s", pr_id, exc)
        raise HTTPException(status_code=404, detail=f"Review session {pr_id} not found.")


@router.post("/session/{pr_id}/decide")
async def register_decision(pr_id: str, payload: DecisionRequest):
    graph = get_graph()
    config = {"configurable": {"thread_id": pr_id}}
    state_info = graph.get_state(config)

    if not state_info or not state_info.values:
        raise HTTPException(status_code=404, detail="Review session thread not found.")

    current_decisions = state_info.values.get("human_decisions", {})
    current_decisions[payload.fix_id] = payload.decision

    graph.update_state(config, {"human_decisions": current_decisions}, as_node="human_in_the_loop")
    logger.info("Decision %s for fix %s in thread %s.", payload.decision, payload.fix_id, pr_id)
    return {"status": "success", "decisions": current_decisions}


def _resume_graph(pr_id: str) -> None:
    try:
        graph = get_graph()
        config = {"configurable": {"thread_id": pr_id}}
        logger.info("Resuming graph for thread %s", pr_id)
        graph.invoke(None, config)
        logger.info("Graph flow completed for thread %s", pr_id)
    except Exception as exc:
        logger.error("Error resuming graph thread %s: %s", pr_id, exc)


@router.post("/session/{pr_id}/resume")
async def resume_session(pr_id: str, background_tasks: BackgroundTasks):
    graph = get_graph()
    config = {"configurable": {"thread_id": pr_id}}
    state_info = graph.get_state(config)

    if not state_info or not state_info.values:
        raise HTTPException(status_code=404, detail="Session thread not found.")

    decisions = state_info.values.get("human_decisions", {})
    pending_fixes = [fid for fid, dec in decisions.items() if dec == "pending"]
    if pending_fixes:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resume. Decisions are still pending for fixes: {pending_fixes}",
        )

    background_tasks.add_task(_resume_graph, pr_id)
    return {"status": "resumed", "detail": "Code Review workflow is finishing in the background."}
