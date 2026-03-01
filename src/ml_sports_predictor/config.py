"""ML Sports Predictor configuration via environment variables and YAML."""

import os
from typing import Literal
import yaml

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class PredictorConfig(BaseModel):
    """Per-sport predictor configuration."""

    features: list[str]
    model_path: str
    calibration: str
    ensemble_weights: dict[str, float]


class DataSourcesConfig(BaseModel):
    """Data source configuration for a sport."""

    primary: str
    fallback: list[str] = []


class SportConfig(BaseModel):
    """Per-sport configuration."""

    name: str
    game_duration_minutes: int
    period_count: int
    period_names: list[str]
    scoring_units: str
    typical_score_range: list[int]
    positions: list[str]
    conferences: list[str]
    ranking_systems: list[str]
    predictor: PredictorConfig
    data_sources: DataSourcesConfig


class Settings(BaseSettings):
    """ML Sports Predictor settings."""

    model_config = {"env_prefix": "ML_SPORTS_", "env_file": ".env", "extra": "ignore"}

    # Transport
    transport: Literal["stdio", "streamable-http"] = "stdio"
    host: str = "127.0.0.1"
    port: int = Field(default=8001, ge=1, le=65535)
    server_api_key: str = Field(default="", repr=False)

    # Cache
    cache_dir: str = ".cache_ml"
    cache_enabled: bool = True

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Sports registry (loaded from YAML)
    sports_registry_path: str = "src/ml_sports_predictor/sports_config.yaml"
    sports_registry: dict[str, SportConfig] = {}

    def __init__(self, **data):
        """Initialize settings and load sports registry from YAML."""
        super().__init__(**data)
        self._load_sports_registry()

    def _load_sports_registry(self):
        """Load sports configuration from YAML file."""
        # Try absolute path first, then relative
        yaml_path = self.sports_registry_path
        if not os.path.exists(yaml_path):
            # Try relative to current dir
            yaml_path = os.path.join(os.getcwd(), self.sports_registry_path)

        if not os.path.exists(yaml_path):
            raise FileNotFoundError(
                f"Sports config YAML not found at: {self.sports_registry_path} or {yaml_path}"
            )

        with open(yaml_path, "r") as f:
            config_data = yaml.safe_load(f)

        if not config_data or "sports" not in config_data:
            raise ValueError(f"Invalid sports config YAML at {yaml_path}")

        for sport_id, sport_config_dict in config_data["sports"].items():
            try:
                self.sports_registry[sport_id] = SportConfig(**sport_config_dict)
            except Exception as e:
                raise ValueError(f"Invalid config for sport '{sport_id}': {e}")

    def get_sport_config(self, sport_id: str) -> SportConfig:
        """Get configuration for a specific sport."""
        if sport_id not in self.sports_registry:
            raise ValueError(f"Unknown sport: {sport_id}")
        return self.sports_registry[sport_id]


settings = Settings()
