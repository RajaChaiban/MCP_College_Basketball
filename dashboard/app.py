"""
CBB Live Dashboard — entry point.

Usage:
    python dashboard/app.py
    # or
    python -m dashboard.app

Requires ANTHROPIC_API_KEY env var for AI chat.
Install dashboard dependencies: pip install -e ".[dashboard]"
"""

from __future__ import annotations

import os
import sys

# Ensure project root and src/ are on the path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_ROOT, "src")
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# Load .env file if present (before any other imports that read env vars)
_env_path = os.path.join(_ROOT, ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

import dash
import dash_bootstrap_components as dbc

from dashboard.layout import build_layout, register_layout_callbacks
from dashboard.callbacks.map_callbacks import register_map_callbacks
from dashboard.callbacks.game_callbacks import register_game_callbacks
from dashboard.callbacks.chat_callbacks import register_chat_callbacks
from dashboard.callbacks.rankings_callbacks import register_rankings_callbacks

# ── App init ──────────────────────────────────────────────────────────────────

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css",
        "https://fonts.googleapis.com/css2?family=Lexend:wght@300;400;700;900&display=swap",
    ],
    title="CBB Live Dashboard",
    suppress_callback_exceptions=True,
    update_title=None,
)

app.layout = build_layout()

# ── Register callbacks ────────────────────────────────────────────────────────

register_map_callbacks(app)
register_game_callbacks(app)
register_chat_callbacks(app)
register_rankings_callbacks(app)
register_layout_callbacks(app)

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        print(
            "\n[WARNING] GEMINI_API_KEY is not set.\n"
            "         AI chat will be disabled until you set it.\n"
            "         export GEMINI_API_KEY=AIza...\n"
        )

    debug = os.environ.get("CBB_DEBUG", "1") == "1"
    port = int(os.environ.get("CBB_DASH_PORT", "8050"))
    host = os.environ.get("CBB_DASH_HOST", "127.0.0.1")

    print(f"\n CBB Live Dashboard starting on http://{host}:{port}\n")
    app.run(debug=debug, host=host, port=port)
