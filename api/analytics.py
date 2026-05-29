"""Aggregated metrics endpoint backing the dashboard's Analytics page."""
import json
import logging
from typing import Any, Dict, List

from fastapi import APIRouter

from api.routes import active_pr_ids, get_session_by_pr
from core.config import LEARNING_DB_PATH
from models.schemas import IssueType

logger = logging.getLogger("Analytics")
router = APIRouter(prefix="/api")


def _load_rejections() -> List[Dict[str, Any]]:
    if not LEARNING_DB_PATH.exists():
        return []
    try:
        return json.loads(LEARNING_DB_PATH.read_text())
    except Exception:
        return []


@router.get("/analytics/summary")
async def analytics_summary() -> Dict[str, Any]:
    """Aggregates metrics across every active PR plus the rejection log."""
    sessions = []
    for pr_id in active_pr_ids:
        try:
            sessions.append(get_session_by_pr(pr_id))
        except Exception as exc:
            logger.warning("Could not load session %s: %s", pr_id, exc)

    total_prs = len(sessions)
    total_issues = sum(len(s.issues) for s in sessions)
    total_fixes_proposed = sum(len(s.fixes) for s in sessions)
    total_fixes_accepted = sum(
        sum(1 for d in s.human_decisions.values() if d == "approved") for s in sessions
    )
    total_fixes_rejected = sum(
        sum(1 for d in s.human_decisions.values() if d == "rejected") for s in sessions
    )
    decided = total_fixes_accepted + total_fixes_rejected
    acceptance_rate = (total_fixes_accepted / decided * 100) if decided else 0.0

    confidence_values: List[int] = []
    confidence_trend: List[Dict[str, Any]] = []
    for s in sessions:
        if not s.evaluations:
            continue
        avg = sum(e.confidence for e in s.evaluations.values()) / len(s.evaluations)
        confidence_values.append(avg)
        confidence_trend.append({"pr_id": s.pr_id, "confidence": round(avg, 1)})
    avg_confidence = round(sum(confidence_values) / len(confidence_values), 1) if confidence_values else 0.0

    defect_distribution = {t.value: 0 for t in IssueType}
    for s in sessions:
        for issue in s.issues:
            key = issue.type.value if hasattr(issue.type, "value") else str(issue.type)
            defect_distribution[key] = defect_distribution.get(key, 0) + 1

    cost_breakdown_usd = round(sum(s.cost for s in sessions), 4)
    tokens_used = sum(s.tokens_used for s in sessions)

    rejections = _load_rejections()
    recent_rejections = list(reversed(rejections))[:5]

    return {
        "total_prs": total_prs,
        "total_issues": total_issues,
        "total_fixes_proposed": total_fixes_proposed,
        "total_fixes_accepted": total_fixes_accepted,
        "total_fixes_rejected": total_fixes_rejected,
        "acceptance_rate": round(acceptance_rate, 1),
        "avg_confidence": avg_confidence,
        "defect_distribution": defect_distribution,
        "confidence_trend": confidence_trend,
        "cost_breakdown_usd": cost_breakdown_usd,
        "tokens_used": tokens_used,
        "total_rejections_logged": len(rejections),
        "recent_rejections": recent_rejections,
    }
