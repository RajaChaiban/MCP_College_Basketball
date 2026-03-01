"""Multi-sport predictor using calibrated ML ensemble models."""

from __future__ import annotations

import os
import logging
from typing import Optional

import joblib

from ml_sports_predictor.config import SportConfig
from ml_sports_predictor.errors import (
    ModelNotFoundError,
    ModelLoadError,
    PredictionError,
    GameStateError,
)


logger = logging.getLogger(__name__)


class MultiSportPredictor:
    """Load and manage ML models for multiple sports."""

    def __init__(self, sports_config: dict[str, SportConfig]):
        """
        Initialize the predictor with sport configurations.

        Args:
            sports_config: Dict mapping sport_id -> SportConfig
        """
        self.sports_config = sports_config
        self.models = {}  # {sport_id: bundle}
        self.load_all_models()

    def load_all_models(self):
        """Load all available sport models (non-blocking failures)."""
        for sport_id, config in self.sports_config.items():
            model_path = config.predictor.model_path
            try:
                if os.path.exists(model_path):
                    bundle = joblib.load(model_path)
                    self.models[sport_id] = bundle
                    logger.info(f"Loaded model for {sport_id}: {model_path}")
                else:
                    logger.warning(
                        f"Model not found for {sport_id}: {model_path} "
                        f"(feature {sport_id} will be unavailable)"
                    )
            except Exception as e:
                logger.warning(f"Failed to load {sport_id} model: {e}")

    async def predict(self, sport_id: str, game_state: dict) -> float:
        """
        Predict win probability for any sport.

        Args:
            sport_id: Sport identifier (e.g., 'cbb', 'soccer', 'nfl')
            game_state: Dict with game features (sport-specific)

        Returns:
            Probability (0.0 to 1.0) for home team winning

        Raises:
            PredictionError: If prediction fails
            GameStateError: If game state is invalid
        """
        if sport_id not in self.sports_config:
            raise PredictionError(sport_id, "unknown", f"Unknown sport: {sport_id}")

        if sport_id not in self.models:
            raise PredictionError(
                sport_id, "unknown", f"No model loaded for {sport_id}"
            )

        config = self.sports_config[sport_id]
        bundle = self.models[sport_id]

        try:
            # Validate game state has required features
            self._validate_game_state(sport_id, game_state, config)

            # Normalize features per sport
            normalized = self._normalize_features(sport_id, game_state, config)

            # Run predictions through both models
            return await self._ensemble_predict(bundle, normalized, config)

        except GameStateError:
            raise
        except Exception as e:
            raise PredictionError(
                sport_id, game_state.get("game_id", "unknown"), f"Prediction failed: {e}"
            )

    def _validate_game_state(
        self, sport_id: str, game_state: dict, config: SportConfig
    ) -> None:
        """Validate game state has at least one feature."""
        if not game_state:
            raise GameStateError(sport_id, "Empty game state")

        # At least one feature should be present
        required_features = config.predictor.features
        if not any(feat in game_state for feat in required_features):
            raise GameStateError(
                sport_id,
                f"Game state must contain at least one of: {required_features}",
            )

    def _normalize_features(
        self, sport_id: str, game_state: dict, config: SportConfig
    ) -> dict:
        """
        Normalize features for the sport.
        Handles score scaling, time ratios, and sport-specific mappings.
        """
        state = game_state.copy()

        min_score, max_score = config.typical_score_range

        # Normalize scoring differences (sport-specific names)
        scoring_diff_keys = ["score_diff", "goal_diff", "run_diff", "set_diff"]
        for key in scoring_diff_keys:
            if key in state:
                if max_score > 0:
                    state[key] = state[key] / max_score
                break  # Only normalize one scoring diff key

        # Normalize time ratio to [0, 1]
        if "time_ratio" in state:
            state["time_ratio"] = max(0.0, min(1.0, state["time_ratio"]))

        # Normalize momentum similarly to scoring difference
        if "momentum" in state:
            if max_score > 0:
                state["momentum"] = state["momentum"] / max_score

        # Ensure all required features exist (fill with 0.0)
        for feat in config.predictor.features:
            if feat not in state:
                state[feat] = 0.0

        return state

    async def _ensemble_predict(self, bundle: dict, normalized: dict, config: SportConfig) -> float:
        """Run ensemble prediction using LR and XGB models."""
        try:
            # Lazy import pandas (circular dependency prevention)
            import pandas as pd

            lr_model = bundle.get("lr_model")
            xgb_model = bundle.get("xgb_model")
            scaler = bundle.get("scaler")
            features = bundle.get("features", config.predictor.features)

            if not lr_model or not xgb_model or not scaler:
                raise PredictionError(
                    "unknown", "unknown", "Models not properly loaded (missing lr_model, xgb_model, or scaler)"
                )

            # Prepare feature dataframe
            X_df = pd.DataFrame([normalized])[features]

            # LR prediction (uses scaler)
            X_scaled = scaler.transform(X_df)
            lr_prob = float(lr_model.predict_proba(X_scaled)[0, 1])

            # XGB prediction (no scaling needed)
            xgb_prob = float(xgb_model.predict_proba(X_df)[0, 1])

            # Ensemble: weighted average
            weights = config.predictor.ensemble_weights
            ensemble_prob = (
                weights.get("lr", 0.5) * lr_prob + weights.get("xgb", 0.5) * xgb_prob
            )

            # Clamp to [0.0, 1.0]
            return max(0.0, min(1.0, ensemble_prob))

        except Exception as e:
            raise PredictionError("unknown", "unknown", f"Ensemble prediction failed: {e}")

    def get_available_sports(self) -> list[str]:
        """Get list of sports with loaded models."""
        return list(self.models.keys())

    def get_sport_info(self, sport_id: str) -> dict:
        """Get human-readable info about a sport."""
        if sport_id not in self.sports_config:
            return {}

        config = self.sports_config[sport_id]
        has_model = sport_id in self.models
        return {
            "name": config.name,
            "game_duration_minutes": config.game_duration_minutes,
            "scoring_units": config.scoring_units,
            "model_loaded": has_model,
            "features": config.predictor.features,
        }
