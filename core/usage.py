"""Shared types + helpers for tracking LLM token usage and cost."""
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from telemetry.pricing import cost_for


class LLMUsage(NamedTuple):
    input_tokens: int = 0
    output_tokens: int = 0
    model: Optional[str] = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def cost_usd(self) -> float:
        if not self.model:
            return 0.0
        return cost_for(self.model, self.input_tokens, self.output_tokens)


ZERO_USAGE = LLMUsage()


def merge(usages: List[LLMUsage]) -> LLMUsage:
    """Sums a list of LLMUsage records."""
    input_t = sum(u.input_tokens for u in usages)
    output_t = sum(u.output_tokens for u in usages)
    model = next((u.model for u in reversed(usages) if u.model), None)
    return LLMUsage(input_t, output_t, model)


def invoke_structured(llm, schema, prompt: str) -> Tuple[Any, LLMUsage]:
    """Calls ``llm.with_structured_output(schema, include_raw=True).invoke(prompt)``
    and returns ``(parsed, usage)``. ``parsed`` may be ``None`` if the model
    failed to produce a valid structured response.
    """
    raw_response = llm.with_structured_output(schema, include_raw=True).invoke(prompt)
    raw_message = raw_response.get("raw") if isinstance(raw_response, dict) else None
    parsed = raw_response.get("parsed") if isinstance(raw_response, dict) else raw_response

    usage_meta: Dict[str, Any] = {}
    if raw_message is not None:
        usage_meta = getattr(raw_message, "usage_metadata", None) or {}

    model = getattr(llm, "model_name", None) or getattr(llm, "model", None)
    return parsed, LLMUsage(
        input_tokens=int(usage_meta.get("input_tokens", 0) or 0),
        output_tokens=int(usage_meta.get("output_tokens", 0) or 0),
        model=model,
    )
