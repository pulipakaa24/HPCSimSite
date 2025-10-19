from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Body, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx

from .enrichment import Enricher
from .adapter import normalize_telemetry

app = FastAPI(title="HPCSim Enrichment API", version="0.1.0")

# Single Enricher instance keeps state across laps
_enricher = Enricher()

# Simple in-memory store of recent enriched records
_recent: List[Dict[str, Any]] = []
_MAX_RECENT = 200

# Optional callback URL to forward enriched data to next stage
_CALLBACK_URL = os.getenv("NEXT_STAGE_CALLBACK_URL")


class EnrichedRecord(BaseModel):
    lap: int
    aero_efficiency: float
    tire_degradation_index: float
    ers_charge: float
    fuel_optimization_score: float
    driver_consistency: float
    weather_impact: str


@app.post("/ingest/telemetry")
async def ingest_telemetry(payload: Dict[str, Any] = Body(...)):
    """Receive raw telemetry (from Pi), normalize, enrich, return enriched with race context.

    Optionally forwards to NEXT_STAGE_CALLBACK_URL if set.
    """
    try:
        normalized = normalize_telemetry(payload)
        result = _enricher.enrich_with_context(normalized)
        enriched = result["enriched_telemetry"]
        race_context = result["race_context"]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to enrich: {e}")

    # Store enriched telemetry in recent buffer
    _recent.append(enriched)
    if len(_recent) > _MAX_RECENT:
        del _recent[: len(_recent) - _MAX_RECENT]

    # Async forward to next stage if configured
    # Send both enriched telemetry and race context
    if _CALLBACK_URL:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(_CALLBACK_URL, json=result)
        except Exception:
            # Don't fail ingestion if forwarding fails; log could be added here
            pass

    return JSONResponse(result)


@app.post("/enriched")
async def post_enriched(enriched: EnrichedRecord):
    """Allow posting externally enriched records (bypass local computation)."""
    rec = enriched.model_dump()
    _recent.append(rec)
    if len(_recent) > _MAX_RECENT:
        del _recent[: len(_recent) - _MAX_RECENT]
    return JSONResponse(rec)


@app.get("/enriched")
async def list_enriched(limit: int = 50):
    limit = max(1, min(200, limit))
    return JSONResponse(_recent[-limit:])


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "stored": len(_recent)}
