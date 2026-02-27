"""
Win Probability Predictor.
Loads the joblib bundle and provides live predictions.
"""

from __future__ import annotations
import os
import joblib
import pandas as pd
import numpy as np
from collections import deque

def _parse_win_pct(record: str) -> float:
    """Parse win percentage from '15-3' format. Returns 0.5 on failure."""
    try:
        parts = record.split('-')
        wins, losses = int(parts[0]), int(parts[1])
        total = wins + losses
        return wins / total if total > 0 else 0.5
    except Exception:
        return 0.5


class WinPredictor:
    def __init__(self, model_path: str = "cbb_predictor_bundle.joblib"):
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
        game_state keys: score_diff, momentum, strength_diff, time_ratio, mins_remaining, period
        """
        if not self.lr_model or not self.xgb_model:
            # Try reloading if not loaded
            self._load_model()
            if not self.lr_model:
                print("[Predictor] Models not loaded.")
                return None

        try:
            # Ensure all features exist
            for feat in self.features:
                if feat not in game_state:
                    game_state[feat] = 0.0

            X_df = pd.DataFrame([game_state])[self.features]
            
            # LR prediction
            X_scaled = self.scaler.transform(X_df)
            lr_prob = self.lr_model.predict_proba(X_scaled)[0, 1]
            
            # XGB prediction
            xgb_prob = self.xgb_model.predict_proba(X_df)[0, 1]
            
            # Ensemble (Average)
            final_prob = (lr_prob + xgb_prob) / 2.0
            print(f"[Predictor] State: {game_state} -> Prob: {final_prob:.4f}")
            return final_prob
        except Exception as e:
            print(f"[Predictor] Prediction error: {e}")
            return None

# Global predictor instance
predictor = WinPredictor()

def get_win_probability(game, pbp=None, strength_map=None) -> float | None:
    """Helper to prepare game state and get prediction."""
    # Convert game dict to object-like if necessary
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
        except:
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

    # 5. Strength Diff (Anchor)
    h_rank = getattr(game_obj.home, "rank", None) or 50
    a_rank = getattr(game_obj.away, "rank", None) or 50
    ranking_diff = (a_rank - h_rank) / 4.0

    if status == "pre":
        # Blend ranking diff (60%) + win% diff (40%) for better pre-game signal
        h_rec = getattr(game_obj.home, "record", "0-0") or "0-0"
        a_rec = getattr(game_obj.away, "record", "0-0") or "0-0"
        record_diff = (_parse_win_pct(h_rec) - _parse_win_pct(a_rec)) * 10
        strength_diff = (ranking_diff * 0.6) + (record_diff * 0.4)
    else:
        strength_diff = ranking_diff

    state = {
        "score_diff": float(score_diff),
        "momentum": float(momentum),
        "strength_diff": float(strength_diff),
        "time_ratio": float(time_ratio),
        "mins_remaining": float(total_mins_remaining),
        "period": float(period)
    }
    
    result = predictor.predict(state)
    if result is not None and status == "pre":
        is_neutral = getattr(game_obj, "neutral_site", False)
        if not is_neutral:
            result = min(0.95, max(0.05, result + 0.03))
    return result
