# CBB Predictive Dashboard

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**NCAA Men's D1 College Basketball — Live Dashboard + Predictive Win Probability Engine**

A full-stack Python application that combines a live college basketball data server with an interactive dashboard and an in-game win probability predictor. Watch games in real time on an interactive US map, explore box scores and play-by-play, and get live win probability powered by an ensemble ML model.

---

## Features

### Live Dashboard
- **Interactive US Map** — every D1 game plotted by venue with color-coded status (green = live, gray = final, blue = upcoming)
- **30-second auto-refresh** — live scores update automatically
- **Game panel** — click any marker to open a real-time box score and play-by-play feed
- **AP Top 25 + All Teams sidebar** — 362 D1 teams browsable by conference with instant search
- **AI Chat** — natural language queries backed by live data tools (scores, stats, rankings, comparisons)
- **Conference filter** — narrow the map to a single conference

### Predictive Engine
- **In-game win probability** — live percentage updated every 30 seconds using current score, time remaining, and game period
- **Ensemble model** — combines Logistic Regression (stable anchor) and XGBoost (non-linear patterns) with equal weighting
- **Features**: score differential, time ratio, minutes remaining, period
- **Training pipeline** — collect historical play-by-play snapshots and retrain with a single command
- **Model artifact** — saved as `cbb_predictor_bundle.joblib` (LR model + XGBoost + scaler + feature list)

### MCP Server (16 tools)
| Tool | Description |
|------|-------------|
| `get_live_scores` | Live/final scores for any date, filterable by conference or Top 25 |
| `get_team` | Look up any team by name (fuzzy matched) |
| `search_teams` | Search teams by name or conference |
| `get_team_roster` | Full roster with player details |
| `get_team_schedule` | Complete schedule with results |
| `get_game_detail` | Game info with scoring summary |
| `get_box_score` | Per-player and team box score |
| `get_play_by_play` | Play-by-play with timestamps |
| `get_rankings` | AP Top 25, Coaches Poll |
| `get_standings` | Conference standings with streaks |
| `get_team_stats` | Season team stats (PPG, FG%, RPG, etc.) |
| `get_player_stats` | Individual player stats for a team |
| `get_stat_leaders` | National stat leaders by category |
| `compare_teams` | Side-by-side team comparison |
| `get_games_by_date` | All games on a date with TV info |
| `get_tournament_bracket` | March Madness bracket and results |

---

## Project Structure

```
├── src/cbb_mcp/              # MCP server (data layer)
│   ├── server.py             # Tool registrations + entry point
│   ├── config.py             # Environment-based configuration
│   ├── services/             # Business logic (games, teams, rankings, stats)
│   ├── sources/              # ESPN, NCAA, sportsdataverse, cbbpy adapters
│   ├── models/               # Pydantic data models
│   └── utils/                # Cache, rate limiter, HTTP client
├── dashboard/                # Dash web application
│   ├── app.py                # Entry point
│   ├── layout.py             # Full page layout
│   ├── components/           # Map, game panel, rankings sidebar, chat
│   ├── callbacks/            # Dash reactive callbacks
│   ├── ai/                   # AI chat agent + tool dispatcher
│   ├── data/                 # Venue coordinates for all 362 D1 schools
│   └── scripts/
│       ├── collect_historical_data.py   # Fetch play-by-play training data
│       ├── train_predictor.py           # Train + save ensemble model
│       └── build_venue_coords.py        # Geocode venue locations
├── tests/                    # 51 unit tests
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

---

## Quick Start

### Install

```bash
git clone https://github.com/RajaChaiban/CBB_Predictive_Dashboard.git
cd CBB_Predictive_Dashboard
pip install -e ".[dashboard]"
```

### Configure

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Key variables:

| Variable | Description |
|----------|-------------|
| `AI_API_KEY` | API key for the AI chat backend |
| `AI_MODEL` | Model name to use for chat |
| `CBB_DASH_PORT` | Dashboard port (default `8050`) |
| `CBB_TRANSPORT` | `stdio` or `streamable-http` |

### Run the Dashboard

```bash
python dashboard/app.py
```

Open `http://localhost:8050` in your browser.

---

## Predictive Engine

### 1. Collect Training Data

Fetches historical play-by-play snapshots and saves them as a CSV:

```bash
python dashboard/scripts/collect_historical_data.py \
  --start 2024-11-01 \
  --end 2025-03-01 \
  --output cbb_training_data.csv
```

Each row is a game snapshot with: `score_diff`, `time_ratio`, `mins_remaining`, `period`, `is_home_win`.

### 2. Train the Model

```bash
python dashboard/scripts/train_predictor.py --input cbb_training_data.csv
```

Outputs:
- Logistic Regression accuracy + Brier score
- XGBoost accuracy + Brier score
- Ensemble accuracy + Brier score
- `cbb_predictor_bundle.joblib` — the saved model bundle

### 3. Live Predictions

Once `cbb_predictor_bundle.joblib` exists in the project root, the dashboard automatically loads it and displays win probability on every live game marker and in the game panel. Probabilities update every 30 seconds with the live score refresh.

### How It Works

```
Live Score (ESPN)
    │
    ▼
score_diff = home_score - away_score
time_ratio = elapsed_time / total_game_time
mins_remaining = minutes left in game
period = 1st half / 2nd half / OT
    │
    ▼
Logistic Regression ──┐
                       ├── average → Win Probability %
XGBoost ──────────────┘
```

---

## Data Sources

All sources are free and require no API keys:

| Source | What it provides |
|--------|-----------------|
| ESPN Hidden API | Live scores, teams, rankings, standings, schedules, box scores |
| NCAA API | Scores, rankings, game details |
| sportsdataverse | Historical play-by-play, team/player box scores |
| cbbpy | Box scores, play-by-play, schedules |

The server tries ESPN first (most comprehensive), then falls back automatically.

---

## Remote Hosting (HTTP)

```bash
CBB_TRANSPORT=streamable-http python -m cbb_mcp.server

# With API key authentication
CBB_TRANSPORT=streamable-http CBB_SERVER_API_KEY=your-secret python -m cbb_mcp.server
```

### Docker

```bash
docker build -t cbb-dashboard .
docker run -p 8000:8000 -p 8050:8050 cbb-dashboard

# Or with docker-compose
docker compose up
```

---

## Configuration

All config via environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `CBB_TRANSPORT` | `stdio` | `stdio` or `streamable-http` |
| `CBB_HOST` | `127.0.0.1` | MCP server bind address |
| `CBB_PORT` | `8000` | MCP server port |
| `CBB_SERVER_API_KEY` | *(empty)* | Bearer token for HTTP auth |
| `CBB_DASH_HOST` | `127.0.0.1` | Dashboard bind address |
| `CBB_DASH_PORT` | `8050` | Dashboard port |
| `CBB_CACHE_ENABLED` | `true` | Enable/disable caching |
| `CBB_CACHE_DIR` | `.cache` | Disk cache directory |
| `CBB_LOG_LEVEL` | `INFO` | Logging level |
| `CBB_ESPN_RATE_LIMIT` | `10` | ESPN requests/sec |
| `CBB_NCAA_RATE_LIMIT` | `5` | NCAA requests/sec |

---

## Development

```bash
pip install -e ".[dev]"
pytest
```

51 tests covering services, models, caching, rate limiting, and source fallback logic.

---

## Security

- All inputs validated and length-limited
- HTTP auth uses timing-safe comparison
- API keys never logged or returned in responses
- HTTP responses capped at 5 MB
- Non-root Docker user

---

## License

MIT
