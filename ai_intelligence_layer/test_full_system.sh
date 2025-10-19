#!/bin/bash
# Quick test script to verify both services are working

echo "🧪 Testing Full System Integration"
echo "==================================="
echo ""

# Check enrichment service
echo "1. Checking Enrichment Service (port 8000)..."
if curl -s http://localhost:8000/healthz > /dev/null 2>&1; then
    echo "   ✓ Enrichment service is running"
else
    echo "   ✗ Enrichment service not running!"
    echo "   Start it with: python3 scripts/serve.py"
    echo ""
    echo "   Or run from project root:"
    echo "   cd /Users/rishubmadhav/Documents/GitHub/HPCSimSite"
    echo "   python3 scripts/serve.py"
    exit 1
fi

# Check AI layer
echo "2. Checking AI Intelligence Layer (port 9000)..."
if curl -s http://localhost:9000/api/health > /dev/null 2>&1; then
    echo "   ✓ AI Intelligence Layer is running"
else
    echo "   ✗ AI Intelligence Layer not running!"
    echo "   Start it with: python main.py"
    echo ""
    echo "   Or run from ai_intelligence_layer:"
    echo "   cd ai_intelligence_layer"
    echo "   source myenv/bin/activate"
    echo "   python main.py"
    exit 1
fi

echo ""
echo "3. Pushing test telemetry via webhook..."
python3 test_webhook_push.py --loop 5 --delay 0.5

echo ""
echo "4. Generating strategies from buffered data..."
python3 test_buffer_usage.py

echo ""
echo "==================================="
echo "✅ Full integration test complete!"
echo ""
echo "View results:"
echo "  cat /tmp/brainstorm_strategies.json | python3 -m json.tool"
echo ""
echo "Check logs in the service terminals for detailed flow."
