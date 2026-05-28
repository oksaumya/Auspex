"""Compiles the LangGraph state machine and exposes a `run_review` helper.

The compiled graph is a process-wide singleton. Its checkpoints persist to a
SQLite file (``CHECKPOINT_DB_PATH``) so sessions survive restarts.
"""
import logging
import sqlite3
from typing import Optional

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from core.config import CHECKPOINT_DB_PATH
from graph.nodes import (
    apply_fix_node,
    context_retrieval_node,
    fix_generation_node,
    human_in_the_loop_node,
    learning_node,
    parallel_analysis_node,
    pr_ingestion_node,
    self_evaluation_node,
)
from graph.state import GraphState

logger = logging.getLogger("Graph.Builder")


def _make_checkpointer() -> SqliteSaver:
    CHECKPOINT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CHECKPOINT_DB_PATH), check_same_thread=False)
    return SqliteSaver(conn)


def build_graph():
    workflow = StateGraph(GraphState)

    workflow.add_node("pr_ingestion", pr_ingestion_node)
    workflow.add_node("context_retrieval", context_retrieval_node)
    workflow.add_node("parallel_analysis", parallel_analysis_node)
    workflow.add_node("fix_generation", fix_generation_node)
    workflow.add_node("self_evaluation", self_evaluation_node)
    workflow.add_node("human_in_the_loop", human_in_the_loop_node)
    workflow.add_node("apply_fix", apply_fix_node)
    workflow.add_node("learning", learning_node)

    workflow.set_entry_point("pr_ingestion")
    workflow.add_edge("pr_ingestion", "context_retrieval")
    workflow.add_edge("context_retrieval", "parallel_analysis")
    workflow.add_edge("parallel_analysis", "fix_generation")
    workflow.add_edge("fix_generation", "self_evaluation")
    workflow.add_edge("self_evaluation", "human_in_the_loop")
    workflow.add_edge("human_in_the_loop", "apply_fix")
    workflow.add_edge("apply_fix", "learning")
    workflow.add_edge("learning", END)

    checkpointer = _make_checkpointer()
    compiled = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_in_the_loop"],
    )
    logger.info("LangGraph compiled with SQLite checkpointer at %s", CHECKPOINT_DB_PATH)
    return compiled


_graph: Optional[object] = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_review(data: dict) -> dict:
    """Synchronously runs the graph for a custom payload (PR ID + files list)."""
    changed_files = []
    for f in data.get("files", []):
        changed_files.append({
            "path": f.get("filename", "unknown.py"),
            "patch": f.get("patch", ""),
            "content": f.get("content", f.get("patch", "")),
        })

    initial_state = {
        "pr_id": data.get("pr_id", "test-001"),
        "repo_name": data.get("repo", "sandbox/review-demo"),
        "commit_sha": "abc1234def",
        "pr_title": data.get("title", "Test Pull Request"),
        "pr_body": "Testing automated review script.",
        "changed_files": changed_files,
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

    graph = get_graph()
    config = {"configurable": {"thread_id": data.get("pr_id", "test-001")}}
    final_state = graph.invoke(initial_state, config)

    evals_dict = final_state.get("evaluations", {})
    evals_list = []
    for fix_id, ev in evals_dict.items():
        setattr(ev, "confidence_score", getattr(ev, "confidence", 90))
        evals_list.append(ev)

    return {
        "issues": final_state.get("issues", []),
        "fixes": final_state.get("fixes", []),
        "evaluations": evals_list,
        "raw_evaluations": evals_dict,
        "status": final_state.get("status", "pending"),
    }
