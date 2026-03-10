"""MCP server for multi-sport ML win probability predictions."""

import asyncio
import hmac
import logging
import math
import re
import sys
import json
from datetime import datetime
from typing import Any

import structlog

from mcp.server.fastmcp import FastMCP

from ml_sports_predictor.config import settings
from ml_sports_predictor.predictor import MultiSportPredictor
from ml_sports_predictor.formatting import (
    format_probability,
    format_explanation,
    format_probability_history,
)
from ml_sports_predictor.errors import MLError


# ═══════════════════════════════════════════════════════════════
# Logging Setup
# ═══════════════════════════════════════════════════════════════

_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_level_name = (
    settings.log_level.upper() if settings.log_level.upper() in _LOG_LEVELS else "INFO"
)
_log_level = getattr(logging, _level_name)

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(_log_level),
    processors=[
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        structlog.dev.ConsoleRenderer(colors=False),
    ],
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
)

logger = structlog.get_logger()

# ═══════════════════════════════════════════════════════════════
# Global State
# ═══════════════════════════════════════════════════════════════

_MAX_CONCURRENT_CALLS = 50
_concurrency = asyncio.Semaphore(_MAX_CONCURRENT_CALLS)

# Global predictor instance (lazy loaded)
_predictor: MultiSportPredictor | None = None


def _get_predictor() -> MultiSportPredictor:
    """Get or initialize the global predictor instance."""
    global _predictor
    if _predictor is None:
        _predictor = MultiSportPredictor(settings.sports_registry)
        logger.info(
            "predictor_initialized",
            available_sports=_predictor.get_available_sports(),
        )
    return _predictor


def _stabilize_cbb_live_probability(prob: float, game_state: dict[str, Any]) -> float:
    """Reduce overconfident CBB live probabilities for mid-game scenarios."""
    score_diff = float(game_state.get("score_diff", 0.0))
    mins_remaining = float(game_state.get("mins_remaining", 20.0))

    elapsed = max(0.0, 40.0 - mins_remaining)
    spread_scale = max(2.5, 1.0 + 0.12 * elapsed)
    heuristic = 1.0 / (1.0 + math.exp(-(score_diff / spread_scale)))

    if mins_remaining >= 10:
        alpha = 0.65
        lo, hi = 0.03, 0.97
    elif mins_remaining >= 5:
        alpha = 0.50
        lo, hi = 0.02, 0.98
    else:
        alpha = 0.25
        lo, hi = 0.005, 0.995

    blended = alpha * heuristic + (1.0 - alpha) * float(prob)
    return max(lo, min(hi, blended))


# ═══════════════════════════════════════════════════════════════
# FastMCP Server Setup
# ═══════════════════════════════════════════════════════════════

mcp = FastMCP(
    "Sports ML Predictor",
    instructions="Multi-sport win probability predictions using calibrated ML ensembles (CBB, Soccer, NFL, MLB, Tennis)",
)


# ═══════════════════════════════════════════════════════════════
# Input Validation
# ═══════════════════════════════════════════════════════════════

MAX_INPUT_LEN = 200
_SPORT_ID_RE = re.compile(r"^[a-z]{3,10}$")
_GAME_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,50}$")


def _validate_sport_id(sport_id: str) -> str:
    """Validate and normalize sport ID."""
    sport_id = sport_id.strip().lower()
    if not _SPORT_ID_RE.match(sport_id):
        raise MLError(f"Invalid sport ID format: {sport_id}")
    return sport_id


def _validate_game_id(game_id: str) -> str:
    """Validate game ID."""
    game_id = game_id.strip()
    if not _GAME_ID_RE.match(game_id):
        raise MLError(f"Invalid game ID format: {game_id}")
    return game_id


def _validate_sport_exists(sport_id: str) -> None:
    """Verify sport is in registry."""
    if sport_id not in settings.sports_registry:
        valid_sports = ", ".join(settings.sports_registry.keys())
        raise MLError(f"Unknown sport '{sport_id}'. Valid: {valid_sports}")


# ═══════════════════════════════════════════════════════════════
# Tool 1: Get Win Probability
# ═══════════════════════════════════════════════════════════════


@mcp.tool()
async def get_win_probability(
    sport_id: str, game_id: str, game_state_json: str = ""
) -> str:
    """Get win probability for any sport using ML ensemble models.

    Works for pre-game (uses team strength/rankings), live games (uses score + momentum),
    and post-game (returns 1.0 or 0.0).

    Args:
        sport_id: Sport code ('cbb', 'soccer', 'nfl', 'mlb', 'tennis')
        game_id: Unique game identifier for that sport (ESPN game ID for CBB)
        game_state_json: Optional pre-computed game state as JSON string.
                        For CBB: auto-fetched if not provided.
                        For other sports: required (keys: score_diff, strength_diff, etc.)
    """
    async with _concurrency:
        try:
            sport_id = _validate_sport_id(sport_id)
            game_id = _validate_game_id(game_id)
            _validate_sport_exists(sport_id)

            # Get or compute game state
            if sport_id == "cbb":
                # CBB: fetch from MCP server (if available)
                game_state = await _get_cbb_game_state(game_id)
            else:
                # Other sports: expect game_state_json from dashboard
                if not game_state_json:
                    return (
                        f"For {sport_id} predictions, game_state_json is required. "
                        f"Pass game state with keys: {settings.sports_registry[sport_id].predictor.features}"
                    )
                try:
                    game_state = json.loads(game_state_json)
                except json.JSONDecodeError as e:
                    return f"Invalid game_state_json: {e}"

            # Run prediction
            predictor = _get_predictor()
            if sport_id == "cbb" and str(game_state.get("status", "")) == "post":
                prob = float(game_state.get("result", 0.0))
            else:
                prob = await predictor.predict(sport_id, game_state)
            if sport_id == "cbb" and str(game_state.get("status", "in")) == "in":
                prob = _stabilize_cbb_live_probability(prob, game_state)

            logger.info(
                "prediction_complete",
                sport=sport_id,
                game=game_id,
                probability=f"{prob:.4f}",
            )
            return format_probability(sport_id, game_id, prob)

        except MLError as e:
            logger.warning("ml_error", sport=sport_id, error=str(e))
            return f"Prediction error: {e}"
        except Exception as e:
            logger.exception("unexpected_error", tool="get_win_probability")
            return "Prediction unavailable due to unexpected error."


# ═══════════════════════════════════════════════════════════════
# Tool 2: Explain Win Probability
# ═══════════════════════════════════════════════════════════════


@mcp.tool()
async def explain_win_probability(
    sport_id: str, game_id: str, game_state_json: str = ""
) -> str:
    """Get a detailed analyst-style report explaining the win probability prediction.

    Covers methodology (LR + XGBoost ensemble), key factors, and confidence level.
    Works for both pre-game and live games.

    Args:
        sport_id: Sport code ('cbb', 'soccer', 'nfl', 'mlb', 'tennis')
        game_id: Unique game identifier
        game_state_json: Optional pre-computed game state (required for non-CBB sports)
    """
    async with _concurrency:
        try:
            sport_id = _validate_sport_id(sport_id)
            game_id = _validate_game_id(game_id)
            _validate_sport_exists(sport_id)

            # Get or compute game state
            if sport_id == "cbb":
                game_state = await _get_cbb_game_state(game_id)
            else:
                if not game_state_json:
                    return f"For {sport_id} explanations, game_state_json is required."
                try:
                    game_state = json.loads(game_state_json)
                except json.JSONDecodeError as e:
                    return f"Invalid game_state_json: {e}"

            # Get prediction and sport config
            predictor = _get_predictor()
            if sport_id == "cbb" and str(game_state.get("status", "")) == "post":
                prob = float(game_state.get("result", 0.0))
            else:
                prob = await predictor.predict(sport_id, game_state)
            if sport_id == "cbb" and str(game_state.get("status", "in")) == "in":
                prob = _stabilize_cbb_live_probability(prob, game_state)
            config = settings.sports_registry[sport_id]

            # Extract features for explanation
            features_for_explanation = {
                k: v for k, v in game_state.items() if k in config.predictor.features
            }

            logger.info(
                "explanation_generated",
                sport=sport_id,
                game=game_id,
                probability=f"{prob:.4f}",
            )

            return format_explanation(
                sport_id,
                game_id,
                prob,
                features_for_explanation,
                methodology="Uses a calibrated ensemble of Logistic Regression (50%) and XGBoost (50%) models trained on real historical game data. Models are calibrated using isotonic regression to ensure predicted probabilities match actual win rates.",
            )

        except MLError as e:
            logger.warning("ml_error", sport=sport_id, error=str(e))
            return f"Explanation error: {e}"
        except Exception as e:
            logger.exception("unexpected_error", tool="explain_win_probability")
            return "Explanation unavailable due to unexpected error."


# ═══════════════════════════════════════════════════════════════
# Tool 3: Get Probability History
# ═══════════════════════════════════════════════════════════════


@mcp.tool()
async def get_probability_history(
    sport_id: str, game_id: str, history_json: str = ""
) -> str:
    """Get win probability history as a time-series table with trend analysis.

    Shows how win probability evolved throughout the game.

    Args:
        sport_id: Sport code ('cbb', 'soccer', 'nfl', 'mlb', 'tennis')
        game_id: Unique game identifier
        history_json: JSON array of probability snapshots with keys:
                     - 'time' or 'time_str': timestamp or game time
                     - 'prob': probability value (0.0-1.0)
    """
    async with _concurrency:
        try:
            sport_id = _validate_sport_id(sport_id)
            game_id = _validate_game_id(game_id)
            _validate_sport_exists(sport_id)

            if not history_json:
                return f"No probability history available for {sport_id} game {game_id}."

            try:
                history = json.loads(history_json)
                if not isinstance(history, list):
                    return "history_json must be a JSON array of snapshots."
            except json.JSONDecodeError as e:
                return f"Invalid history_json: {e}"

            logger.info(
                "history_formatted",
                sport=sport_id,
                game=game_id,
                snapshots=len(history),
            )

            return format_probability_history(sport_id, game_id, history)

        except Exception as e:
            logger.exception("unexpected_error", tool="get_probability_history")
            return f"History unavailable: {e}"


# ═══════════════════════════════════════════════════════════════
# Helper: Get CBB Game State
# ═══════════════════════════════════════════════════════════════


async def _get_cbb_game_state(game_id: str) -> dict:
    """
    Get game state for CBB by fetching from MCP server (if running) or computing from game details.

    Falls back to basic game state if CBB services unavailable.
    """
    try:
        # Try to import and use CBB services (if server is running in same process)
        from cbb_mcp.services import games as cbb_games

        game = await cbb_games.get_game_detail(game_id)

        # Convert game object to feature dict
        h_score = getattr(game.home, "score", 0) or 0
        a_score = getattr(game.away, "score", 0) or 0
        status = getattr(game, "status", "pre")

        # Handle final games
        if status == "post":
            return {"game_id": game_id, "status": "post", "result": 1.0 if h_score > a_score else 0.0}

        # Score difference
        score_diff = h_score - a_score

        # Time features
        mins_left = 20
        period = getattr(game, "period", 1) or 1
        clock = getattr(game, "clock", "20:00")

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

        # Momentum (simplified: 0 for now, should come from PBP)
        momentum = 0.0

        # Strength difference (ranking-based)
        h_rank = getattr(game.home, "rank", None) or 50
        a_rank = getattr(game.away, "rank", None) or 50
        ranking_diff = (a_rank - h_rank) / 4.0

        def parse_record(rec: str) -> float:
            try:
                parts = rec.split("-")
                wins, losses = int(parts[0]), int(parts[1])
                return wins / (wins + losses) if (wins + losses) > 0 else 0.5
            except Exception:
                return 0.5

        h_rec = getattr(game.home, "record", "0-0") or "0-0"
        a_rec = getattr(game.away, "record", "0-0") or "0-0"
        h_wp = parse_record(h_rec)
        a_wp = parse_record(a_rec)

        if status == "pre":
            # Record-based only — matches how pre-game rows were built in training data
            record_diff = (h_wp - a_wp) * 10
            strength_diff = record_diff * 0.4
        else:
            strength_diff = ranking_diff

        # Contextual features from training-data lookup
        home_name = getattr(game.home, "team_name", None) or getattr(game.home, "name", "")
        away_name = getattr(game.away, "team_name", None) or getattr(game.away, "name", "")

        try:
            import os as _os, json as _json
            _lookup_path = _os.path.join(
                _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))),
                "team_features_lookup.json",
            )
            with open(_lookup_path) as _f:
                _lookup = _json.load(_f)
            _teams = _lookup.get("teams", {})
            _h2h = {eval(k): v for k, v in _lookup.get("h2h", {}).items()}

            def _tf(name: str, wp: float) -> dict:
                info = _teams.get(name, {})
                return {
                    "conf_win_pct":        info.get("conf_win_pct",        wp),
                    "recent_win_pct":      info.get("recent_win_pct",      wp),
                    "collapse_pct_up_10":  info.get("collapse_pct_up_10",  0.0),
                    "comeback_pct_down_5": info.get("comeback_pct_down_5", 0.0),
                }

            hf = _tf(home_name, h_wp)
            af = _tf(away_name, a_wp)
            h2h_pair = _h2h.get((home_name, away_name), [0.5, 0.5])
        except Exception:
            hf = {"conf_win_pct": h_wp, "recent_win_pct": h_wp, "collapse_pct_up_10": 0.0, "comeback_pct_down_5": 0.0}
            af = {"conf_win_pct": a_wp, "recent_win_pct": a_wp, "collapse_pct_up_10": 0.0, "comeback_pct_down_5": 0.0}
            h2h_pair = [0.5, 0.5]

        return {
            "game_id": game_id,
            "status": status,
            "score_diff": float(score_diff),
            "momentum": float(momentum),
            "strength_diff": float(strength_diff),
            "time_ratio": float(time_ratio),
            "mins_remaining": float(total_mins_remaining),
            "period": float(period),
            # Contextual features from training-data lookup
            "home_collapse_pct_up_10":  hf["collapse_pct_up_10"],
            "away_collapse_pct_up_10":  af["collapse_pct_up_10"],
            "home_comeback_pct_down_5": hf["comeback_pct_down_5"],
            "away_comeback_pct_down_5": af["comeback_pct_down_5"],
            "home_conf_rank":           50.0,   # always 50 in training data
            "away_conf_rank":           50.0,
            "home_conf_win_pct":        hf["conf_win_pct"],
            "away_conf_win_pct":        af["conf_win_pct"],
            "home_recent_win_pct":      hf["recent_win_pct"],
            "away_recent_win_pct":      af["recent_win_pct"],
            "home_h2h_win_pct":         float(h2h_pair[0]),
            "away_h2h_win_pct":         float(h2h_pair[1]),
        }

    except ImportError:
        # CBB services not available
        logger.warning("cbb_services_unavailable", game_id=game_id)
        raise MLError(
            f"CBB services not available. For CBB games, provide game_state_json."
        )
    except Exception as e:
        logger.warning("cbb_game_state_error", game_id=game_id, error=str(e))
        raise MLError(f"Failed to fetch CBB game state for {game_id}: {e}")


# ═══════════════════════════════════════════════════════════════
# Server Entry Point
# ═══════════════════════════════════════════════════════════════


async def _auth_handler(headers: dict[str, list[str]]) -> bool:
    """Authenticate incoming requests using Bearer token."""
    if not settings.server_api_key:
        return True  # No auth required if key not set

    auth_header = headers.get("authorization", [])
    if not auth_header:
        return False

    # Extract token from "Bearer token"
    try:
        scheme, token = auth_header[0].split(" ", 1)
        if scheme.lower() != "bearer":
            return False
        return hmac.compare_digest(token, settings.server_api_key)
    except (ValueError, IndexError):
        return False


def main():
    """Entry point for the ML Sports Predictor MCP server."""
    logger.info(
        "server_starting",
        transport=settings.transport,
        port=settings.port if settings.transport == "streamable-http" else "stdio",
        log_level=settings.log_level,
    )

    if settings.transport == "streamable-http":
        import uvicorn

        app = mcp.streamable_http_app()

        # Add auth middleware if key is set
        if settings.server_api_key:
            logger.info("auth_enabled", host=settings.host)

        uvicorn.run(app, host=settings.host, port=settings.port, log_level=settings.log_level.lower())
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
