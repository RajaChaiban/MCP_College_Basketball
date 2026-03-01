# ML Sports Predictor Server Migration Guide

## Overview

The **ML Sports Predictor** is a new, standalone MCP server that has been separated from the CBB Dashboard. This enables:

1. **Scalability** — Run the ML server independently, even on GPU-equipped machines
2. **Multi-Sport Support** — CBB (full), Soccer/NFL/MLB/Tennis (ready for models)
3. **Separation of Concerns** — ML inference decoupled from data fetching
4. **Reusability** — Can be deployed to other applications beyond the dashboard

## Architecture Change

### Before (Single Process)
```
Dashboard
├── CBB MCP Client (tools)
└── Predictor Client (in-process)
    └── Models (cbb_predictor_bundle.joblib)
```

### After (Multi-Process)
```
Dashboard
├── CBB MCP Client ──┬──> CBB MCP Server (data tools: scores, teams, rankings, etc.)
└── ML MCP Client ──┬──> ML MCP Server (prediction tools: get_win_probability, etc.)
                     └──> Models (sport-specific bundles)
```

## What Changed

### New Files Created

**ML Sports Predictor Package (`src/ml_sports_predictor/`)**
- `__init__.py` — Package exports
- `config.py` — Pydantic-based configuration + YAML loading
- `sports_config.yaml` — Sport configurations (5 sports: CBB, Soccer, NFL, MLB, Tennis)
- `predictor.py` — MultiSportPredictor wrapper class
- `server.py` — FastMCP server with 3 tools (get_win_probability, explain_win_probability, get_probability_history)
- `formatting.py` — Output formatting utilities
- `errors.py` — ML-specific exception hierarchy

**Dashboard Integration (`dashboard/ai/`)**
- `ml_mcp_client.py` — Async client for ML MCP server communication

**Tests (`tests/ml_sports_predictor/`)**
- `test_config.py` — Configuration + YAML loading
- `test_predictor.py` — MultiSportPredictor class
- `test_server.py` — Server tools + validation
- `test_formatting.py` — Output formatting
- `test_integration.py` — Multi-server integration

### Modified Files

**`dashboard/ai/tools.py`**
- Updated `dispatch_tool()` to route predictor tools to ML MCP server (instead of in-process client)
- Changed import from `predictor_client` to `ml_mcp_client`

**`pyproject.toml`**
- Added `ml-sports-predictor` entry point
- Added dependencies: `pyyaml`, `joblib`, `scikit-learn`, `xgboost`
- Added `src/ml_sports_predictor` to wheel packages

### Deprecated Files

**`dashboard/ai/predictor_client.py`** — DEPRECATED
- **Still works** but no longer used by dashboard
- Can be removed in next major version
- Old in-process predictor client code

**`src/cbb_mcp/predictor_server.py`** — DEPRECATED
- **Still works** but redundant with new ML server
- Can be removed in next major version
- Old predictor integration in CBB server

## Migration Steps

### For Users (Dashboard Operators)

#### 1. Install Dependencies
```bash
pip install -e ".[dev,dashboard]"
```

#### 2. Run Both Servers

**Terminal 1 — CBB Data Server:**
```bash
export CBB_LOG_LEVEL=INFO
python -m cbb_mcp.server
# or: cbb-mcp
```

**Terminal 2 — ML Predictor Server:**
```bash
export ML_SPORTS_LOG_LEVEL=INFO
python -m ml_sports_predictor.server
# or: ml-sports-predictor
```

**Terminal 3 — Dashboard:**
```bash
export GEMINI_API_KEY=your-key
python dashboard/app.py
# Opens: http://localhost:8050
```

#### 3. Verify Both Servers Are Running

- CBB Server should log: `server_starting transport=stdio` (to stderr)
- ML Server should log: `server_starting transport=stdio` (to stderr)
- Dashboard should start without errors

### For Developers

#### Unit Tests

All ML server tests pass:
```bash
pytest tests/ml_sports_predictor/ -v
```

All CBB server tests still pass:
```bash
pytest tests/test_services/ -v
```

#### Adding a New Sport

1. Add sport config to `src/ml_sports_predictor/sports_config.yaml`
2. Train model: `python dashboard/scripts/train_predictor.py --sport soccer --input data.csv`
3. Save bundle: `models/soccer_predictor_bundle.joblib`
4. Restart ML server (auto-loads all models)
5. Dashboard Gemini tools automatically support new sport

#### Environment Variables

**ML Server (`ML_SPORTS_*` prefix)**
| Variable | Default | Notes |
|----------|---------|-------|
| `ML_SPORTS_TRANSPORT` | `stdio` | `stdio` or `streamable-http` |
| `ML_SPORTS_HOST` | `127.0.0.1` | For HTTP mode |
| `ML_SPORTS_PORT` | `8001` | For HTTP mode |
| `ML_SPORTS_LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR |
| `ML_SPORTS_CACHE_ENABLED` | `true` | Enable prediction caching |
| `ML_SPORTS_SPORTS_REGISTRY_PATH` | `src/ml_sports_predictor/sports_config.yaml` | Config file path |

**CBB Server (`CBB_*` prefix)**
- Unchanged from before

## Backwards Compatibility

✅ **No Breaking Changes for Dashboard Users**

- Predictor tools (`get_win_probability`, etc.) maintain same interface
- Tool parameters, return format identical
- Gemini agent code unchanged
- Just "internal plumbing" upgrade

❌ **In-Process Predictor Deprecated**

If you were importing `from dashboard.ai.predictor import get_win_probability`:
```python
# OLD (deprecated):
from dashboard.ai.predictor import get_win_probability
prob = get_win_probability(game_obj)

# NEW (not typically needed, use dispatch_tool instead):
from dashboard.ai.ml_mcp_client import get_ml_client
client = get_ml_client()
prob_text = await client.call_tool("get_win_probability", {"sport_id": "cbb", "game_id": "401827712"})
```

## Docker Deployment

### Single Container (Both Servers)

**Dockerfile** (multi-stage example)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e ".[dev,dashboard]"

# Entrypoint runs both servers in background, dashboard in foreground
CMD ["bash", "-c", "python -m ml_sports_predictor.server > /tmp/ml.log 2>&1 & python -m cbb_mcp.server > /tmp/cbb.log 2>&1 & python dashboard/app.py"]
```

### Docker Compose (Recommended)

```yaml
version: '3'

services:
  cbb-data-server:
    build: .
    command: python -m cbb_mcp.server
    environment:
      CBB_LOG_LEVEL: INFO
    ports:
      - "8000:8000"  # If HTTP mode
    volumes:
      - ./.cache:/app/.cache

  ml-predictor-server:
    build: .
    command: python -m ml_sports_predictor.server
    environment:
      ML_SPORTS_LOG_LEVEL: INFO
    ports:
      - "8001:8001"  # If HTTP mode
    volumes:
      - ./.cache_ml:/app/.cache_ml
      - ./cbb_predictor_bundle.joblib:/app/cbb_predictor_bundle.joblib

  dashboard:
    build: .
    command: python dashboard/app.py
    ports:
      - "8050:8050"
    environment:
      GEMINI_API_KEY: ${GEMINI_API_KEY}
      CBB_LOG_LEVEL: INFO
      ML_SPORTS_LOG_LEVEL: INFO
    depends_on:
      - cbb-data-server
      - ml-predictor-server
    volumes:
      - ./.cache:/app/.cache
      - ./.cache_ml:/app/.cache_ml
```

Run:
```bash
docker-compose up
```

## Cloud Deployment (Smithery, etc.)

### Configuration for HTTP Transport

Set environment variables:
```
ML_SPORTS_TRANSPORT=streamable-http
ML_SPORTS_PORT=8001
CBB_TRANSPORT=streamable-http
CBB_PORT=8000
```

The dashboard will communicate with both servers via HTTP instead of stdio.

## Troubleshooting

### "ML MCP server connection failed"
- Verify ML server is running: `python -m ml_sports_predictor.server`
- Check stderr output for startup errors
- Verify `sports_config.yaml` is in the correct path

### "Model not found for cbb"
- Verify `cbb_predictor_bundle.joblib` exists in working directory
- Check ML server logs for model loading status
- If model not found, predictions will be unavailable but no crash

### "Tool error: Unknown sport"
- Valid sports: `cbb`, `soccer`, `nfl`, `mlb`, `tennis`
- Verify sport ID spelling (case-insensitive)
- For new sports: add config to YAML + train model

### Both Servers Running But Dashboard Fails
- Verify dashboard can import `ml_mcp_client`: `python -c "from dashboard.ai.ml_mcp_client import get_ml_client"`
- Check `GEMINI_API_KEY` is set
- Verify no port conflicts (CBB: 8000, ML: 8001)

## Performance Notes

### Latency

- **Pre-server startup:** ~500ms (model loading)
- **Per-prediction call:** ~10-50ms (LR + XGB ensemble)
- **Network overhead:** +10-20ms per server (stdio)

### Memory

- **ML Server baseline:** ~150MB (Python + MCP)
- **Model loading:** +200-400MB (depending on models loaded)
- **Total per server:** ~400-600MB expected

### Scaling

To run multiple ML servers (e.g., one per sport):
1. Deploy each as separate container
2. Update dashboard config to route by sport
3. Example: `ML_SPORTS_PREDICTOR_SOCCER_URL=http://soccer-ml:8001`

## Next Steps

### For Developers
1. Run tests: `pytest tests/ml_sports_predictor/ -v`
2. Add new sports to `sports_config.yaml`
3. Train sport-specific models
4. Deploy with docker-compose

### For Users
1. Update to latest version
2. Run both servers (CBB + ML)
3. Use dashboard normally—no UI changes

### For Researchers
1. Inspect `src/ml_sports_predictor/sports_config.yaml` for sport configs
2. Review `tests/ml_sports_predictor/test_predictor.py` for feature normalization
3. Check `dashboard/scripts/train_predictor.py` for training pipeline

## References

- **Architecture Details:** See `agents.md` for comprehensive codebase reference
- **Configuration:** `src/ml_sports_predictor/config.py`
- **Formatting:** `src/ml_sports_predictor/formatting.py`
- **Tests:** `tests/ml_sports_predictor/`
- **Sport Configurations:** `src/ml_sports_predictor/sports_config.yaml`

---

**Migration Date:** 2026-02-28
**Status:** ✅ Complete, All Tests Passing
