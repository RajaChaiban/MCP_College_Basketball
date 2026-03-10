"""Tests for live probability stabilization in dashboard predictor."""

from dashboard.ai.predictor import _stabilize_live_probability


def test_midgame_large_deficit_not_extreme_zero():
    # Previously, raw model output could be ~0.004 at ~11 mins left for -6/-11 margins.
    adjusted = _stabilize_live_probability(
        raw_prob=0.004,
        score_diff=-6.0,
        mins_remaining=11.0,
        period=2.0,
    )
    assert adjusted >= 0.03


def test_stabilizer_preserves_direction():
    up = _stabilize_live_probability(0.99, score_diff=6.0, mins_remaining=11.0, period=2.0)
    down = _stabilize_live_probability(0.004, score_diff=-6.0, mins_remaining=11.0, period=2.0)
    assert up > 0.5
    assert down < 0.5
