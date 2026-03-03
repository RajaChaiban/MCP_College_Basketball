"""Tests for dashboard/ai/predictor.py — pre-game ranking fix."""

from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers to build minimal game-like objects
# ---------------------------------------------------------------------------

class _Team:
    def __init__(self, name="Team", record="15-10", rank=None, score=0):
        self.team_name = name
        self.name = name
        self.record = record
        self.rank = rank
        self.score = score


class _Game:
    def __init__(self, home: _Team, away: _Team, status="pre",
                 period=1, clock="20:00", neutral_site=False):
        self.home = home
        self.away = away
        self.status = status
        self.period = period
        self.clock = clock
        self.neutral_site = neutral_site


# ---------------------------------------------------------------------------
# Patch the WinPredictor so tests don't need the .joblib file
# ---------------------------------------------------------------------------

def _make_mock_predictor(fixed_prob: float = 0.5):
    """Return a mock WinPredictor whose predict() echoes strength_diff signal."""
    mock = MagicMock()

    def _predict(state: dict) -> float:
        # Return a value that lets us verify strength_diff direction:
        # prob > 0.5  ↔  strength_diff > 0  (home favoured)
        # prob < 0.5  ↔  strength_diff < 0  (away favoured)
        sd = state.get("strength_diff", 0.0)
        return max(0.05, min(0.95, 0.5 + sd * 0.05))

    mock.predict.side_effect = _predict
    return mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPreGameRankingFix:
    """Verify that AP rankings are used in pre-game strength_diff."""

    def _call(self, home: _Team, away: _Team, mock_pred):
        """Call get_win_probability with a patched predictor instance."""
        with patch("dashboard.ai.predictor.predictor", mock_pred), \
             patch("dashboard.ai.predictor._load_lookup"), \
             patch("dashboard.ai.predictor._team_lookup", {}), \
             patch("dashboard.ai.predictor._h2h_lookup", {}):
            from dashboard.ai.predictor import get_win_probability
            return get_win_probability(_Game(home, away))

    # ------------------------------------------------------------------
    # 1. Ranked home team should be favoured over a worse unranked team
    # ------------------------------------------------------------------
    def test_ranked_home_favoured_over_unranked(self):
        mock_pred = _make_mock_predictor()
        home = _Team("Arizona", record="28-2", rank=2)
        away = _Team("Kansas State", record="10-18", rank=None)
        prob = self._call(home, away, mock_pred)
        # Home is ranked #2 with great record → should be heavily favoured
        assert prob is not None
        assert prob > 0.55, f"Expected prob > 0.55, got {prob:.4f}"

    # ------------------------------------------------------------------
    # 2. Ranked away team should overcome unranked home team
    # ------------------------------------------------------------------
    def test_ranked_away_penalises_unranked_home(self):
        mock_pred = _make_mock_predictor()
        home = _Team("Arizona State", record="8-20", rank=None)
        away = _Team("Kansas", record="21-8", rank=14)
        prob = self._call(home, away, mock_pred)
        # Away is ranked #14, home is unranked with bad record → home not favoured
        assert prob is not None
        assert prob < 0.50, f"Expected prob < 0.50, got {prob:.4f}"

    # ------------------------------------------------------------------
    # 3. Better-ranked team wins the head-to-head strength comparison
    # ------------------------------------------------------------------
    def test_higher_rank_wins_strength_comparison(self):
        """#2 Arizona at home should beat #14 Kansas away."""
        mock_pred = _make_mock_predictor()
        home_az  = _Team("Arizona", record="28-2",  rank=2)
        away_ku  = _Team("Kansas",  record="21-8", rank=14)

        home_az_vs_ku = _Team("Kansas",  record="21-8", rank=14)
        away_az       = _Team("Arizona", record="28-2",  rank=2)

        prob_az_home = self._call(home_az, away_ku, mock_pred)
        prob_az_away = self._call(home_az_vs_ku, away_az, mock_pred)

        assert prob_az_home is not None and prob_az_away is not None
        # Arizona home should yield higher probability than Kansas home
        assert prob_az_home > prob_az_away, (
            f"Arizona home prob ({prob_az_home:.4f}) should exceed "
            f"Kansas home prob ({prob_az_away:.4f})"
        )

    # ------------------------------------------------------------------
    # 4. Ranking matters more than a modest record difference
    # ------------------------------------------------------------------
    def test_ranking_outweighs_modest_record_gap(self):
        """#1 ranked team with 80% record should beat an unranked 85%-record team."""
        mock_pred = _make_mock_predictor()
        home = _Team("TopSeed", record="24-6", rank=1)   # 80 % — ranked #1
        away = _Team("Bubble",  record="26-5", rank=None) # 84 % — unranked
        prob = self._call(home, away, mock_pred)
        assert prob is not None
        assert prob > 0.50, (
            f"#1 seed home should be favoured despite slightly worse record; "
            f"got prob={prob:.4f}"
        )

    # ------------------------------------------------------------------
    # 5. Neither team ranked → falls back to pure record-based (original)
    # ------------------------------------------------------------------
    def test_neither_ranked_uses_record_only(self):
        mock_pred = _make_mock_predictor()
        home = _Team("TeamA", record="20-5",  rank=None)   # 80 %
        away = _Team("TeamB", record="10-15", rank=None)   # 40 %
        prob = self._call(home, away, mock_pred)
        assert prob is not None
        assert prob > 0.50, (
            f"Better-record home team should be favoured; got prob={prob:.4f}"
        )

    # ------------------------------------------------------------------
    # 6. strength_diff is directionally correct for both ranked
    # ------------------------------------------------------------------
    def test_both_ranked_home_better_rank(self):
        mock_pred = _make_mock_predictor()
        home = _Team("A", record="25-3", rank=3)
        away = _Team("B", record="22-6", rank=10)
        prob = self._call(home, away, mock_pred)
        assert prob is not None
        assert prob > 0.50, f"Home #3 vs Away #10 — home should be favoured; got {prob:.4f}"

    def test_both_ranked_away_better_rank(self):
        mock_pred = _make_mock_predictor()
        home = _Team("A", record="22-6", rank=10)
        away = _Team("B", record="25-3", rank=3)
        prob = self._call(home, away, mock_pred)
        assert prob is not None
        # After +0.03 home-court boost: #3 away vs #10 home — away should still dominate
        assert prob < 0.50, f"Home #10 vs Away #3 — away should be favoured; got {prob:.4f}"
