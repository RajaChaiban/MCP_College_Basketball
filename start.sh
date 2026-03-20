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

# Wait for MCP server to be ready (max 30 seconds)
echo "Waiting for MCP server to be ready..."
for i in {1..30}; do
    if python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/mcp', timeout=2)" 2>/dev/null; then
        echo "MCP server is ready!"
        break
    fi
    echo "  Waiting... ($i/30)"
    sleep 1
done

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
