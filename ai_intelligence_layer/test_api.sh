#!/bin/bash

# Test script for AI Intelligence Layer (no jq required)

BASE_URL="http://localhost:9000"

echo "=== AI Intelligence Layer Test Script ==="
echo ""

# Test 1: Health check
echo "1. Testing health endpoint..."
curl -s "$BASE_URL/api/health" | python3 -m json.tool
echo ""
echo ""

# Test 2: Brainstorm strategies
echo "2. Testing brainstorm endpoint..."
echo "   (This may take 15-30 seconds...)"

# Create a temporary Python script to build the request
python3 << 'PYEOF' > /tmp/test_request.json
import json

# Load sample data
with open('sample_data/sample_enriched_telemetry.json') as f:
    telemetry = json.load(f)

with open('sample_data/sample_race_context.json') as f:
    context = json.load(f)

# Build request
request = {
    "enriched_telemetry": telemetry,
    "race_context": context
}

# Write to file
print(json.dumps(request, indent=2))
PYEOF

# Make the brainstorm request
curl -s -X POST "$BASE_URL/api/strategy/brainstorm" \
  -H "Content-Type: application/json" \
  -d @/tmp/test_request.json > /tmp/brainstorm_result.json

# Parse and display results
python3 << 'PYEOF'
import json

try:
    with open('/tmp/brainstorm_result.json') as f:
        data = json.load(f)
    
    if 'strategies' in data:
        strategies = data['strategies']
        print(f"✓ Generated {len(strategies)} strategies")
        print("\nSample strategies:")
        for s in strategies[:3]:
            print(f"  {s['strategy_id']}. {s['strategy_name']}")
            print(f"     Stops: {s['stop_count']}, Risk: {s['risk_level']}")
    else:
        print("✗ Error in brainstorm response:")
        print(json.dumps(data, indent=2))
except Exception as e:
    print(f"✗ Failed to parse brainstorm result: {e}")
PYEOF

echo ""
echo ""

# Test 3: Analyze strategies
echo "3. Testing analyze endpoint..."
echo "   (This may take 20-40 seconds...)"

# Build analyze request
python3 << 'PYEOF' > /tmp/analyze_request.json
import json

# Load brainstorm result
try:
    with open('/tmp/brainstorm_result.json') as f:
        brainstorm = json.load(f)
    
    if 'strategies' not in brainstorm:
        print("Error: No strategies found in brainstorm result")
        exit(1)
    
    # Load sample data
    with open('sample_data/sample_enriched_telemetry.json') as f:
        telemetry = json.load(f)
    
    with open('sample_data/sample_race_context.json') as f:
        context = json.load(f)
    
    # Build analyze request
    request = {
        "enriched_telemetry": telemetry,
        "race_context": context,
        "strategies": brainstorm['strategies']
    }
    
    print(json.dumps(request, indent=2))
except Exception as e:
    print(f"Error building analyze request: {e}")
    exit(1)
PYEOF

# Make the analyze request
curl -s -X POST "$BASE_URL/api/strategy/analyze" \
  -H "Content-Type: application/json" \
  -d @/tmp/analyze_request.json > /tmp/analyze_result.json

# Parse and display results
python3 << 'PYEOF'
import json

try:
    with open('/tmp/analyze_result.json') as f:
        data = json.load(f)
    
    if 'top_strategies' in data:
        print("✓ Analysis complete!")
        print("\nTop 3 strategies:")
        for s in data['top_strategies']:
            print(f"\n{s['rank']}. {s['strategy_name']} ({s['classification']})")
            print(f"   Predicted: P{s['predicted_outcome']['finish_position_most_likely']}")
            print(f"   P3 or better: {s['predicted_outcome']['p1_probability'] + s['predicted_outcome']['p2_probability'] + s['predicted_outcome']['p3_probability']}%")
            print(f"   Risk: {s['risk_assessment']['risk_level']}")
        
        # Show recommended strategy details
        rec = data['top_strategies'][0]
        print("\n" + "="*60)
        print("RECOMMENDED STRATEGY DETAILS:")
        print("="*60)
        print(f"\nEngineer Brief: {rec['engineer_brief']['summary']}")
        print(f"\nDriver Radio: \"{rec['driver_audio_script']}\"")
        print(f"\nECU Commands:")
        print(f"  Fuel: {rec['ecu_commands']['fuel_mode']}")
        print(f"  ERS: {rec['ecu_commands']['ers_strategy']}")
        print(f"  Engine: {rec['ecu_commands']['engine_mode']}")
        
        print("\n" + "="*60)
    else:
        print("✗ Error in analyze response:")
        print(json.dumps(data, indent=2))
except Exception as e:
    print(f"✗ Failed to parse analyze result: {e}")
PYEOF

echo ""
echo "=== Test Complete ==="
echo "Full results saved to:"
echo "  - /tmp/brainstorm_result.json"
echo "  - /tmp/analyze_result.json"
