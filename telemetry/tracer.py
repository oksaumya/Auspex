"""LangSmith client wrapper that logs review-session telemetry."""
import logging
from typing import Optional

from core.config import LANGSMITH_API_KEY, LANGSMITH_ENABLED, LANGSMITH_PROJECT
from models.schemas import ReviewSession
from telemetry.pricing import cost_for

logger = logging.getLogger("Telemetry")


class LangSmithTracer:
    def __init__(self) -> None:
        self.enabled = LANGSMITH_ENABLED
        self.api_key = LANGSMITH_API_KEY
        self.project_name = LANGSMITH_PROJECT
        self.client = None

        if self.enabled and self.api_key:
            try:
                from langsmith import Client

                self.client = Client(api_key=self.api_key)
                logger.info("LangSmith client initialized.")
            except Exception as exc:
                logger.error("Failed to initialize LangSmith Client: %s", exc)
        else:
            logger.info("LangSmith tracing disabled or API key missing.")

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        return cost_for(model, input_tokens, output_tokens)

    def log_session_run(self, session: ReviewSession) -> None:
        if not self.client:
            return
        try:
            tags = [
                f"pr-{session.pr_id}",
                f"repo-{session.repo_name.replace('/', '-')}",
                session.status,
            ]
            fixes_accepted = sum(
                1 for decision in session.human_decisions.values() if decision == "approved"
            )
            total_fixes = len(session.fixes)
            accepted_rate = (fixes_accepted / total_fixes * 100) if total_fixes else 0
            avg_confidence = 0.0
            if session.evaluations:
                avg_confidence = sum(
                    e.confidence for e in session.evaluations.values()
                ) / len(session.evaluations)

            metadata = {
                "issues_found": len(session.issues),
                "fixes_proposed": total_fixes,
                "fixes_accepted": fixes_accepted,
                "fixes_accepted_rate": accepted_rate,
                "avg_confidence_score": avg_confidence,
                "total_tokens": session.tokens_used,
                "total_cost_usd": session.cost,
            }
            logger.info("LangSmith logging: %s", metadata)

            self.client.create_run(
                name=f"PR Review: {session.repo_name} #{session.pr_id}",
                run_type="chain",
                inputs={"pr_id": session.pr_id, "repo": session.repo_name},
                outputs={"issues_found": len(session.issues), "status": session.status},
                tags=tags,
                extra={"metadata": metadata},
                project_name=self.project_name,
            )
        except Exception as exc:
            logger.warning("Failed to log run to LangSmith: %s", exc)


_tracer: Optional[LangSmithTracer] = None


def get_tracer() -> LangSmithTracer:
    global _tracer
    if _tracer is None:
        _tracer = LangSmithTracer()
    return _tracer
