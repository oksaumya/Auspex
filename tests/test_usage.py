"""LLMUsage math + cost derivation."""
from core.usage import ZERO_USAGE, LLMUsage, merge


def test_zero_usage_costs_zero():
    assert ZERO_USAGE.cost_usd == 0.0
    assert ZERO_USAGE.total_tokens == 0


def test_known_model_costs_match_pricing_table():
    u = LLMUsage(input_tokens=2_000_000, output_tokens=1_000_000, model="llama-3.3-70b-versatile")
    assert u.cost_usd > 0
    # 2M * 0.59/1M  +  1M * 0.79/1M  ==  1.18 + 0.79
    assert round(u.cost_usd, 4) == round(1.18 + 0.79, 4)


def test_unknown_model_returns_zero_when_model_missing():
    u = LLMUsage(input_tokens=100, output_tokens=100, model=None)
    assert u.cost_usd == 0.0


def test_merge_sums_tokens_and_picks_last_model():
    merged = merge([
        LLMUsage(10, 20, "llama-3.1-8b-instant"),
        LLMUsage(5, 5, "llama-3.3-70b-versatile"),
        LLMUsage(1, 2, None),
    ])
    assert merged.input_tokens == 16
    assert merged.output_tokens == 27
    assert merged.model == "llama-3.3-70b-versatile"


def test_merge_empty():
    merged = merge([])
    assert merged == LLMUsage(0, 0, None)
