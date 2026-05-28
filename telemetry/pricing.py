"""Groq model pricing per 1M tokens (USD).

Used by the LangSmith tracer to estimate per-run cost.
"""

PRICING = {
    "llama-3.3-70b-versatile": {"input": 0.59 / 1_000_000, "output": 0.79 / 1_000_000},
    "llama-3.1-8b-instant": {"input": 0.05 / 1_000_000, "output": 0.08 / 1_000_000},
    "openai/gpt-oss-120b": {"input": 0.15 / 1_000_000, "output": 0.75 / 1_000_000},
    "openai/gpt-oss-20b": {"input": 0.10 / 1_000_000, "output": 0.50 / 1_000_000},
    "meta-llama/llama-4-scout-17b-16e-instruct": {"input": 0.11 / 1_000_000, "output": 0.34 / 1_000_000},
    "default": {"input": 0.20 / 1_000_000, "output": 0.60 / 1_000_000},
}


def cost_for(model: str, input_tokens: int, output_tokens: int) -> float:
    prices = PRICING.get(model, PRICING["default"])
    return input_tokens * prices["input"] + output_tokens * prices["output"]
