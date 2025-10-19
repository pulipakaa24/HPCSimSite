# Webhook Push Integration Guide

## Overview

The AI Intelligence Layer supports **two integration models** for receiving enriched telemetry:

1. **Push Model (Webhook)** - Enrichment service POSTs data to AI layer ✅ **RECOMMENDED**
2. **Pull Model** - AI layer fetches data from enrichment service (fallback)

## Push Model (Webhook) - How It Works

```
┌─────────────────────┐         ┌─────────────────────┐
│  HPC Enrichment     │  POST   │  AI Intelligence    │
│  Service            │────────▶│  Layer              │
│  (Port 8000)        │         │  (Port 9000)        │
└─────────────────────┘         └─────────────────────┘
                                         │
                                         ▼
                                 ┌──────────────┐
                                 │ Telemetry    │
                                 │ Buffer       │
                                 │ (in-memory)  │
                                 └──────────────┘
                                         │
                                         ▼
                                 ┌──────────────┐
                                 │ Brainstorm   │
                                 │ & Analyze    │
                                 │ (Gemini AI)  │
                                 └──────────────┘
```

### Configuration

In your **enrichment service** (port 8000), set the callback URL:

```bash
export NEXT_STAGE_CALLBACK_URL=http://localhost:9000/api/ingest/enriched
```

When enrichment is complete for each lap, the service will POST to this endpoint.

### Webhook Endpoint

**Endpoint:** `POST /api/ingest/enriched`

**Request Body:** Single enriched telemetry record (JSON)

```json
{
  "lap": 27,
  "lap_time_seconds": 78.456,
  "tire_degradation_index": 0.72,
  "fuel_remaining_kg": 45.2,
  "aero_efficiency": 0.85,
  "ers_recovery_rate": 0.78,
  "brake_wear_index": 0.65,
  "fuel_optimization_score": 0.82,
  "driver_consistency": 0.88,
  "predicted_tire_cliff_lap": 35,
  "weather_impact": "minimal",
  "hpc_simulation_id": "sim_monaco_lap27_001",
  "metadata": {
    "simulation_timestamp": "2025-10-18T22:15:30Z",
    "confidence_level": 0.92,
    "cluster_nodes_used": 8
  }
}
```

**Response:**

```json
{
  "status": "received",
  "lap": 27,
  "buffer_size": 15
}
```

### Buffer Behavior

- **Max Size:** 100 records (configurable)
- **Storage:** In-memory (cleared on restart)
- **Retrieval:** FIFO - newest data returned first
- **Auto-cleanup:** Oldest records dropped when buffer is full

## Testing the Webhook

### 1. Start the AI Intelligence Layer

```bash
cd ai_intelligence_layer
source myenv/bin/activate  # or your venv
python main.py
```

Verify it's running:
```bash
curl http://localhost:9000/api/health
```

### 2. Simulate Enrichment Service Pushing Data

**Option A: Using the test script**

```bash
# Post single telemetry record
python3 test_webhook_push.py

# Post 10 records with 2s delay between each
python3 test_webhook_push.py --loop 10 --delay 2

# Post 5 records with 1s delay
python3 test_webhook_push.py --loop 5 --delay 1
```

**Option B: Using curl**

```bash
curl -X POST http://localhost:9000/api/ingest/enriched \
  -H "Content-Type: application/json" \
  -d '{
    "lap": 27,
    "lap_time_seconds": 78.456,
    "tire_degradation_index": 0.72,
    "fuel_remaining_kg": 45.2,
    "aero_efficiency": 0.85,
    "ers_recovery_rate": 0.78,
    "brake_wear_index": 0.65,
    "fuel_optimization_score": 0.82,
    "driver_consistency": 0.88,
    "predicted_tire_cliff_lap": 35,
    "weather_impact": "minimal",
    "hpc_simulation_id": "sim_monaco_lap27_001",
    "metadata": {
      "simulation_timestamp": "2025-10-18T22:15:30Z",
      "confidence_level": 0.92,
      "cluster_nodes_used": 8
    }
  }'
```

### 3. Verify Buffer Contains Data

Check the logs - you should see:
```
INFO - Received enriched telemetry webhook: lap 27
INFO - Added telemetry for lap 27 (buffer size: 1)
```

### 4. Test Strategy Generation Using Buffered Data

**Brainstorm endpoint** (no telemetry in request = uses buffer):

```bash
curl -X POST http://localhost:9000/api/strategy/brainstorm \
  -H "Content-Type: application/json" \
  -d '{
    "race_context": {
      "race_info": {
        "track_name": "Monaco",
        "current_lap": 27,
        "total_laps": 58,
        "weather_condition": "Dry",
        "track_temp_celsius": 42
      },
      "driver_state": {
        "driver_name": "Hamilton",
        "current_position": 4,
        "current_tire_compound": "medium",
        "tire_age_laps": 14,
        "fuel_remaining_percent": 47
      },
      "competitors": []
    }
  }' | python3 -m json.tool
```

Check logs for:
```
INFO - Using 10 telemetry records from webhook buffer
```

## Pull Model (Fallback)

If the buffer is empty and no telemetry is provided in the request, the AI layer will **automatically fetch** from the enrichment service:

```bash
GET http://localhost:8000/enriched?limit=10
```

This ensures the system works even without webhook configuration.

## Priority Order

When brainstorm/analyze endpoints are called:

1. **Check request body** - Use `enriched_telemetry` if provided
2. **Check buffer** - Use webhook buffer if it has data
3. **Fetch from service** - Pull from enrichment service as fallback
4. **Error** - If all fail, return 400 error

## Production Recommendations

### For Enrichment Service

```bash
# Configure callback URL
export NEXT_STAGE_CALLBACK_URL=http://ai-layer:9000/api/ingest/enriched

# Add retry logic (recommended)
export CALLBACK_MAX_RETRIES=3
export CALLBACK_TIMEOUT=10
```

### For AI Layer

```python
# config.py - Increase buffer size for production
telemetry_buffer_max_size: int = 500  # Store more history

# Consider Redis for persistent buffer
# (current implementation is in-memory only)
```

### Health Monitoring

```bash
# Check buffer status
curl http://localhost:9000/api/health

# Response includes buffer info (could be added):
{
  "status": "healthy",
  "buffer_size": 25,
  "buffer_max_size": 100
}
```

## Common Issues

### 1. Webhook Not Receiving Data

**Symptoms:** Buffer size stays at 0

**Solutions:**
- Verify enrichment service has `NEXT_STAGE_CALLBACK_URL` configured
- Check network connectivity between services
- Examine enrichment service logs for POST errors
- Confirm AI layer is running on port 9000

### 2. Old Data in Buffer

**Symptoms:** AI uses outdated telemetry

**Solutions:**
- Buffer is FIFO - automatically clears old data
- Restart AI service to clear buffer
- Increase buffer size if race generates data faster than consumption

### 3. Pull Model Used Instead of Push

**Symptoms:** Logs show "fetching from enrichment service" instead of "using buffer"

**Solutions:**
- Confirm webhook is posting data (check buffer size in logs)
- Verify webhook POST is successful (200 response)
- Check if buffer was cleared (restart)

## Integration Examples

### Python (Enrichment Service)

```python
import httpx

async def push_enriched_telemetry(telemetry_data: dict):
    """Push enriched telemetry to AI layer."""
    url = "http://localhost:9000/api/ingest/enriched"
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=telemetry_data, timeout=10.0)
        response.raise_for_status()
        return response.json()
```

### Shell Script (Testing)

```bash
#!/bin/bash
# push_telemetry.sh

for lap in {1..10}; do
  curl -X POST http://localhost:9000/api/ingest/enriched \
    -H "Content-Type: application/json" \
    -d "{\"lap\": $lap, \"tire_degradation_index\": 0.7, ...}"
  sleep 2
done
```

## Benefits of Push Model

✅ **Real-time** - AI layer receives data immediately as enrichment completes  
✅ **Efficient** - No polling, reduces load on enrichment service  
✅ **Decoupled** - Services don't need to coordinate timing  
✅ **Resilient** - Buffer allows AI to process multiple requests from same dataset  
✅ **Simple** - Enrichment service just POST and forget

---

**Next Steps:**
1. Configure `NEXT_STAGE_CALLBACK_URL` in enrichment service
2. Test webhook with `test_webhook_push.py`
3. Monitor logs to confirm push model is working
4. Run brainstorm/analyze and verify buffer usage
