"""
Win Probability Predictor.
Loads the joblib bundle and provides live predictions.
"""

from __future__ import annotations
import json
import math
import os
import joblib
import pandas as pd
import numpy as np
from collections import deque

# ---------------------------------------------------------------------------
# Per-team contextual feature lookup (built from training data)
# ---------------------------------------------------------------------------

_LOOKUP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "team_features_lookup.json")

_team_lookup: dict | None = None
_h2h_lookup: dict | None = None


def _load_lookup() -> None:
    global _team_lookup, _h2h_lookup
    if _team_lookup is not None:
        return
    try:
        with open(_LOOKUP_PATH) as f:
            data = json.load(f)
        _team_lookup = data.get("teams", {})
        # h2h keys are stored as "(home, away)" strings
        _h2h_lookup = {eval(k): v for k, v in data.get("h2h", {}).items()}
    except Exception as e:
        print(f"[Predictor] Could not load team_features_lookup.json: {e}")
        _team_lookup = {}
        _h2h_lookup = {}


def _team_features(team_name: str, side: str, fallback_wp: float) -> dict:
    """Return contextual features for a team from the training-data lookup."""
    _load_lookup()
    info = _team_lookup.get(team_name, {})
    return {
        f"{side}_conf_win_pct":        info.get("conf_win_pct",        fallback_wp),
        f"{side}_recent_win_pct":      info.get("recent_win_pct",      fallback_wp),
        f"{side}_collapse_pct_up_10":  info.get("collapse_pct_up_10",  0.0),
        f"{side}_comeback_pct_down_5": info.get("comeback_pct_down_5", 0.0),
        f"{side}_conf_rank":           50.0,   # always 50 in training data
        f"{side}_h2h_win_pct":         0.5,    # filled in by caller if H2H known
    }


def _h2h_features(home_team: str, away_team: str) -> tuple[float, float]:
    """Return (home_h2h_win_pct, away_h2h_win_pct) from training lookup."""
    _load_lookup()
    if _h2h_lookup is None:
        return 0.5, 0.5
    pair = _h2h_lookup.get((home_team, away_team))
    if pair:
        return float(pair[0]), float(pair[1])
    return 0.5, 0.5


def _parse_win_pct(record: str) -> float:
    """Parse win percentage from '15-3' format. Returns 0.5 on failure."""
    try:
        parts = record.split('-')
        wins, losses = int(parts[0]), int(parts[1])
        total = wins + losses
        return wins / total if total > 0 else 0.5
    except Exception:
        return 0.5


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class WinPredictor:
    def __init__(self, model_path: str | None = None):
        if model_path is None:
            _project_root = os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))))
            preferred = os.path.join(_project_root, "cbb_predictor_bundle_2025_26_safe.joblib")
            fallback = os.path.join(_project_root, "cbb_predictor_bundle.joblib")
            self.model_path = preferred if os.path.exists(preferred) else fallback
        else:
            self.model_path = model_path
        self.bundle = None
        self.lr_model = None
        self.xgb_model = None
        self.scaler = None
        self.features = None
        self.last_load_time = 0
        self._load_model()

    def _load_model(self):
        if not os.path.exists(self.model_path):
            print(f"[Predictor] Model file not found at {self.model_path}")
            return

        try:
            self.bundle = joblib.load(self.model_path)
            self.lr_model = self.bundle.get('lr_model')
            self.xgb_model = self.bundle.get('xgb_model')
            self.scaler = self.bundle.get('scaler')
            self.features = self.bundle.get('features')
            print(f"[Predictor] Loaded bundle features: {self.features}")
        except Exception as e:
            print(f"[Predictor] Error loading predictor bundle: {e}")

    def predict(self, game_state: dict) -> float | None:
        """
        Calculate win probability (0.0 to 1.0) for the HOME team.
        """
        if not self.lr_model or not self.xgb_model:
            self._load_model()
            if not self.lr_model:
                print("[Predictor] Models not loaded.")
                return None

        try:
            # Fill any missing features with 0 as final safety net
            for feat in self.features:
                if feat not in game_state:
                    game_state[feat] = 0.0

            X_df = pd.DataFrame([game_state])[self.features]

            X_scaled = self.scaler.transform(X_df)
            lr_prob = self.lr_model.predict_proba(X_scaled)[0, 1]
            xgb_prob = self.xgb_model.predict_proba(X_df)[0, 1]

            final_prob = (lr_prob + xgb_prob) / 2.0
            print(f"[Predictor] State: {game_state} -> Prob: {final_prob:.4f}")
            return final_prob
        except Exception as e:
            print(f"[Predictor] Prediction error: {e}")
            return None


# Global predictor instance
predictor = WinPredictor()

def _stabilize_live_probability(raw_prob: float, score_diff: float, mins_remaining: float, period: float) -> float:
    """
    Apply a conservative stabilization layer to reduce overconfident live outputs
    when the model is fed sparse/noisy game-state features.
    """
    # Heuristic prior from score margin and remaining time.
    elapsed = max(0.0, 40.0 - float(mins_remaining))
    spread_scale = max(2.5, 1.0 + 0.12 * elapsed)
    heuristic = 1.0 / (1.0 + math.exp(-(float(score_diff) / spread_scale)))

    # Trust heuristic more earlier in game; trust model more late.
    if mins_remaining >= 10:
        alpha = 0.65
        lo, hi = 0.03, 0.97
    elif mins_remaining >= 5:
        alpha = 0.50
        lo, hi = 0.02, 0.98
    else:
        alpha = 0.25
        lo, hi = 0.005, 0.995

    blended = alpha * heuristic + (1.0 - alpha) * float(raw_prob)
    return min(hi, max(lo, blended))


def get_win_probability(game, pbp=None, strength_map=None) -> float | None:
    """Helper to prepare game state and get prediction."""
    if isinstance(game, dict):
        class Obj:
            def __init__(self, d):
                for k, v in d.items():
                    if isinstance(v, dict):
                        setattr(self, k, Obj(v))
                    else:
                        setattr(self, k, v)
        game_obj = Obj(game)
    else:
        game_obj = game

    status = getattr(game_obj, "status", "pre")

    # 1. Handle Final Games
    h_score = getattr(game_obj.home, "score", 0)
    a_score = getattr(game_obj.away, "score", 0)
    if status == "post":
        return 1.0 if h_score > a_score else 0.0

    # 2. Score Difference
    score_diff = h_score - a_score

    # 3. Time features
    mins_left = 20
    period = getattr(game_obj, "period", 1) or 1
    clock = getattr(game_obj, "clock", "20:00")

    if clock and ":" in str(clock):
        try:
            parts = str(clock).split(":")
            mins_left = int(parts[0])
        except Exception:
            mins_left = 10

    total_mins_remaining = mins_left if period >= 2 else mins_left + 20
    if status == "pre":
        total_mins_remaining = 40

    time_ratio = total_mins_remaining / 40.0

    # 4. Momentum (from PBP if available)
    momentum = 0.0
    if pbp and hasattr(pbp, "plays") and pbp.plays:
        recent_plays = pbp.plays[-20:]
        old_diff = recent_plays[0].score_home - recent_plays[0].score_away
        momentum = score_diff - old_diff

    # 5. Strength diff
    h_rec = getattr(game_obj.home, "record", "0-0") or "0-0"
    a_rec = getattr(game_obj.away, "record", "0-0") or "0-0"
    h_wp = _parse_win_pct(h_rec)
    a_wp = _parse_win_pct(a_rec)

    if status == "pre":
        # Pre-game: blend rank + record when rankings are available.
        # Convert rank (1=best, 25=worst ranked) to a 0-1 strength score so
        # the resulting strength_diff stays in the same scale the model was
        # trained on.  Unranked teams stay at their win-pct only.
        h_rank = getattr(game_obj.home, "rank", None)
        a_rank = getattr(game_obj.away, "rank", None)

        if h_rank:
            h_strength = 0.6 * ((26 - float(h_rank)) / 25.0) + 0.4 * h_wp
        else:
            h_strength = h_wp

        if a_rank:
            a_strength = 0.6 * ((26 - float(a_rank)) / 25.0) + 0.4 * a_wp
        else:
            a_strength = a_wp

        strength_diff = (h_strength - a_strength) * 10 * 0.4
    else:
        h_rank = getattr(game_obj.home, "rank", None) or 50
        a_rank = getattr(game_obj.away, "rank", None) or 50
        strength_diff = (a_rank - h_rank) / 4.0

    # 6. Contextual features — from training-data lookup, fall back to current record
    home_name = getattr(game_obj.home, "team_name", None) or getattr(game_obj.home, "name", "")
    away_name = getattr(game_obj.away, "team_name", None) or getattr(game_obj.away, "name", "")

    home_ctx = _team_features(home_name, "home", h_wp)
    away_ctx = _team_features(away_name, "away", a_wp)

    # H2H from lookup
    home_h2h, away_h2h = _h2h_features(home_name, away_name)
    home_ctx["home_h2h_win_pct"] = home_h2h
    away_ctx["away_h2h_win_pct"] = away_h2h

    state = {
        "score_diff":    float(score_diff),
        "momentum":      float(momentum),
        "strength_diff": float(strength_diff),
        "time_ratio":    float(time_ratio),
        "mins_remaining": float(total_mins_remaining),
        "period":        float(period),
        **home_ctx,
        **away_ctx,
    }

    result = predictor.predict(state)
    if result is not None and status == "in":
        result = _stabilize_live_probability(
            raw_prob=float(result),
            score_diff=float(score_diff),
            mins_remaining=float(total_mins_remaining),
            period=float(period),
        )
    if result is not None and status == "pre":
        is_neutral = getattr(game_obj, "neutral_site", False)
        if not is_neutral:
            result = min(0.95, max(0.05, result + 0.03))
    return result
