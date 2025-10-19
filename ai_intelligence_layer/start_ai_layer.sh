#!/bin/bash
# Start AI Intelligence Layer
# Usage: ./start_ai_layer.sh

cd "$(dirname "$0")"

echo "Starting AI Intelligence Layer on port 9000..."
echo "Logs will be written to /tmp/ai_layer.log"
echo ""

# Kill any existing process on port 9000
PID=$(lsof -ti:9000)
if [ ! -z "$PID" ]; then
    echo "Killing existing process on port 9000 (PID: $PID)"
    kill -9 $PID 2>/dev/null
    sleep 1
fi

# Start the AI layer
python3 main.py > /tmp/ai_layer.log 2>&1 &
AI_PID=$!

echo "AI Layer started with PID: $AI_PID"
echo ""

# Wait for startup
echo "Waiting for server to start..."
sleep 3

# Check if it's running
if lsof -Pi :9000 -sTCP:LISTEN -t >/dev/null ; then
    echo "✓ AI Intelligence Layer is running on port 9000"
    echo ""
    echo "Health check:"
    curl -s http://localhost:9000/api/health | python3 -m json.tool 2>/dev/null || echo "  (waiting for full startup...)"
    echo ""
    echo "WebSocket endpoint: ws://localhost:9000/ws/pi"
    echo ""
    echo "To stop: kill $AI_PID"
    echo "To view logs: tail -f /tmp/ai_layer.log"
else
    echo "✗ Failed to start AI Intelligence Layer"
    echo "Check logs: tail /tmp/ai_layer.log"
    exit 1
fi
