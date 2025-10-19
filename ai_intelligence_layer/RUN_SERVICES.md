# 🚀 Quick Start: Full System Test

## Overview

Test the complete webhook integration flow:
1. **Enrichment Service** (port 8000) - Receives telemetry, enriches it, POSTs to AI layer
2. **AI Intelligence Layer** (port 9000) - Receives enriched data, generates 3 strategies

## Step-by-Step Testing

### 1. Start the Enrichment Service (Port 8000)

From the **project root** (`HPCSimSite/`):

```bash
# Option A: Using the serve script
python3 scripts/serve.py
```

**Or from any directory:**

```bash
cd /Users/rishubmadhav/Documents/GitHub/HPCSimSite
python3 -m uvicorn hpcsim.api:app --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

**Verify it's running:**
```bash
curl http://localhost:8000/healthz
# Should return: {"status":"ok","stored":0}
```

### 2. Configure Webhook Callback

The enrichment service needs to know where to send enriched data.

**Option A: Set environment variable (before starting)**
```bash
export NEXT_STAGE_CALLBACK_URL=http://localhost:9000/api/ingest/enriched
python3 scripts/serve.py
```

**Option B: For testing, manually POST enriched data**

You can skip the callback and use `test_webhook_push.py` to simulate it (already working!).

### 3. Start the AI Intelligence Layer (Port 9000)

In a **new terminal**, from `ai_intelligence_layer/`:

```bash
cd /Users/rishubmadhav/Documents/GitHub/HPCSimSite/ai_intelligence_layer
source myenv/bin/activate  # Activate virtual environment
python main.py
```

You should see:
```
INFO - Starting AI Intelligence Layer on port 9000
INFO - Strategy count: 3
INFO - All services initialized successfully
INFO:     Uvicorn running on http://0.0.0.0:9000
```

**Verify it's running:**
```bash
curl http://localhost:9000/api/health
```

### 4. Test the Webhook Flow

**Method 1: Simulate enrichment service (fastest)**

```bash
cd ai_intelligence_layer
python3 test_webhook_push.py --loop 5
```

Output:
```
✓ Posted lap 27 - Buffer size: 1 records
✓ Posted lap 28 - Buffer size: 2 records
...
Posted 5/5 records successfully
```

**Method 2: POST to enrichment service (full integration)**

POST raw telemetry to enrichment service, it will enrich and forward:

```bash
curl -X POST http://localhost:8000/ingest/telemetry \
  -H "Content-Type: application/json" \
  -d '{
    "lap": 27,
    "speed": 310,
    "tire_temp": 95,
    "fuel_level": 45
  }'
```

*Note: This requires NEXT_STAGE_CALLBACK_URL to be set*

### 5. Generate Strategies

```bash
cd ai_intelligence_layer
python3 test_buffer_usage.py
```

Output:
```
Testing FAST brainstorm with buffered telemetry...
(Configured for 3 strategies - fast and diverse!)

✓ Brainstorm succeeded!
  Generated 3 strategies
  Saved to: /tmp/brainstorm_strategies.json

  Strategies:
    1. Conservative Stay Out (1-stop, low risk)
       Tires: medium → hard
       Pits at: laps [35]
       Extend current stint then hard tires to end

    2. Standard Undercut (1-stop, medium risk)
       Tires: medium → hard
       Pits at: laps [32]
       Pit before tire cliff for track position

    3. Aggressive Two-Stop (2-stop, high risk)
       Tires: medium → soft → hard
       Pits at: laps [30, 45]
       Early pit for fresh rubber and pace advantage

✓ SUCCESS: AI layer is using webhook buffer!
  Full JSON saved to /tmp/brainstorm_strategies.json
```

### 6. View the Results

```bash
cat /tmp/brainstorm_strategies.json | python3 -m json.tool
```

Or just:
```bash
cat /tmp/brainstorm_strategies.json
```

## Terminal Setup

Here's the recommended terminal layout:

```
┌─────────────────────────┬─────────────────────────┐
│ Terminal 1              │ Terminal 2              │
│ Enrichment Service      │ AI Intelligence Layer   │
│ (Port 8000)             │ (Port 9000)             │
│                         │                         │
│ $ cd HPCSimSite         │ $ cd ai_intelligence... │
│ $ python3 scripts/      │ $ source myenv/bin/...  │
│   serve.py              │ $ python main.py        │
│                         │                         │
│ Running...              │ Running...              │
└─────────────────────────┴─────────────────────────┘
┌───────────────────────────────────────────────────┐
│ Terminal 3 - Testing                              │
│                                                   │
│ $ cd ai_intelligence_layer                        │
│ $ python3 test_webhook_push.py --loop 5           │
│ $ python3 test_buffer_usage.py                    │
└───────────────────────────────────────────────────┘
```

## Current Configuration

### Enrichment Service (Port 8000)
- **Endpoints:**
  - `POST /ingest/telemetry` - Receive raw telemetry
  - `POST /enriched` - Manually post enriched data
  - `GET /enriched?limit=N` - Retrieve recent enriched records
  - `GET /healthz` - Health check

### AI Intelligence Layer (Port 9000)
- **Endpoints:**
  - `GET /api/health` - Health check
  - `POST /api/ingest/enriched` - Webhook receiver (enrichment service POSTs here)
  - `POST /api/strategy/brainstorm` - Generate 3 strategies
  - ~~`POST /api/strategy/analyze`~~ - **DISABLED** for speed

- **Configuration:**
  - `STRATEGY_COUNT=3` - Generates 3 strategies
  - `FAST_MODE=true` - Uses shorter prompts
  - Response time: ~15-20 seconds (was ~2 minutes with 20 strategies + analysis)

## Troubleshooting

### Enrichment service won't start
```bash
# Check if port 8000 is already in use
lsof -i :8000

# Kill existing process
kill -9 <PID>

# Or use a different port
python3 -m uvicorn hpcsim.api:app --host 0.0.0.0 --port 8001
```

### AI layer can't find enrichment service
If you see: `"Cannot connect to enrichment service at http://localhost:8000"`

**Solution:** The buffer is empty and it's trying to pull from enrichment service.

```bash
# Push some data via webhook first:
python3 test_webhook_push.py --loop 5
```

### Virtual environment issues
```bash
cd ai_intelligence_layer

# Check if venv exists
ls -la myenv/

# If missing, recreate:
python3 -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
```

### Module not found errors
```bash
# For enrichment service
cd /Users/rishubmadhav/Documents/GitHub/HPCSimSite
export PYTHONPATH=$PWD:$PYTHONPATH
python3 scripts/serve.py

# For AI layer
cd ai_intelligence_layer
source myenv/bin/activate
python main.py
```

## Full Integration Test Workflow

```bash
# Terminal 1: Start enrichment
cd /Users/rishubmadhav/Documents/GitHub/HPCSimSite
export NEXT_STAGE_CALLBACK_URL=http://localhost:9000/api/ingest/enriched
python3 scripts/serve.py

# Terminal 2: Start AI layer
cd /Users/rishubmadhav/Documents/GitHub/HPCSimSite/ai_intelligence_layer
source myenv/bin/activate
python main.py

# Terminal 3: Test webhook push
cd /Users/rishubmadhav/Documents/GitHub/HPCSimSite/ai_intelligence_layer
python3 test_webhook_push.py --loop 5

# Terminal 3: Generate strategies
python3 test_buffer_usage.py

# View results
cat /tmp/brainstorm_strategies.json | python3 -m json.tool
```

## What's Next?

1. ✅ **Both services running** - Enrichment on 8000, AI on 9000
2. ✅ **Webhook tested** - Data flows from enrichment → AI layer
3. ✅ **Strategies generated** - 3 strategies in ~20 seconds
4. ⏭️ **Real telemetry** - Connect actual race data source
5. ⏭️ **Frontend** - Build UI to display strategies
6. ⏭️ **Production** - Increase to 20 strategies, enable analysis

---

**Status:** 🚀 Both services ready to run!  
**Performance:** ~20 seconds for 3 strategies (vs 2+ minutes for 20 + analysis)  
**Integration:** Webhook push working perfectly
