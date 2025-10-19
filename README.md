# HPCSimSite
HPC simulation site

# F1 Virtual Race Engineer — Enrichment Module

This repo contains a minimal, dependency-free Python module to enrich Raspberry Pi telemetry (derived from FastF1) with HPC-style analytics features. It simulates the first LLM stage (data enrichment) using deterministic heuristics so you can run the pipeline locally and in CI without external services.

## What it does
- Accepts lap-level telemetry JSON records.
- Produces an enriched record with:
	- aero_efficiency (0..1)
	- tire_degradation_index (0..1, higher=worse)
	- ers_charge (0..1)
	- fuel_optimization_score (0..1)
	- driver_consistency (0..1)
	- weather_impact (low|medium|high)

## Expected input schema
Fields are extensible; these cover the initial POC.

Required (or sensible defaults applied):
- lap: int
- speed: float (km/h)
- throttle: float (0..1)
- brake: float (0..1)
- tire_compound: string (soft|medium|hard|inter|wet)
- fuel_level: float (0..1)

Optional:
- ers: float (0..1)
- track_temp: float (Celsius)
- rain_probability: float (0..1)

Example telemetry line (JSONL):
{"lap":27,"speed":282,"throttle":0.91,"brake":0.05,"tire_compound":"medium","fuel_level":0.47}

## Output schema (enriched)
Example:
{"lap":27,"aero_efficiency":0.83,"tire_degradation_index":0.65,"ers_charge":0.72,"fuel_optimization_score":0.91,"driver_consistency":0.89,"weather_impact":"medium"}

## Quick start

### Run the CLI
The CLI reads JSON Lines (one JSON object per line) from stdin or a file and writes enriched JSON lines to stdout or a file.

```bash
python3 scripts/enrich_telemetry.py -i telemetry.jsonl -o enriched.jsonl
```

Or stream:

```bash
cat telemetry.jsonl | python3 scripts/enrich_telemetry.py > enriched.jsonl
```

### Library usage

```python
from hpcsim.enrichment import Enricher

enricher = Enricher()
out = enricher.enrich({
		"lap": 1,
		"speed": 250,
		"throttle": 0.8,
		"brake": 0.1,
		"tire_compound": "medium",
		"fuel_level": 0.6,
})
print(out)
```

## Notes
- The enrichment maintains state across laps (e.g., cumulative tire wear, consistency from last up to 5 laps). If you restart the process mid-race, these will reset; you can re-feed prior laps to restore state.
- If your FastF1-derived telemetry has a different shape, share a sample and we can add adapters.

## Tests

Run minimal tests:

```bash
python3 -m unittest tests/test_enrichment.py -v
```

## API reference (Enrichment Service)

Base URL (local): http://localhost:8000

Interactive docs: http://localhost:8000/docs (Swagger) and http://localhost:8000/redoc

### Run the API server

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
curl -s -X POST http://localhost:8000/ingest/telemetry \
	-H "Content-Type: application/json" \
	-d '{
				"LapNumber": 27,
				"Speed": 282,
				"Throttle": 0.91,
				"Brakes": 0.05,
				"TyreCompound": "medium",
				"FuelRel": 0.47
			}'
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
