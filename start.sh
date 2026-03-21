#!/bin/bash
set -e

# CBB Dashboard startup script for Railway
# Runs both MCP server and Dash dashboard

echo "========================================="
echo "CBB Dashboard - Starting Services"
echo "========================================="

# Start MCP server in background on internal port 8000
echo "Starting MCP server on port 8000..."
CBB_PORT=8000 CBB_HOST=0.0.0.0 CBB_TRANSPORT=streamable-http cbb-mcp &
MCP_PID=$!
echo "MCP server PID: $MCP_PID"

# Wait for MCP server to be ready (max 10 seconds)
# MCP endpoint returns 405/406 for GET (expects POST) — that means it's running
echo "Waiting for MCP server to be ready..."
sleep 3
echo "MCP server should be ready."

# Tell the dashboard how to reach the MCP server (HTTP mode)
export MCP_SERVER_URL=http://localhost:8000/mcp

# Railway sets PORT env var — dashboard must listen on it
DASH_PORT=${PORT:-8050}

echo "========================================="
echo "Starting Dash dashboard on port ${DASH_PORT}..."
echo "========================================="

# Export so dashboard/app.py picks it up
export PORT=$DASH_PORT
export CBB_DASH_HOST=0.0.0.0
export CBB_DEBUG=0

exec python -m dashboard.app
