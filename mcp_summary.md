# MCP Architecture Summary: College Basketball Analytics

This document provides a detailed breakdown of the Model Context Protocol (MCP) integration within the `MCP_College_Basketball` project. The system uses a hybrid approach, combining a standalone MCP server for data retrieval with an in-process "Predictor Client" for ML-driven analytics.

---

## 1. The `College Basketball` Server (Physical MCP)

The core data engine is a standalone Python process built using the **FastMCP** framework. It acts as the "Source of Truth" for all NCAA Men's Division I data.

### Architecture
- **Transport**: `stdio` (Standard Input/Output).
- **Process**: Spawned as a subprocess by the Dashboard (`dashboard/ai/mcp_client.py`).
- **Data Sources**: Aggregates data from ESPN, NCAA, and SportsDataVerse.
- **Concurrency**: Implements a global semaphore (max 50 concurrent calls) to prevent resource exhaustion during heavy agentic loops.

### Capabilities & Tools
This server provides "Ground Truth" tools that allow an AI agent to see the current state of the college basketball world.

| Tool | Purpose | Example Input |
| :--- | :--- | :--- |
| `get_live_scores` | Fetches real-time scores for a date. | `{"date": "2026-02-28", "top25_only": true}` |
| `get_team` | Fuzzy-searches for a team and returns its "Identity" (Record, Venue, Rank). | `{"team_name": "Duke"}` |
| `get_box_score` | Detailed per-player statistics for a specific game. | `{"game_id": "401575451"}` |
| `compare_teams` | Side-by-side statistical analysis of two teams. | `{"team1": "Kansas", "team2": "Houston"}` |

### Example Interaction
**Agent Query:** "How did the Big Ten teams do today?"
1. Agent calls `get_live_scores(conference="Big Ten")`.
2. Server returns a formatted markdown table of scores, TV networks, and game statuses.

---

## 2. The Predictor "Client" (In-Process Adapter)

Unlike the main server, the Predictor Client is an **In-Process Adapter**. It mimics the MCP interface (`call_tool` pattern) but executes code directly within the dashboard's Python environment to minimize latency and simplify ML model management.

### Architecture
- **Model Type**: Calibrated Ensemble (Logistic Regression + XGBoost).
- **Execution**: Local execution within `dashboard/ai/predictor.py`.
- **Integration**: Accessed via `dashboard/ai/predictor_client.py`.

### Capabilities & Tools
The Predictor focuses on "Analytical Inference"—taking the raw data from the main server and turning it into a forecast.

| Tool | Purpose | Output Style |
| :--- | :--- | :--- |
| `get_win_probability` | Calculates a 0.0-1.0 probability for a game. | "Predicted Winner: Houston (72.4%)" |
| `explain_win_probability` | Generates a narrative analyst report explaining the "Why". | 200-300 word breakdown of Ranking vs. Momentum. |
| `get_probability_history` | Returns the trend of the model's confidence over time. | Time-series table of win % shifts. |

### Example Interaction
**Agent Query:** "Why is UNC favored over NC State?"
1. Agent calls `get_win_probability(game_id="...")` to get the raw numbers.
2. Agent calls `explain_win_probability(game_id="...")`.
3. The Predictor analyzes the *Strength Differential* (60% weight on AP Rank, 40% on Win Rate) and *Home Court Advantage* to generate a narrative report.

---

## 3. The Orchestration Layer (Gemini AI Agent)

The **Gemini Agent** (`dashboard/ai/agent.py`) acts as the conductor for these two components. It is instructed via a system prompt to never answer from memory and always use these tools in sequence.

### The "Analyst" Workflow:
1. **Identify**: User asks about a matchup.
2. **Retrieve**: Agent calls `search_teams` and `get_live_scores` from the **College Basketball Server**.
3. **Predict**: Agent passes the `game_id` to the **Predictor Client**'s `get_win_probability`.
4. **Synthesize**: Agent combines the raw stats (Ground Truth) with the ML forecast (Inference) to provide a complete answer.

---

## 4. Why This Hybrid Approach?

| Feature | Physical Server (stdio) | In-Process Client |
| :--- | :--- | :--- |
| **Separation of Concerns** | Excellent. Data logic is isolated. | Tight. ML models stay with the UI. |
| **Performance** | Subprocess overhead. | Zero-latency function calls. |
| **Reusability** | Can be used by Claude Desktop/other MCP clients. | Specific to the Dashboard AI agent. |
| **Maintenance** | Easy to update data sources without touching the UI. | Easier to debug ML weights and features. |
