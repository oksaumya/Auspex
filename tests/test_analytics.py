"""Analytics aggregation across multiple sessions."""
from unittest.mock import patch

from models.schemas import (
    Fix,
    FixEvaluation,
    Issue,
    IssueType,
    ReviewSession,
    Severity,
)


def _session(pr_id: str, n_issues: int = 1, accepted: int = 0, rejected: int = 0, confidence: int = 90) -> ReviewSession:
    issues = [Issue(file="a.py", line=1, type=IssueType.BUG, severity=Severity.LOW, description=f"#{i}") for i in range(n_issues)]
    fixes = [Fix(id=str(i), issue_id=issues[i].id, original_code="o", proposed_code="p", explanation="e") for i in range(n_issues)]
    decisions = {}
    for i in range(accepted):
        decisions[fixes[i].id] = "approved"
    for i in range(accepted, accepted + rejected):
        decisions[fixes[i].id] = "rejected"
    evaluations = {
        f.id: FixEvaluation(
            fix_id=f.id,
            correctness_score=confidence,
            security_score=confidence,
            compatibility_score=confidence,
            risk_level=Severity.LOW,
            confidence=confidence,
            reasoning="test",
        )
        for f in fixes
    }
    return ReviewSession(
        pr_id=pr_id,
        repo_name="org/repo",
        issues=issues,
        fixes=fixes,
        evaluations=evaluations,
        human_decisions=decisions,
        cost=0.0012,
        tokens_used=500,
    )


def test_summary_aggregates_across_sessions():
    import asyncio

    from api.analytics import analytics_summary

    sessions = [
        _session("pr-1", n_issues=3, accepted=2, rejected=1, confidence=80),
        _session("pr-2", n_issues=2, accepted=1, rejected=0, confidence=90),
    ]

    def fake_get(pr_id):
        return next(s for s in sessions if s.pr_id == pr_id)

    with patch("api.analytics.active_pr_ids", ["pr-1", "pr-2"]):
        with patch("api.analytics.get_session_by_pr", side_effect=fake_get):
            with patch("api.analytics._load_rejections", return_value=[]):
                summary = asyncio.run(analytics_summary())

    assert summary["total_prs"] == 2
    assert summary["total_issues"] == 5
    assert summary["total_fixes_proposed"] == 5
    assert summary["total_fixes_accepted"] == 3
    assert summary["total_fixes_rejected"] == 1
    assert summary["acceptance_rate"] == 75.0  # 3 of 4 decided
    assert summary["avg_confidence"] == 85.0
    assert summary["defect_distribution"]["BUG"] == 5
    assert len(summary["confidence_trend"]) == 2
    assert summary["cost_breakdown_usd"] == round(0.0024, 4)
    assert summary["tokens_used"] == 1000
