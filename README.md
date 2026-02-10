# cbb-mcp

**NCAA Men's D1 College Basketball MCP Server**

An [MCP](https://modelcontextprotocol.io) server that gives Claude (and any MCP client) real-time access to college basketball data — live scores, rankings, team stats, box scores, play-by-play, and more.

100% free. No API keys required.

---

## Features

- **16 tools** covering scores, teams, rankings, stats, and tournament data
- **4 data sources** (ESPN, NCAA, sportsdataverse, cbbpy) with automatic fallback
- **Fuzzy team matching** — say "duke", "Blue Devils", or "DUKE" and it just works
- **Two-layer caching** (memory + disk) with smart TTLs
- **Rate limiting** per source to stay within free tier limits
- **Dual transport** — stdio for Claude Desktop/Code, Streamable HTTP for remote hosting
- **Security hardened** — input validation, timing-safe auth, response size limits, secret masking

## Quick Start

### Install

```bash
pip install cbb-mcp
```

### Connect to Claude Desktop

Add to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "college-basketball": {
      "command": "cbb-mcp"
    }
  }
}
```

### Connect to Claude Code

```bash
claude mcp add college-basketball cbb-mcp
```

Then ask Claude things like:
- "What are today's college basketball scores?"
- "Compare Duke and North Carolina"
- "Who leads the nation in scoring?"
- "Show me the AP Top 25"
- "Get the box score for game 401720001"

## Tools

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

Plus **1 resource** (`cbb://conferences`) and **2 prompts** (`game_preview_prompt`, `season_recap_prompt`).

## Data Sources

All sources are free and require no API keys:

| Source | What it provides |
|--------|-----------------|
| ESPN Hidden API | Live scores, teams, rankings, standings, schedules, box scores |
| NCAA API | Scores, rankings, game details |
| sportsdataverse | Historical play-by-play, team/player box scores |
| cbbpy | Box scores, play-by-play, schedules |

The server tries ESPN first (most comprehensive), then falls back through other sources automatically if a request fails.

## Remote Hosting (HTTP)

Run as an HTTP server for remote clients:

```bash
# Start HTTP server
CBB_TRANSPORT=streamable-http cbb-mcp

# With API key auth
CBB_TRANSPORT=streamable-http CBB_SERVER_API_KEY=your-secret cbb-mcp
```

### Docker

```bash
docker build -t cbb-mcp .
docker run -p 8000:8000 cbb-mcp

# Or with docker-compose
docker compose up
```

Connect remote MCP clients to `http://your-host:8000/mcp`.

## Configuration

All config via environment variables (or `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `CBB_TRANSPORT` | `stdio` | `stdio` or `streamable-http` |
| `CBB_HOST` | `127.0.0.1` | HTTP server bind address |
| `CBB_PORT` | `8000` | HTTP server port |
| `CBB_SERVER_API_KEY` | *(empty)* | Bearer token for HTTP auth |
| `CBB_CACHE_ENABLED` | `true` | Enable/disable caching |
| `CBB_CACHE_DIR` | `.cache` | Disk cache directory |
| `CBB_LOG_LEVEL` | `INFO` | Logging level |
| `CBB_ESPN_RATE_LIMIT` | `10` | ESPN requests/sec |
| `CBB_NCAA_RATE_LIMIT` | `5` | NCAA requests/sec |

## Security

- All inputs validated and length-limited
- Game IDs validated against alphanumeric pattern
- Dates parsed strictly (rejects malformed input)
- Season years bounded to 2000-2100
- HTTP auth uses timing-safe comparison (`hmac.compare_digest`)
- API keys/secrets never logged or returned in responses (`repr=False`)
- Source resolver uses method whitelist (no arbitrary method invocation)
- HTTP responses capped at 5 MB
- Non-root Docker user with read-only filesystem
- Warns when API key auth is used on non-localhost without TLS

## Development

```bash
git clone https://github.com/rajachatrathi/cbb-mcp.git
cd cbb-mcp
pip install -e ".[dev]"
pytest
```

## License

MIT
