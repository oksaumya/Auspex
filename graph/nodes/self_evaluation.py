"""5. Self-Evaluation Node — scores each proposed fix."""
import logging
from typing import Any, Dict, List

from core.usage import LLMUsage, merge
from graph.state import GraphState
from reviewers.critic import evaluate_fix

logger = logging.getLogger("Node.SelfEval")


def self_evaluation_node(state: GraphState) -> Dict[str, Any]:
    logger.info("Executing Self-Evaluation Node...")
    evaluations = {}
    usages: List[LLMUsage] = []

    for fix in state["fixes"]:
        issue = next((i for i in state["issues"] if i.id == fix.issue_id), None)
        if not issue:
            continue
        evaluation, usage = evaluate_fix(issue, fix)
        evaluations[fix.id] = evaluation
        usages.append(usage)

    logger.info("Evaluated %d fixes.", len(evaluations))
    aggregate = merge(usages)
    return {
        "evaluations": evaluations,
        "status": "evaluated",
        "cost": (state.get("cost", 0.0) or 0.0) + aggregate.cost_usd,
        "tokens_used": (state.get("tokens_used", 0) or 0) + aggregate.total_tokens,
    }
