# Testing the AI Intelligence Layer

## Quick Test Options

### Option 1: Python Script (RECOMMENDED - No dependencies)
```bash
python3 test_api.py
```

**Advantages:**
- ✅ No external tools required
- ✅ Clear, formatted output
- ✅ Built-in error handling
- ✅ Works on all systems

### Option 2: Shell Script
```bash
./test_api.sh
```

**Note:** Uses pure Python for JSON processing (no `jq` required)

### Option 3: Manual Testing

#### Health Check
```bash
curl http://localhost:9000/api/health | python3 -m json.tool
```

#### Brainstorm Test
```bash
python3 << 'EOF'
import json
import urllib.request

# Load data
with open('sample_data/sample_enriched_telemetry.json') as f:
    telemetry = json.load(f)
with open('sample_data/sample_race_context.json') as f:
    context = json.load(f)

# Make request
data = json.dumps({
    "enriched_telemetry": telemetry,
    "race_context": context
}).encode('utf-8')

req = urllib.request.Request(
    'http://localhost:9000/api/strategy/brainstorm',
    data=data,
    headers={'Content-Type': 'application/json'}
)

with urllib.request.urlopen(req, timeout=120) as response:
    result = json.loads(response.read())
    print(f"Generated {len(result['strategies'])} strategies")
    for s in result['strategies'][:3]:
        print(f"{s['strategy_id']}. {s['strategy_name']} - {s['risk_level']} risk")
EOF
```

## Expected Output

### Successful Test Run

```
======================================================================
AI Intelligence Layer - Test Suite
======================================================================
1. Testing health endpoint...
   ✓ Status: healthy
   ✓ Service: AI Intelligence Layer
   ✓ Demo mode: False

2. Testing brainstorm endpoint...
   (This may take 15-30 seconds...)
   ✓ Generated 20 strategies in 18.3s

   Sample strategies:
     1. Conservative 1-Stop
        Stops: 1, Risk: low
     2. Standard Medium-Hard
        Stops: 1, Risk: medium
     3. Aggressive Undercut
        Stops: 2, Risk: high

3. Testing analyze endpoint...
   (This may take 20-40 seconds...)
   ✓ Analysis complete in 24.7s

   Top 3 strategies:

     1. Aggressive Undercut (RECOMMENDED)
        Predicted: P3
        P3 or better: 75%
        Risk: medium

     2. Standard Two-Stop (ALTERNATIVE)
        Predicted: P4
        P3 or better: 63%
        Risk: medium

     3. Conservative 1-Stop (CONSERVATIVE)
        Predicted: P5
        P3 or better: 37%
        Risk: low

======================================================================
RECOMMENDED STRATEGY DETAILS:
======================================================================

Engineer Brief:
  Undercut Leclerc on lap 32. 75% chance of P3 or better.

Driver Radio:
  "Box this lap. Soft tires going on. Push mode for next 8 laps."

ECU Commands:
  Fuel: RICH
  ERS: AGGRESSIVE_DEPLOY
  Engine: PUSH

======================================================================

======================================================================
✓ ALL TESTS PASSED!
======================================================================

Results saved to:
  - /tmp/brainstorm_result.json
  - /tmp/analyze_result.json
```

## Troubleshooting

### "Connection refused"
```bash
# Service not running. Start it:
python main.py
```

### "Timeout" errors
```bash
# Check .env settings:
cat .env | grep TIMEOUT

# Should see:
# BRAINSTORM_TIMEOUT=90
# ANALYZE_TIMEOUT=120

# Also check Fast Mode is enabled:
cat .env | grep FAST_MODE
# Should see: FAST_MODE=true
```

### "422 Unprocessable Content"
This usually means invalid JSON in the request. The new test scripts handle this automatically.

### Test takes too long
```bash
# Enable fast mode in .env:
FAST_MODE=true

# Restart service:
# Press Ctrl+C in the terminal running python main.py
# Then: python main.py
```

## Performance Benchmarks

With `FAST_MODE=true` and `gemini-2.5-flash`:

| Test | Expected Time | Status |
|------|--------------|--------|
| Health | <1s | ✅ |
| Brainstorm | 15-30s | ✅ |
| Analyze | 20-40s | ✅ |
| **Total** | **40-70s** | ✅ |

## Component Tests

To test just the data models and validators (no API calls):

```bash
python test_components.py
```

This runs instantly and doesn't require the Gemini API.

## Files Created During Tests

- `/tmp/test_request.json` - Brainstorm request payload
- `/tmp/brainstorm_result.json` - 20 generated strategies
- `/tmp/analyze_request.json` - Analyze request payload  
- `/tmp/analyze_result.json` - Top 3 analyzed strategies

You can inspect these files to see the full API responses.

## Integration with Enrichment Service

If the enrichment service is running on `localhost:8000`, the AI layer will automatically fetch telemetry data when not provided in the request:

```bash
# Test without providing telemetry (will fetch from enrichment service)
curl -X POST http://localhost:9000/api/strategy/brainstorm \
  -H "Content-Type: application/json" \
  -d '{
    "race_context": {
      "race_info": {"track_name": "Monaco", "current_lap": 27, "total_laps": 58},
      "driver_state": {"driver_name": "Hamilton", "current_position": 4}
    }
  }'
```

---

**Ready to test!** 🚀

Just run: `python3 test_api.py`
