"""3. Parallel Analysis Node — fans out to the three specialist reviewers.

Each agent's output is filtered to its category (in the reviewer itself).
Aggregated results are then deduplicated across agents and cost is summed.
"""
import concurrent.futures
import logging
from typing import Any, Dict, List

from core.usage import LLMUsage, merge
from graph.state import GraphState
from models.schemas import Issue
from reviewers import run_bug_hunter, run_performance_reviewer, run_security_scanner
from reviewers._aggregation import deduplicate

logger = logging.getLogger("Node.Analysis")


def parallel_analysis_node(state: GraphState) -> Dict[str, Any]:
    logger.info("Executing Parallel Analysis Node...")
    raw_issues: List[Issue] = []
    usages: List[LLMUsage] = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for f_info in state["changed_files"]:
            path = f_info["path"]
            content = f_info["content"]
            patch = f_info["patch"]
            context = state["retrieved_context"].get(path, [])

            futures.append(executor.submit(run_bug_hunter, path, content, patch, context))
            futures.append(executor.submit(run_security_scanner, path, content, patch, context))
            futures.append(executor.submit(run_performance_reviewer, path, content, patch, context))

        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                raw_issues.extend(result.issues)
                usages.append(result.usage)
            except Exception as exc:
                logger.error("Specialist thread raised: %s", exc)

    deduped = deduplicate(raw_issues)
    dropped = len(raw_issues) - len(deduped)
    if dropped:
        logger.info("Dedupe dropped %d duplicate issues across agents.", dropped)
    logger.info("Analysis complete. %d unique issues (from %d raw).", len(deduped), len(raw_issues))

    aggregate = merge(usages)
    prior_cost = state.get("cost", 0.0) or 0.0
    prior_tokens = state.get("tokens_used", 0) or 0
    return {
        "issues": deduped,
        "status": "analyzed",
        "cost": prior_cost + aggregate.cost_usd,
        "tokens_used": prior_tokens + aggregate.total_tokens,
    }
