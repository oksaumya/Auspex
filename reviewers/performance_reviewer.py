"""Performance Reviewer agent."""
import logging
from typing import List

from core.llm import build_llm
from core.usage import invoke_structured
from models.schemas import Issue, IssueType
from reviewers._aggregation import filter_to_category
from reviewers._result import ReviewerResult
from reviewers._schema import SubAgentReviewOutput
from reviewers.heuristics import run_mock_review
from reviewers.prompts import PERFORMANCE_REVIEWER_PROMPT

logger = logging.getLogger("PerformanceReviewer")


def run_performance_reviewer(
    filepath: str, content: str, patch: str, context: List[str]
) -> ReviewerResult:
    logger.info("Running Performance Reviewer on %s", filepath)
    llm = build_llm()
    if not llm:
        return ReviewerResult(
            issues=run_mock_review(filepath, content, patch, IssueType.PERFORMANCE)
        )

    prompt = PERFORMANCE_REVIEWER_PROMPT.format(
        filepath=filepath,
        patch=patch,
        content=content,
        context="\n\n".join(context),
    )
    try:
        parsed, usage = invoke_structured(llm, SubAgentReviewOutput, prompt)
        issues: List[Issue] = (parsed.issues if parsed is not None else []) or []
        for issue in issues:
            issue.file = filepath
            issue.type = IssueType.PERFORMANCE
        return ReviewerResult(
            issues=filter_to_category(issues, IssueType.PERFORMANCE), usage=usage
        )
    except Exception as exc:
        logger.error("Performance Reviewer LLM call failed: %s", exc)
        return ReviewerResult(
            issues=run_mock_review(filepath, content, patch, IssueType.PERFORMANCE)
        )
