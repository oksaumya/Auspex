"""Shared LangGraph state schema."""
from typing import Any, Dict, List, Optional, TypedDict

from models.schemas import Fix, FixEvaluation, Issue


class GraphState(TypedDict):
    pr_id: str
    repo_name: str
    commit_sha: str
    pr_title: str
    pr_body: str

    # Files being reviewed: [{'path': str, 'patch': str, 'content': str}]
    changed_files: List[Dict[str, Any]]

    # Context search results: {filepath: [context_chunks]}
    retrieved_context: Dict[str, List[str]]

    issues: List[Issue]
    fixes: List[Fix]
    evaluations: Dict[str, FixEvaluation]  # fix_id -> FixEvaluation

    # 'approved' | 'rejected' | 'pending', keyed by fix_id
    human_decisions: Dict[str, str]
    applied_fixes: List[str]

    status: str
    tokens_used: int
    cost: float
    error: Optional[str]
    metadata: Dict[str, Any]
