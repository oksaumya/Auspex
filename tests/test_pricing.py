"""Per-model pricing math."""
import pytest

from telemetry.pricing import PRICING, cost_for


def test_known_model_uses_its_rate():
    cost = cost_for("llama-3.3-70b-versatile", 1_000_000, 1_000_000)
    assert cost == pytest.approx(0.59 + 0.79, rel=1e-6)


def test_unknown_model_falls_back_to_default():
    cost = cost_for("not-a-real-model", 1_000_000, 1_000_000)
    expected = PRICING["default"]["input"] * 1_000_000 + PRICING["default"]["output"] * 1_000_000
    assert cost == pytest.approx(expected, rel=1e-6)


def test_zero_tokens_zero_cost():
    assert cost_for("llama-3.1-8b-instant", 0, 0) == 0.0


def test_partial_tokens_proportional():
    cost = cost_for("llama-3.1-8b-instant", 500_000, 250_000)
    assert cost == pytest.approx(0.05 * 0.5 + 0.08 * 0.25, rel=1e-6)
