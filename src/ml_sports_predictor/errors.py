"""Custom exception hierarchy for the ML Sports Predictor MCP server."""


class MLError(Exception):
    """Base exception for all ML prediction errors."""


class ModelNotFoundError(MLError):
    """Model file not found for a sport."""

    def __init__(self, sport_id: str, model_path: str):
        self.sport_id = sport_id
        super().__init__(f"Model not found for {sport_id}: {model_path}")


class ModelLoadError(MLError):
    """Failed to load a model."""

    def __init__(self, sport_id: str, message: str):
        self.sport_id = sport_id
        super().__init__(f"Failed to load {sport_id} model: {message}")


class PredictionError(MLError):
    """Error during prediction."""

    def __init__(self, sport_id: str, game_id: str, message: str):
        self.sport_id = sport_id
        self.game_id = game_id
        super().__init__(f"Prediction error for {sport_id} game {game_id}: {message}")


class GameStateError(MLError):
    """Invalid game state provided for prediction."""

    def __init__(self, sport_id: str, message: str):
        self.sport_id = sport_id
        super().__init__(f"Invalid game state for {sport_id}: {message}")


class UnsupportedSportError(MLError):
    """Sport is not supported."""

    def __init__(self, sport_id: str):
        super().__init__(f"Unsupported sport: {sport_id}")
