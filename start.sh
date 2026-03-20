#!/bin/bash
set -e

# CBB Dashboard startup script for Railway
# Runs both MCP server and Dash dashboard

echo "========================================="
echo "CBB Dashboard - Starting Services"
echo "========================================="

# Start MCP server in background
echo "Starting MCP server on port ${CBB_PORT:-8000}..."
cbb-mcp &
MCP_PID=$!
echo "MCP server PID: $MCP_PID"

# Wait for MCP server to be ready (max 30 seconds)
echo "Waiting for MCP server to be ready..."
for i in {1..30}; do
    if python -c "import urllib.request; urllib.request.urlopen('http://localhost:${CBB_PORT:-8000}/mcp', timeout=2)" 2>/dev/null; then
        echo "✓ MCP server is ready!"
        break
    fi
    echo "  Waiting... ($i/30)"
    sleep 1
done

# Start Dash dashboard (foreground, so Docker can manage the process)
echo "========================================="
echo "Starting Dash dashboard on port ${CBB_DASH_PORT:-8050}..."
echo "========================================="
echo ""
echo "🎯 Dashboard will be available at:"
echo "   http://localhost:${CBB_DASH_PORT:-8050}"
echo ""

exec python -m dashboard.app
