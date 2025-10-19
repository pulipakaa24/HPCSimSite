#!/bin/bash
# Startup script for Render.com deployment
# Starts both the enrichment service and AI intelligence layer

set -e  # Exit on error

echo "🚀 Starting HPC Simulation Services..."

# Trap to handle cleanup on exit
cleanup() {
    echo "🛑 Shutting down services..."
    kill $ENRICHMENT_PID $AI_PID 2>/dev/null || true
    exit
}
trap cleanup SIGINT SIGTERM

# Start enrichment service in background
echo "📊 Starting Enrichment Service on port 8000..."
python scripts/serve.py &
ENRICHMENT_PID=$!
echo "   ├─ PID: $ENRICHMENT_PID"

# Give enrichment service time to start
sleep 5

# Check if enrichment service is still running
if ! kill -0 $ENRICHMENT_PID 2>/dev/null; then
    echo "❌ Enrichment service failed to start"
    exit 1
fi
echo "   └─ ✅ Enrichment service started successfully"

# Start AI Intelligence Layer in background
echo "🤖 Starting AI Intelligence Layer on port 9000..."
python ai_intelligence_layer/main.py &
AI_PID=$!
echo "   ├─ PID: $AI_PID"

# Give AI layer time to start
sleep 3

# Check if AI layer is still running
if ! kill -0 $AI_PID 2>/dev/null; then
    echo "❌ AI Intelligence Layer failed to start"
    kill $ENRICHMENT_PID 2>/dev/null || true
    exit 1
fi
echo "   └─ ✅ AI Intelligence Layer started successfully"

echo ""
echo "✨ All services running!"
echo "   📊 Enrichment Service: http://0.0.0.0:8000"
echo "   🤖 AI Intelligence Layer: ws://0.0.0.0:9000/ws/pi"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for both processes (this keeps the script running)
wait $ENRICHMENT_PID $AI_PID
