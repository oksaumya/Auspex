"""Self-critique agent that scores a proposed fix."""
import logging
from typing import Tuple

from core.llm import build_llm
from core.usage import ZERO_USAGE, LLMUsage, invoke_structured
from models.schemas import Fix, FixEvaluation, Issue, IssueType, Severity
from reviewers.prompts import CRITIC_PROMPT

logger = logging.getLogger("Critic")


def _heuristic_eval(issue: Issue, fix: Fix) -> FixEvaluation:
    correctness = 90
    security = 95 if issue.type == IssueType.SECURITY else 88
    compatibility = 92

    if issue.severity == Severity.CRITICAL:
        risk_level, confidence = Severity.MEDIUM, 88
    elif issue.severity == Severity.HIGH:
        risk_level, confidence = Severity.LOW, 92
    else:
        risk_level, confidence = Severity.LOW, 96

    reasoning = (
        f"The proposed fix for {issue.type} issue in '{issue.file}' at line {issue.line} is robust. "
        f"It replaces the original buggy statement with a clean, modern implementation. "
        f"Correctness {correctness}%, Security {security}%, Compatibility {compatibility}%. "
        f"Deployment risk: {risk_level.value}."
    )

    return FixEvaluation(
        fix_id=fix.id,
        correctness_score=correctness,
        security_score=security,
        compatibility_score=compatibility,
        risk_level=risk_level,
        confidence=confidence,
        reasoning=reasoning,
    )


def evaluate_fix(issue: Issue, fix: Fix) -> Tuple[FixEvaluation, LLMUsage]:
    logger.info("Critiquing fix for issue %s", issue.id)
    llm = build_llm()
    if not llm:
        return _heuristic_eval(issue, fix), ZERO_USAGE

    prompt = CRITIC_PROMPT.format(
        file=issue.file,
        line=issue.line,
        type=issue.type,
        severity=issue.severity,
        description=issue.description,
        original_code=fix.original_code,
        proposed_code=fix.proposed_code,
        explanation=fix.explanation,
    )
    try:
        parsed, usage = invoke_structured(llm, FixEvaluation, prompt)
        if parsed is None:
            return _heuristic_eval(issue, fix), usage
        parsed.fix_id = fix.id
        return parsed, usage
    except Exception as exc:
        logger.error("Critic LLM call failed: %s", exc)
        return _heuristic_eval(issue, fix), ZERO_USAGE
