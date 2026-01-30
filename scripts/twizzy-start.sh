#!/bin/bash
# Start TWIZZY Web Interface

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Starting TWIZZY..."

cd "$PROJECT_ROOT"

# Activate virtual environment if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Check if already running
if pgrep -f "uvicorn.*src.web.app" > /dev/null; then
    echo "TWIZZY is already running!"
    echo "Opening browser..."
    open http://127.0.0.1:7777
    exit 0
fi

# Start uvicorn with auto-reload in background
echo "Starting web server..."
nohup python -m uvicorn src.web.app:app \
    --host 127.0.0.1 \
    --port 7777 \
    --reload \
    --reload-dir src \
    > logs/twizzy.log 2>&1 &

# Wait for server to start
echo "Waiting for server..."
for i in {1..10}; do
    if curl -s http://127.0.0.1:7777 > /dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

# Open browser
echo "Opening browser..."
sleep 1
open http://127.0.0.1:7777

echo ""
echo "TWIZZY started!"
echo "   - Web server: http://127.0.0.1:7777"
echo "   - Auto-reload enabled (changes reload automatically)"
echo "   - Logs: $PROJECT_ROOT/logs/twizzy.log"
echo ""
echo "To stop: ./scripts/twizzy-kill.sh"
