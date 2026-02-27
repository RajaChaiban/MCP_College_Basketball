# CBB Predictive Dashboard — Codebase Summary

**Purpose**: Multi-agent reference document for Claude and Gemini to understand the project structure, architecture, and collaboration points.

---

## Executive Overview

**CBB Predictive Dashboard** is a full-stack Python application that provides:
- **Live NCAA Men's D1 Basketball Dashboard** with interactive US map, box scores, play-by-play, and rankings
- **MCP (Model Context Protocol) Server** with 16 data tools for fetching live scores, teams, stats, and rankings
- **Predictive Win Probability Engine** using ensemble ML models (Logistic Regression + XGBoost)
- **AI Chat Agent** powered by Gemini with function calling for natural language queries

**Tech Stack**: Python 3.11+, FastMCP, Dash, Plotly, aiohttp, structlog, uvicorn

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                 CBB Dashboard (Dash)                     │
│  - Interactive US map with live game markers            │
│  - Game panel (box scores, play-by-play)               │
│  - Rankings sidebar (AP Top 25 + all teams)            │
│  - AI Chat panel (Gemini agent with tool calling)      │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    ┌────▼──────┐        ┌──────▼────┐
    │ MCP Server│        │ML Predictor│
    │(FastMCP)  │        │  (Joblib)  │
    └────┬──────┘        └────────────┘
         │
    ┌────▼────────────────────────────────────┐
    │  Multi-Source Data Resolution Layer     │
    │  Priority: ESPN → NCAA → SportsDV → CBBpy
    └────┬────────────────────────────────────┘
         │
    ┌────▼────────────────────────────────────┐
    │  Services Layer (Games, Teams, Ranks)   │
    │  + Caching (2-layer: memory + disk)    │
    │  + Rate Limiting (per-source)          │
    │  + HTTP Client (shared, 5MB limit)     │
    └────┬────────────────────────────────────┘
         │
    ┌────▼────────────────────────────────────┐
    │  Data Sources                           │
    │  ├─ ESPN (primary)                      │
    │  ├─ NCAA API                            │
    │  ├─ SportsDV (historical data)         │
    │  └─ CBBpy (fallback)                   │
    └─────────────────────────────────────────┘
```

---

## Project Structure

```
CBB_Predictive_Dashboard/
├── src/cbb_mcp/                    # MCP Server (3,728 lines)
│   ├── server.py                   # Tool registrations, auth, entry point
│   ├── config.py                   # Pydantic settings (env prefix: CBB_)
│   ├── models/                     # Data models
│   │   ├── common.py               # Base Pydantic models
│   │   ├── games.py                # Game, BoxScore, PlayByPlay
│   │   ├── teams.py                # Team, Player, Roster
│   │   ├── rankings.py             # RankingEntry, Poll
│   │   └── stats.py                # StatsPage, LeaderEntry
│   ├── services/                   # Business logic
│   │   ├── resolver.py             # Source priority + fallback chain
│   │   ├── games.py                # get_live_scores, get_game_detail, etc.
│   │   ├── teams.py                # get_team, search_teams, get_roster, etc.
│   │   ├── rankings.py             # get_rankings, get_standings
│   │   └── stats.py                # get_team_stats, get_player_stats, etc.
│   ├── sources/                    # Data adapters
│   │   ├── base.py                 # DataSource ABC, DataCapability enum
│   │   ├── espn.py                 # ESPNSource (ESPN hidden API)
│   │   ├── ncaa.py                 # NCAASource (NCAA official API)
│   │   ├── sportsdataverse.py      # SportsdataverseSource (historical)
│   │   └── cbbpy_source.py         # CbbpySource (fallback)
│   └── utils/                      # Infrastructure
│       ├── cache.py                # 2-layer cache (memory + disk, LRU)
│       ├── http_client.py          # Shared aiohttp session, 5MB limit
│       ├── rate_limiter.py         # Token bucket per source
│       ├── errors.py               # CBBError, SourceError, AllSourcesFailedError
│       ├── constants.py            # ESPN_CONFERENCES, CURRENT_SEASON
│       └── formatting.py           # Date/time utilities
│
├── dashboard/                      # Dash Web App (2,557 lines)
│   ├── app.py                      # Entry point, app init, callbacks
│   ├── layout.py                   # Page layout builder
│   ├── components/                 # Reusable UI components
│   │   ├── map_view.py             # Plotly choropleth map + scatter
│   │   ├── game_panel.py           # Game details, box score, play-by-play
│   │   ├── rankings_sidebar.py     # AP Top 25 + all teams browser
│   │   └── chat_panel.py           # Chat input/output UI
│   ├── callbacks/                  # Dash reactive handlers
│   │   ├── map_callbacks.py        # Map marker clicks, hover, filter
│   │   ├── game_callbacks.py       # Game panel updates
│   │   ├── chat_callbacks.py       # Chat message submission + streaming
│   │   └── rankings_callbacks.py   # Rankings search + click
│   ├── ai/                         # AI Agent Layer
│   │   ├── agent.py                # Gemini agentic loop (function calling)
│   │   ├── mcp_client.py           # MCP client to fetch tool definitions
│   │   ├── tools.py                # Tool dispatcher + Gemini schema builder
│   ├── data/                       # Venue data + geocoding
│   │   ├── venue_coordinates.py    # 362 D1 school coordinates (lat/lon)
│   │   └── geocoder.py             # Geocoding utilities (geopy wrapper)
│   └── scripts/                    # Data pipeline scripts
│       ├── collect_historical_data.py  # Fetch play-by-play snapshots (training)
│       ├── train_predictor.py          # Ensemble ML model training + save
│       └── build_venue_coords.py       # Generate venue_coordinates.py
│
├── tests/                          # 51 unit tests (829 lines)
│   ├── test_services/              # Service logic tests
│   ├── test_models/                # Model validation tests
│   ├── test_sources/               # Source adapter tests
│   ├── test_utils/                 # Cache, limiter, formatting tests
│   └── fixtures/                   # Mock data, test helpers
│
├── pyproject.toml                  # Dependencies, entry point
├── Dockerfile                      # Production container
├── docker-compose.yml              # Multi-container setup
├── smithery.yaml                   # Smithery cloud deployment config
└── README.md                       # User documentation

**Code Metrics**:
- Total: ~6,300 lines
- MCP Server: 3,728 lines
- Dashboard: 2,557 lines
- Tests: 829 lines

---

## MCP Server: 16 Tools

The MCP server (`src/cbb_mcp/server.py`) exposes 16 tools for fetching college basketball data:

### Team Tools
- **`get_team(team_name: str)`** — Fuzzy match and return team by name (ID, record, conference, venue)
- **`search_teams(query: str, conference: str = "")`** — Search teams by name or conference
- **`get_team_roster(team_name: str)`** — Full roster with player details

### Schedule & Games
- **`get_team_schedule(team_name: str, season: int = 0)`** — Complete schedule with results
- **`get_live_scores(date: str = "", conference: str = "", top25_only: bool = False)`** — Live/final scores
- **`get_games_by_date(date: str = "", conference: str = "")`** — All games on a date with TV info
- **`get_game_detail(game_id: str)`** — Game info with scoring summary
- **`get_box_score(game_id: str)`** — Per-player and team box score
- **`get_play_by_play(game_id: str, last_n: int = 20)`** — Play-by-play with timestamps

### Rankings & Standings
- **`get_rankings(poll: str = "ap", season: int = 0, week: int = 0)`** — AP Top 25, Coaches Poll
- **`get_standings(conference: str = "")`** — Conference standings with streaks
- **`get_tournament_bracket(season: int = 0)`** — March Madness bracket and results

### Statistics
- **`get_team_stats(team_name: str, season: int = 0)`** — Season team stats (PPG, FG%, RPG, etc.)
- **`get_player_stats(team_name: str)`** — Individual player stats for a team
- **`get_stat_leaders(category: str = "scoring", season: int = 0)`** — National stat leaders by category
- **`compare_teams(team1: str, team2: str)`** — Side-by-side team comparison

**All tools**:
- Validate and sanitize inputs (max 200 char for text, strict game ID format)
- Return JSON-serializable Pydantic models
- Wrapped with `_concurrency` semaphore (max 50 concurrent calls)
- Catch all exceptions and return user-friendly error messages (no stack trace leakage)

---

## Data Sources & Fallback Chain

**Resolver Pattern** (`src/cbb_mcp/services/resolver.py`):
Tries each source in priority order; if one fails, moves to the next.

### Source Priority
1. **ESPN** (priority 1) — Most comprehensive, lowest latency
   - Uses ESPN hidden API (unofficial but reliable)
   - Rate limit: 10 req/sec (configurable via `CBB_ESPN_RATE_LIMIT`)
   - Primary for live scores, teams, schedules, box scores

2. **NCAA** (priority 2) — Official API, slower
   - Rate limit: 5 req/sec (configurable)
   - Fallback for rankings, schedules, standings

3. **SportsDV** (priority 3) — Historical and detailed play-by-play
   - Rate limit: 5 req/sec
   - Used for training data collection

4. **CBBpy** (priority 4) — Last resort
   - Slow, limited scope
   - Rate limit: 3 req/sec

Each source implements the `DataSource` ABC with:
- `priority` (int) — lower = tried first
- `capabilities()` → set of `DataCapability` enums it supports
- Methods: `get_live_scores()`, `get_team()`, `search_teams()`, `get_roster()`, etc.

### Caching Strategy
**Two-layer cache** (`src/cbb_mcp/utils/cache.py`):
- **Layer 1: In-memory (LRU)** — Fast, 1,000 entry cap
- **Layer 2: Disk** — Persistent across restarts, `.cache/` directory
- **TTL (Time-to-Live)**:
  - Live scores: 30 sec
  - Team/roster: 24 hours
  - Rankings: 4 hours
  - Stats: 24 hours

### Rate Limiting
**Token-bucket algorithm** per source (`src/cbb_mcp/utils/rate_limiter.py`):
- Prevents hammer abuse
- Respects ESPN, NCAA, etc. rate policies
- Env var config: `CBB_ESPN_RATE_LIMIT`, `CBB_NCAA_RATE_LIMIT`, etc.

---

## Predictive Engine: Win Probability

**Model Bundle**: `cbb_predictor_bundle.joblib` (saved in project root)

### Pipeline
1. **Data Collection** (`dashboard/scripts/collect_historical_data.py`)
   - Fetches play-by-play snapshots from historical games
   - Features: `score_diff`, `momentum`, `strength_diff`, `time_ratio`, `mins_remaining`, `period`, `is_home_win`
   - **New**: `strength_diff` (Team PPG differential) and `momentum` (score change in last 4 mins)
   - Output: CSV training data

2. **Training** (`dashboard/scripts/train_predictor.py`)
   - **Calibrated Logistic Regression** — Stable baseline, isotonic calibration for reliable probabilities
   - **Calibrated XGBoost** — Captures non-linear patterns with isotonic calibration
   - **Ensemble** — Average of calibrated models
   - **Validation**: Brier score (measures probability accuracy)
   - Outputs: Accuracy, Brier score, saved calibrated joblib bundle

3. **Live Prediction** (Dashboard)
   - Loaded from joblib on app startup
   - Invoked every 30 sec as live scores update
   - Displayed on map markers and in game panel

### Features Used
- `score_diff` — Current score differential (home - away)
- `momentum` — Score change over the last 4 minutes of game time
- `strength_diff` — Pre-game strength gap (Home PPG Diff - Away PPG Diff)
- `time_ratio` — Elapsed game time / total game time (0.0 to 1.0+)
- `mins_remaining` — Minutes left in current period
- `period` — 1 = 1st half, 2 = 2nd half, 3+ = OT

### Output
- Win probability % (0–100) updated live for every game

---

## AI Chat Agent (Gemini)

**Chat Backend** (`dashboard/ai/agent.py`):
- Uses Google Generai SDK with function calling
- Agentic loop: `function_call` → `function_response` (up to 10 rounds)
- Streams responses directly to the Dash UI

### Tool Integration
**Tool Dispatcher** (`dashboard/ai/tools.py`):
1. Fetches MCP tool definitions from the server
2. Converts to Gemini function schema
3. Dispatches function calls to `dispatch_tool(tool_name, kwargs)`
4. Returns results as JSON strings

### System Prompt
> "You are a knowledgeable NCAA Men's Division I college basketball analyst. Use tools to fetch current data. Be concise. Format stats clearly with markdown tables."

### Context Awareness
- Game context (selected game ID, selected team)
- Passed to Gemini to let it reference the current user view

---

## Dashboard Components

### Map View (`dashboard/components/map_view.py`)
- **Plotly Choropleth** — US states with score distribution
- **Scatter Markers** — Every D1 game plotted by venue (lat/lon)
- **Color coding**:
  - Green = Live game
  - Gray = Final
  - Blue = Upcoming
- **Win Probability Badge** — Green/red overlay showing ensemble model prediction
- **Interactive**: Click marker → open game panel

### Game Panel (`dashboard/components/game_panel.py`)
- **Live scoreboard** (teams, scores, time remaining, period)
- **Box score tabs** (home team, away team)
- **Play-by-play feed** — Last 20 plays with timestamps
- **30-second auto-refresh**

### Rankings Sidebar (`dashboard/components/rankings_sidebar.py`)
- **AP Top 25 browser** — With conference icons
- **All 362 D1 teams** — Searchable by name/conference
- **Click to view team** → Loads team stats

### Chat Panel (`dashboard/components/chat_panel.py`)
- **Input field** — Natural language queries
- **Message history** — With Gemini responses
- **Streaming UI** — Shows "Assistant is typing..."

---

## Key Patterns & Conventions

### Error Handling
- Custom exception hierarchy: `CBBError` → `SourceError`, `AllSourcesFailedError`
- All tool handlers catch bare `Exception` to prevent stack trace leakage
- User-friendly error messages returned in JSON

### Async/Concurrency
- All services use async/await
- Global `_concurrency` semaphore (50 max in-flight calls)
- aiohttp session shared across all HTTP calls

### Input Validation
- All tool inputs validated with `_sanitize_text()`, `_validate_date()`, etc.
- Max input length: 200 characters
- Game IDs must match alphanumeric regex

### Logging
- Structured logging via `structlog`
- Configurable log level: `CBB_LOG_LEVEL` (default INFO)
- No API keys or sensitive data logged

### Configuration
- All config via environment variables
- Prefix: `CBB_` (e.g., `CBB_TRANSPORT`, `CBB_CACHE_ENABLED`)
- `.env` file auto-loaded on app start
- Pydantic settings with validation

---

## Collaboration Guidelines for Multi-Agent Systems

### For Claude (Code Generation & Review)
1. **Reference Structure**: When modifying services, check `resolver.py` for fallback patterns
2. **Async Pattern**: All new service methods must be async
3. **Error Handling**: Wrap with try/except and return CBBError
4. **Input Validation**: Use `_sanitize_text()`, `_validate_*()` helpers
5. **Testing**: Add tests to `tests/` folder; run `pytest` before commit
6. **Commit Style**: Small, focused commits; reference agents.md in PR if architectural

### For Gemini (AI Chat)
1. **Tool Schema**: Fetch definitions from `mcp_client.py`
2. **Context Passing**: Use `context` dict to reference game/team selections
3. **Error Recovery**: If tool fails, explain to user why and try alternate approach
4. **Response Format**: Use markdown tables for stats, clear lists for rankings
5. **Data Freshness**: Always fetch live data; don't rely on memory

### Shared Responsibilities
- **Codebase Health**: Check tests pass (`pytest`) before major changes
- **Production Stability**: Monitor concurrency limits, cache size, rate limits
- **Documentation**: Update agents.md if adding new services or data sources
- **Performance**: Profile slow queries; consider caching or fallback chains

---

## Testing

**51 unit tests** in `tests/`:
- `test_services/` — Service logic (games, teams, rankings, stats)
- `test_models/` — Pydantic model validation
- `test_sources/` — Source adapter mocking
- `test_utils/` — Cache, rate limiter, formatting

**Run tests**:
```bash
python -m pytest tests/ -x -q
```

**Coverage**: Sync layer (services, models), fallback chain, cache logic, rate limiting.
*Note*: Dash callbacks and Gemini agent tested via integration (chat_callbacks tests).

---

## Deployment

### Local Development
```bash
pip install -e ".[dev,dashboard]"
export GEMINI_API_KEY=...
python dashboard/app.py
# Dashboard: http://localhost:8050
# MCP Server: stdio (default, used by dashboard internally)
```

### Docker
```bash
docker build -t cbb-dashboard .
docker run -p 8000:8000 -p 8050:8050 \
  -e GEMINI_API_KEY=... \
  cbb-dashboard
```

### Cloud (Smithery)
```yaml
# smithery.yaml
server:
  module: cbb_mcp.server
  handler: mcp
  log_level: INFO
  transport: streamable-http
```

---

## Environment Variables Reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `CBB_TRANSPORT` | `stdio` | `stdio` or `streamable-http` |
| `CBB_HOST` | `127.0.0.1` | MCP server bind address |
| `CBB_PORT` | `8000` | MCP server port |
| `CBB_SERVER_API_KEY` | *(none)* | Bearer token for HTTP auth |
| `CBB_DASH_HOST` | `127.0.0.1` | Dashboard bind address |
| `CBB_DASH_PORT` | `8050` | Dashboard port |
| `CBB_CACHE_ENABLED` | `true` | Enable caching |
| `CBB_CACHE_DIR` | `.cache` | Disk cache directory |
| `CBB_LOG_LEVEL` | `INFO` | Logging level |
| `CBB_ESPN_RATE_LIMIT` | `10` | ESPN requests/sec |
| `CBB_NCAA_RATE_LIMIT` | `5` | NCAA requests/sec |
| `GEMINI_API_KEY` | *(required)* | Google Generai API key |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model to use |

---

## Quick Reference: Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `src/cbb_mcp/server.py` | Tool registration, auth, entry | ~450 |
| `src/cbb_mcp/services/resolver.py` | Source fallback logic | ~80 |
| `src/cbb_mcp/services/games.py` | Game service layer | ~200 |
| `src/cbb_mcp/services/teams.py` | Team service layer | ~150 |
| `src/cbb_mcp/utils/cache.py` | 2-layer cache implementation | ~150 |
| `src/cbb_mcp/sources/espn.py` | ESPN adapter | ~300 |
| `dashboard/app.py` | Dash app init + callbacks | ~150 |
| `dashboard/callbacks/chat_callbacks.py` | Chat UI logic | ~100 |
| `dashboard/ai/agent.py` | Gemini agentic loop | ~200 |
| `dashboard/scripts/train_predictor.py` | Model training pipeline | ~100 |

---

## Contact & Updates

**Repository**: https://github.com/rajachaiban/CBB_Predictive_Dashboard
**Issues**: For bugs or feature requests, open a GitHub issue
**Branch**: Current dev branch is `CBB_Dashboard` (main PR target is `main`)
