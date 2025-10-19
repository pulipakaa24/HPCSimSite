# Integration Updates - Enrichment to AI Intelligence Layer

## Overview
This document describes the updates made to integrate the HPC enrichment stage with the AI Intelligence Layer for automatic strategy generation.

## Changes Summary

### 1. AI Intelligence Layer (`/api/ingest/enriched` endpoint)

**Previous behavior:**
- Received only enriched telemetry data
- Stored data in buffer
- Required manual calls to `/api/strategy/brainstorm` endpoint

**New behavior:**
- Receives **both** enriched telemetry AND race context
- Stores telemetry in buffer AND updates global race context
- **Automatically triggers strategy brainstorming** when sufficient data is available (≥3 laps)
- Returns generated strategies in the webhook response

**Updated Input Model:**
```python
class EnrichedTelemetryWithContext(BaseModel):
    enriched_telemetry: EnrichedTelemetryWebhook
    race_context: RaceContext
```

**Response includes:**
- `status`: Processing status
- `lap`: Current lap number
- `buffer_size`: Number of telemetry records in buffer
- `strategies_generated`: Number of strategies created (if auto-brainstorm triggered)
- `strategies`: List of strategy objects (if auto-brainstorm triggered)

### 2. Enrichment Stage Output

**Previous output (enriched telemetry only):**
```json
{
  "lap": 27,
  "aero_efficiency": 0.83,
  "tire_degradation_index": 0.65,
  "ers_charge": 0.72,
  "fuel_optimization_score": 0.91,
  "driver_consistency": 0.89,
  "weather_impact": "low"
}
```

**New output (enriched telemetry + race context):**
```json
{
  "enriched_telemetry": {
    "lap": 27,
    "aero_efficiency": 0.83,
    "tire_degradation_index": 0.65,
    "ers_charge": 0.72,
    "fuel_optimization_score": 0.91,
    "driver_consistency": 0.89,
    "weather_impact": "low"
  },
  "race_context": {
    "race_info": {
      "track_name": "Monza",
      "total_laps": 51,
      "current_lap": 27,
      "weather_condition": "Dry",
      "track_temp_celsius": 42.5
    },
    "driver_state": {
      "driver_name": "Alonso",
      "current_position": 5,
      "current_tire_compound": "medium",
      "tire_age_laps": 12,
      "fuel_remaining_percent": 65.0
    },
    "competitors": [
      {
        "position": 4,
        "driver": "Sainz",
        "tire_compound": "medium",
        "tire_age_laps": 10,
        "gap_seconds": -2.3
      },
      // ... more competitors
    ]
  }
}
```

### 3. Modified Components

#### `hpcsim/enrichment.py`
- Added `enrich_with_context()` method (new primary method)
- Maintains backward compatibility with `enrich()` (legacy method)
- Builds complete race context including:
  - Race information (track, laps, weather)
  - Driver state (position, tires, fuel)
  - Competitor data (mock generation for testing)

#### `hpcsim/adapter.py`
- Extended to normalize additional fields:
  - `track_name`
  - `total_laps`
  - `driver_name`
  - `current_position`
  - `tire_life_laps`
  - `rainfall`

#### `hpcsim/api.py`
- Updated `/ingest/telemetry` endpoint to use `enrich_with_context()`
- Webhook now sends complete payload with enriched telemetry + race context

#### `scripts/simulate_pi_stream.py`
- Updated to include race context fields in telemetry data:
  - `track_name`: "Monza"
  - `driver_name`: "Alonso"
  - `current_position`: 5
  - `fuel_level`: Calculated based on lap progress

#### `scripts/enrich_telemetry.py`
- Added `--full-context` flag for outputting complete race context
- Default behavior unchanged (backward compatible)

#### `ai_intelligence_layer/main.py`
- Updated `/api/ingest/enriched` endpoint to:
  - Accept `EnrichedTelemetryWithContext` model
  - Store race context globally
  - Auto-trigger strategy brainstorming with ≥3 laps of data
  - Return strategies in webhook response

#### `ai_intelligence_layer/models/input_models.py`
- Added `EnrichedTelemetryWithContext` model

## Usage

### Running the Full Pipeline

1. **Start the enrichment service:**
```bash
export NEXT_STAGE_CALLBACK_URL=http://localhost:9000/api/ingest/enriched
uvicorn hpcsim.api:app --host 0.0.0.0 --port 8000
```

2. **Start the AI Intelligence Layer:**
```bash
cd ai_intelligence_layer
uvicorn main:app --host 0.0.0.0 --port 9000
```

3. **Stream telemetry data:**
```bash
python scripts/simulate_pi_stream.py \
  --data ALONSO_2023_MONZA_RACE \
  --endpoint http://localhost:8000/ingest/telemetry \
  --speed 10.0
```

### What Happens

1. Pi simulator sends raw telemetry to enrichment service (port 8000)
2. Enrichment service:
   - Normalizes telemetry
   - Enriches with HPC metrics
   - Builds race context
   - Forwards to AI layer webhook (port 9000)
3. AI Intelligence Layer:
   - Receives enriched telemetry + race context
   - Stores in buffer
   - **Automatically generates strategies** when buffer has ≥3 laps
   - Returns strategies in webhook response

### Manual Testing

Test enrichment with context:
```bash
echo '{"lap":10,"speed":280,"throttle":0.85,"brake":0.05,"tire_compound":"medium","fuel_level":0.7,"track_temp":42.5,"total_laps":51,"track_name":"Monza","driver_name":"Alonso","current_position":5,"tire_life_laps":8}' | \
python scripts/enrich_telemetry.py --full-context
```

Test webhook directly:
```bash
curl -X POST http://localhost:9000/api/ingest/enriched \
  -H "Content-Type: application/json" \
  -d '{
    "enriched_telemetry": {
      "lap": 15,
      "aero_efficiency": 0.85,
      "tire_degradation_index": 0.3,
      "ers_charge": 0.75,
      "fuel_optimization_score": 0.9,
      "driver_consistency": 0.88,
      "weather_impact": "low"
    },
    "race_context": {
      "race_info": {
        "track_name": "Monza",
        "total_laps": 51,
        "current_lap": 15,
        "weather_condition": "Dry",
        "track_temp_celsius": 42.5
      },
      "driver_state": {
        "driver_name": "Alonso",
        "current_position": 5,
        "current_tire_compound": "medium",
        "tire_age_laps": 10,
        "fuel_remaining_percent": 70.0
      },
      "competitors": []
    }
  }'
```

## Testing

Run all tests:
```bash
python -m pytest tests/ -v
```

Specific test files:
```bash
# Unit tests for enrichment
python -m pytest tests/test_enrichment.py -v

# Integration tests
python -m pytest tests/test_integration.py -v
```

## Backward Compatibility

- The legacy `enrich()` method still works and returns only enriched metrics
- The `/api/strategy/brainstorm` endpoint can still be called manually
- Scripts work with or without race context fields
- Existing tests continue to pass

## Key Benefits

1. **Automatic Strategy Generation**: No manual endpoint calls needed
2. **Complete Context**: AI layer receives all necessary data in one webhook
3. **Real-time Processing**: Strategies generated as telemetry arrives
4. **Stateful Enrichment**: Enricher maintains race state across laps
5. **Realistic Competitor Data**: Mock competitors generated for testing
6. **Type Safety**: Pydantic models ensure data validity

## Data Flow

```
Pi/Simulator → Enrichment Service → AI Intelligence Layer
    (raw)         (enrich + context)    (auto-brainstorm)
                                              ↓
                                        Strategies
```

## Notes

- **Minimum buffer size**: AI layer waits for ≥3 laps before auto-brainstorming
- **Competitor data**: Currently mock-generated; can be replaced with real data
- **Fuel conversion**: Automatically converts 0-1 range to 0-100 percentage
- **Tire normalization**: Maps all tire compound variations to standard names
- **Weather detection**: Based on `rainfall` boolean and temperature
