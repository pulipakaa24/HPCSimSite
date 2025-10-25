# Guido.tech: 
## An F1 AI Race Engineer System

Real-time F1 race strategy system combining telemetry enrichment with AI-powered strategy generation. The system receives lap-by-lap telemetry from vehicle controller simulation, enriches it with performance analytics, and generates dynamic race strategies using Google Gemini AI before sending control updates back to the vehicle controller simulation.

## Architecture

The system consists of two main services:

1. **Enrichment Service** (`hpcsim/`) - Port 8000
   - Receives raw telemetry from Raspberry Pi simulator
   - Enriches data with tire degradation, pace trends, pit window predictions
   - Forwards to AI Layer via webhook

2. **AI Intelligence Layer** (`ai_intelligence_layer/`) - Port 9000
   - WebSocket server for real-time Pi communication
   - Generates race strategies using Google Gemini AI
   - Sends control commands (brake bias, differential slip) back to Pi
   - Web dashboard for monitoring

## Quick Start

### Prerequisites

- Python 3.9+
- Google Gemini API key

### 1. Install Dependencies

```bash
# Install enrichment service dependencies
pip install -r requirements.txt

# Install AI layer dependencies
pip install -r ai_intelligence_layer/requirements.txt
```

### 2. Configure Environment

Create `ai_intelligence_layer/.env`:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
ENVIRONMENT=development
FAST_MODE=true
STRATEGY_COUNT=3
```

### 3. Run the System

**Option A: Run both services together (recommended)**

```bash
python3 scripts/serve.py
```

Optional downstream forwarding:

```bash
export NEXT_STAGE_CALLBACK_URL="http://localhost:9000/next-stage"
python3 scripts/serve.py
```

When set, every enriched record is also POSTed to the callback URL (best-effort, async). Ingestion still returns 200 even if forwarding fails.

### POST /ingest/telemetry

Accepts raw Raspberry Pi or FastF1-style telemetry, normalizes field names, enriches it, stores a recent copy, and returns the enriched record.

- Content-Type: application/json
- Request body (flexible/aliases allowed):
	- lap (int) — aliases: Lap, LapNumber
	- speed (float, km/h) — alias: Speed
	- throttle (0..1) — alias: Throttle
	- brake (0..1) — aliases: Brake, Brakes
	- tire_compound (string: soft|medium|hard|inter|wet) — aliases: Compound, TyreCompound, Tire
	- fuel_level (0..1) — aliases: Fuel, FuelRel, FuelLevel
	- ers (0..1) — aliases: ERS, ERSCharge (optional)
	- track_temp (Celsius) — alias: TrackTemp (optional)
	- rain_probability (0..1) — aliases: RainProb, PrecipProb (optional)

Example request:

```bash

```

Response 200 (application/json):

```json
{
	"lap": 27,
	"aero_efficiency": 0.83,
	"tire_degradation_index": 0.65,
	"ers_charge": 0.72,
	"fuel_optimization_score": 0.91,
	"driver_consistency": 0.89,
	"weather_impact": "medium"
}
```

Errors:
- 400 if the body cannot be normalized/enriched

### POST /enriched

Accepts an already-enriched record (useful if enrichment runs elsewhere). Stores and echoes it back.

- Content-Type: application/json
- Request body:
	- lap: int
	- aero_efficiency: float (0..1)
	- tire_degradation_index: float (0..1)
	- ers_charge: float (0..1)
	- fuel_optimization_score: float (0..1)
	- driver_consistency: float (0..1)
	- weather_impact: string (low|medium|high)

Example:

```bash
curl -s -X POST http://localhost:8000/enriched \
	-H "Content-Type: application/json" \
	-d '{
				"lap": 99,
				"aero_efficiency": 0.8,
				"tire_degradation_index": 0.5,
				"ers_charge": 0.6,
				"fuel_optimization_score": 0.9,
				"driver_consistency": 0.95,
				"weather_impact": "low"
			}'
```

### GET /enriched

Returns an array of the most recent enriched records.

- Query params:
	- limit: int (1..200, default 50)

Example:

```bash
curl -s "http://localhost:8000/enriched?limit=10"
```

Response 200 example:

```json
[
	{ "lap": 27, "aero_efficiency": 0.83, "tire_degradation_index": 0.65, "ers_charge": 0.72, "fuel_optimization_score": 0.91, "driver_consistency": 0.89, "weather_impact": "medium" }
]
```

### GET /healthz

Health check.

```bash
curl -s http://localhost:8000/healthz
```

Response 200 example:

```json
{ "status": "ok", "stored": 5 }
```

### Notes
- Authentication/authorization is not enabled yet; add API keys or headers if deploying externally.
- Storage is in-memory (most recent ~200 records). For persistence, we can add Redis/SQLite.
- Forwarding to downstream (e.g., strategy LLM stage) is opt-in via `NEXT_STAGE_CALLBACK_URL`.
