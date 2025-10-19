# Race Context Guide

## Why Race Context is Separate from Telemetry

**Enrichment Service** (port 8000):
- Provides: **Enriched telemetry** (changes every lap)
- Example: tire degradation, aero efficiency, ERS charge

**Client/Frontend**:
- Provides: **Race context** (changes less frequently)
- Example: driver name, current position, track info, competitors

This separation is intentional:
- Telemetry changes **every lap** (real-time HPC data)
- Race context changes **occasionally** (position changes, pit stops)
- Keeps enrichment service simple and focused

## How to Call Brainstorm with Both

### Option 1: Client Provides Both (Recommended)

```bash
curl -X POST http://localhost:9000/api/strategy/brainstorm \
  -H "Content-Type: application/json" \
  -d '{
    "enriched_telemetry": [
      {
        "lap": 27,
        "aero_efficiency": 0.85,
        "tire_degradation_index": 0.72,
        "ers_charge": 0.78,
        "fuel_optimization_score": 0.82,
        "driver_consistency": 0.88,
        "weather_impact": "low"
      }
    ],
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
  }'
```

### Option 2: AI Layer Fetches Telemetry, Client Provides Context

```bash
# Enrichment service POSTs telemetry to webhook
# Then client calls:

curl -X POST http://localhost:9000/api/strategy/brainstorm \
  -H "Content-Type: application/json" \
  -d '{
    "race_context": {
      "race_info": {...},
      "driver_state": {...},
      "competitors": []
    }
  }'
```

AI layer will use telemetry from:
1. **Buffer** (if webhook has pushed data) ← CURRENT SETUP
2. **GET /enriched** from enrichment service (fallback)

## Creating a Race Context Template

Here's a reusable template:

```json
{
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
    "competitors": [
      {
        "position": 1,
        "driver": "Verstappen",
        "tire_compound": "hard",
        "tire_age_laps": 18,
        "gap_seconds": -12.5
      },
      {
        "position": 2,
        "driver": "Leclerc",
        "tire_compound": "medium",
        "tire_age_laps": 10,
        "gap_seconds": -5.2
      },
      {
        "position": 3,
        "driver": "Norris",
        "tire_compound": "medium",
        "tire_age_laps": 12,
        "gap_seconds": -2.1
      },
      {
        "position": 5,
        "driver": "Sainz",
        "tire_compound": "soft",
        "tire_age_laps": 5,
        "gap_seconds": 3.8
      }
    ]
  }
}
```

## Where Does Race Context Come From?

In a real system, race context typically comes from:

1. **Timing System** - Official F1 timing data
   - Current positions
   - Gap times
   - Lap numbers

2. **Team Database** - Historical race data
   - Track information
   - Total laps for this race
   - Weather forecasts

3. **Pit Wall** - Live observations
   - Competitor tire strategies
   - Weather conditions
   - Track temperature

4. **Telemetry Feed** - Some data overlaps
   - Driver's current tires
   - Tire age
   - Fuel remaining

## Recommended Architecture

```
┌─────────────────────┐
│  Timing System      │
│  (Race Control)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐         ┌─────────────────────┐
│  Frontend/Client    │         │  Enrichment Service │
│                     │         │  (Port 8000)        │
│  Manages:           │         │                     │
│  - Race context     │         │  Manages:           │
│  - UI state         │         │  - Telemetry        │
│  - User inputs      │         │  - HPC enrichment   │
└──────────┬──────────┘         └──────────┬──────────┘
           │                               │
           │                               │ POST /ingest/enriched
           │                               │ (telemetry only)
           │                               ▼
           │                    ┌─────────────────────┐
           │                    │  AI Layer Buffer    │
           │                    │  (telemetry only)   │
           │                    └─────────────────────┘
           │                               │
           │ POST /api/strategy/brainstorm │
           │ (race_context + telemetry)    │
           └───────────────────────────────┤
                                           │
                                           ▼
                                ┌─────────────────────┐
                                │  AI Strategy Layer  │
                                │  (Port 9000)        │
                                │                     │
                                │  Generates 3        │
                                │  strategies         │
                                └─────────────────────┘
```

## Python Example: Calling with Race Context

```python
import httpx

async def get_race_strategies(race_context: dict):
    """
    Get strategies from AI layer.
    
    Args:
        race_context: Current race state
        
    Returns:
        3 strategies with pit plans and risk assessments
    """
    url = "http://localhost:9000/api/strategy/brainstorm"
    
    payload = {
        "race_context": race_context
        # enriched_telemetry is optional - AI will use buffer or fetch
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

# Usage:
race_context = {
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

strategies = await get_race_strategies(race_context)
print(f"Generated {len(strategies['strategies'])} strategies")
```

## Alternative: Enrichment Service Sends Full Payload

If you really want enrichment service to send race context too, you'd need to:

### 1. Store race context in enrichment service

```python
# In hpcsim/api.py
_race_context = {
    "race_info": {...},
    "driver_state": {...},
    "competitors": []
}

@app.post("/set_race_context")
async def set_race_context(context: Dict[str, Any]):
    """Update race context (call this when race state changes)."""
    global _race_context
    _race_context = context
    return {"status": "ok"}
```

### 2. Send both in webhook

```python
# In ingest_telemetry endpoint
if _CALLBACK_URL:
    payload = {
        "enriched_telemetry": [enriched],
        "race_context": _race_context
    }
    await client.post(_CALLBACK_URL, json=payload)
```

### 3. Update AI webhook to handle full payload

But this adds complexity. **I recommend keeping it simple**: client provides race_context when calling brainstorm.

---

## Current Working Setup

✅ **Enrichment service** → POSTs telemetry to `/api/ingest/enriched`  
✅ **AI layer** → Stores telemetry in buffer  
✅ **Client** → Calls `/api/strategy/brainstorm` with race_context  
✅ **AI layer** → Uses buffer telemetry + provided race_context → Generates strategies

This is clean, simple, and follows single responsibility principle!
