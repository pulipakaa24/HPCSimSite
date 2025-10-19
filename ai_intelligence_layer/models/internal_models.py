"""
Internal data models for processing.
"""
from pydantic import BaseModel
from typing import Dict, Any


class TelemetryTrends(BaseModel):
    """Calculated trends from enriched telemetry."""
    tire_deg_rate: float  # Per lap rate of change
    aero_efficiency_avg: float  # Moving average
    ers_pattern: str  # "charging", "stable", "depleting"
    fuel_critical: bool  # Whether fuel is a concern
    driver_form: str  # "excellent", "good", "inconsistent"
