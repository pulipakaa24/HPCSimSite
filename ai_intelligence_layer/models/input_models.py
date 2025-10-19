"""
Input data models for the AI Intelligence Layer.
Defines schemas for enriched telemetry, race context, and request payloads.
"""
from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class EnrichedTelemetryWebhook(BaseModel):
    """Single lap of enriched telemetry data from HPC enrichment module."""
    lap: int = Field(..., description="Lap number")
    aero_efficiency: float = Field(..., ge=0.0, le=1.0, description="Aerodynamic efficiency (0..1, higher is better)")
    tire_degradation_index: float = Field(..., ge=0.0, le=1.0, description="Tire wear (0..1, higher is worse)")
    ers_charge: float = Field(..., ge=0.0, le=1.0, description="Energy recovery system charge level")
    fuel_optimization_score: float = Field(..., ge=0.0, le=1.0, description="Fuel efficiency score")
    driver_consistency: float = Field(..., ge=0.0, le=1.0, description="Lap-to-lap consistency")
    weather_impact: Literal["low", "medium", "high"] = Field(..., description="Weather effect severity")


class RaceInfo(BaseModel):
    """Current race information."""
    track_name: str = Field(..., description="Name of the circuit")
    total_laps: int = Field(..., gt=0, description="Total race laps")
    current_lap: int = Field(..., ge=0, description="Current lap number")
    weather_condition: str = Field(..., description="Current weather (e.g., Dry, Wet, Mixed)")
    track_temp_celsius: float = Field(..., description="Track temperature in Celsius")


class DriverState(BaseModel):
    """Current driver state."""
    driver_name: str = Field(..., description="Driver name")
    current_position: int = Field(..., gt=0, description="Current race position")
    current_tire_compound: Literal["soft", "medium", "hard", "intermediate", "wet"] = Field(..., description="Current tire compound")
    tire_age_laps: int = Field(..., ge=0, description="Laps on current tires")
    fuel_remaining_percent: float = Field(..., ge=0.0, le=100.0, description="Remaining fuel percentage")


class Competitor(BaseModel):
    """Competitor information."""
    position: int = Field(..., gt=0, description="Race position")
    driver: str = Field(..., description="Driver name")
    tire_compound: Literal["soft", "medium", "hard", "intermediate", "wet"] = Field(..., description="Tire compound")
    tire_age_laps: int = Field(..., ge=0, description="Laps on current tires")
    gap_seconds: float = Field(..., description="Gap in seconds (negative if ahead)")


class RaceContext(BaseModel):
    """Complete race context."""
    race_info: RaceInfo
    driver_state: DriverState
    competitors: List[Competitor] = Field(default_factory=list)


class Strategy(BaseModel):
    """A single race strategy option."""
    strategy_id: int = Field(..., description="Unique strategy identifier (1-20)")
    strategy_name: str = Field(..., description="Short descriptive name")
    stop_count: int = Field(..., ge=1, le=3, description="Number of pit stops")
    pit_laps: List[int] = Field(..., description="Lap numbers for pit stops")
    tire_sequence: List[Literal["soft", "medium", "hard", "intermediate", "wet"]] = Field(..., description="Tire compounds in order")
    brief_description: str = Field(..., description="One sentence rationale")
    risk_level: Literal["low", "medium", "high", "critical"] = Field(..., description="Risk assessment")
    key_assumption: str = Field(..., description="Main assumption this strategy relies on")


class BrainstormRequest(BaseModel):
    """Request for strategy brainstorming."""
    enriched_telemetry: Optional[List[EnrichedTelemetryWebhook]] = Field(None, description="Enriched telemetry data")
    race_context: RaceContext = Field(..., description="Current race context")


class AnalyzeRequest(BaseModel):
    """Request for strategy analysis."""
    enriched_telemetry: Optional[List[EnrichedTelemetryWebhook]] = Field(None, description="Enriched telemetry data")
    race_context: RaceContext = Field(..., description="Current race context")
    strategies: List[Strategy] = Field(..., description="Strategies to analyze (typically 20)")


class EnrichedTelemetryWithContext(BaseModel):
    """Webhook payload containing enriched telemetry and race context."""
    enriched_telemetry: EnrichedTelemetryWebhook = Field(..., description="Single lap enriched telemetry")
    race_context: RaceContext = Field(..., description="Current race context")
