#!/bin/bash

# mitmios Development Server

echo "mitmios - iOS Network Debugging Tool (dev mode)"
echo ""

# Project directories
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MITMPROXY_DIR="$PROJECT_DIR/mitmproxy"

# Cleanup on exit
cleanup() {
    echo ""
    echo "Stopping servers..."
    pkill -f "npm start" 2>/dev/null
    pkill -f "mitmweb" 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# 1. Frontend dev server (Vite)
echo "Starting Vite frontend dev server..."
cd "$MITMPROXY_DIR/web"
npm start > /tmp/mitmios-vite.log 2>&1 &
VITE_PID=$!

sleep 3
echo "Vite dev server: http://localhost:5173"

# 2. mitmweb backend
echo "Starting mitmweb backend..."
cd "$MITMPROXY_DIR"
uv run mitmweb --web-host 127.0.0.1 --web-port 8081 > /tmp/mitmios-backend.log 2>&1 &
MITMWEB_PID=$!

sleep 3

# Extract auth token
TOKEN=$(grep -o 'token=[a-f0-9]*' /tmp/mitmios-backend.log | head -1 | cut -d= -f2)

echo "mitmweb backend: http://127.0.0.1:8081"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  mitmios Web UI: http://127.0.0.1:8081/?token=$TOKEN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Auto-open browser
open "http://127.0.0.1:8081/?token=$TOKEN"

# Monitor logs
echo "Monitoring logs..."
tail -f /tmp/mitmios-backend.log /tmp/mitmios-vite.log
