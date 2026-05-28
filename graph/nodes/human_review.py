"""6. Human-in-the-Loop Node — interrupt point for developer review."""
import logging
from typing import Any, Dict

from graph.state import GraphState

logger = logging.getLogger("Node.HumanReview")


def human_in_the_loop_node(state: GraphState) -> Dict[str, Any]:
    logger.info("Executing Human-in-the-Loop Node...")
    decisions = state.get("human_decisions", {})
    pending = False

    for fix in state["fixes"]:
        if fix.id not in decisions or decisions[fix.id] == "pending":
            decisions[fix.id] = "pending"
            pending = True

    if pending:
        logger.info("Halting pipeline: awaiting developer review on dashboard.")
        return {"human_decisions": decisions, "status": "waiting_for_approval"}

    logger.info("All decisions reviewed. Continuing flow.")
    return {"status": "applying"}
