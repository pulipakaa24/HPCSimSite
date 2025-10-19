"""
Output data models for the AI Intelligence Layer.
Defines schemas for strategy generation and analysis results.
"""
from pydantic import BaseModel, Field
from typing import List, Literal
from models.input_models import Strategy


class BrainstormResponse(BaseModel):
    """Response from strategy brainstorming."""
    strategies: List[Strategy] = Field(..., description="20 diverse strategy options")


class PredictedOutcome(BaseModel):
    """Predicted race outcome for a strategy."""
    finish_position_most_likely: int = Field(..., gt=0, description="Most likely finishing position")
    p1_probability: int = Field(..., ge=0, le=100, description="Probability of P1 (%)")
    p2_probability: int = Field(..., ge=0, le=100, description="Probability of P2 (%)")
    p3_probability: int = Field(..., ge=0, le=100, description="Probability of P3 (%)")
    p4_or_worse_probability: int = Field(..., ge=0, le=100, description="Probability of P4 or worse (%)")
    confidence_score: int = Field(..., ge=0, le=100, description="Overall confidence in prediction (%)")


class RiskAssessment(BaseModel):
    """Risk assessment for a strategy."""
    risk_level: Literal["low", "medium", "high", "critical"] = Field(..., description="Overall risk level")
    key_risks: List[str] = Field(..., description="Primary risks")
    success_factors: List[str] = Field(..., description="Factors that enable success")


class TelemetryInsights(BaseModel):
    """Insights derived from enriched telemetry."""
    tire_wear_projection: str = Field(..., description="Tire degradation projection")
    aero_status: str = Field(..., description="Aerodynamic performance status")
    fuel_margin: str = Field(..., description="Fuel situation assessment")
    driver_form: str = Field(..., description="Driver consistency assessment")


class EngineerBrief(BaseModel):
    """Detailed brief for race engineer."""
    title: str = Field(..., description="Brief title")
    summary: str = Field(..., description="Executive summary")
    key_points: List[str] = Field(..., description="Key decision points")
    execution_steps: List[str] = Field(..., description="Step-by-step execution plan")


class ECUCommands(BaseModel):
    """Electronic Control Unit commands for car setup."""
    fuel_mode: Literal["LEAN", "STANDARD", "RICH"] = Field(..., description="Fuel consumption mode")
    ers_strategy: Literal["CONSERVATIVE", "BALANCED", "AGGRESSIVE_DEPLOY"] = Field(..., description="ERS deployment strategy")
    engine_mode: Literal["SAVE", "STANDARD", "PUSH", "OVERTAKE"] = Field(..., description="Engine power mode")
    brake_balance_adjustment: int = Field(..., ge=-5, le=5, description="Brake balance adjustment")
    differential_setting: Literal["CONSERVATIVE", "BALANCED", "AGGRESSIVE"] = Field(..., description="Differential setting")


class AnalyzedStrategy(BaseModel):
    """A single analyzed strategy with full details."""
    rank: int = Field(..., ge=1, le=3, description="Strategy rank (1-3)")
    strategy_id: int = Field(..., description="Reference to original strategy")
    strategy_name: str = Field(..., description="Strategy name")
    classification: Literal["RECOMMENDED", "ALTERNATIVE", "CONSERVATIVE"] = Field(..., description="Strategy classification")
    predicted_outcome: PredictedOutcome
    risk_assessment: RiskAssessment
    telemetry_insights: TelemetryInsights
    engineer_brief: EngineerBrief
    driver_audio_script: str = Field(..., description="Radio message to driver")
    ecu_commands: ECUCommands


class SituationalContext(BaseModel):
    """Current situational context and alerts."""
    critical_decision_point: str = Field(..., description="Current critical decision point")
    telemetry_alert: str = Field(..., description="Important telemetry alerts")
    key_assumption: str = Field(..., description="Key assumption for analysis")
    time_sensitivity: str = Field(..., description="Time-sensitive factors")


class AnalyzeResponse(BaseModel):
    """Response from strategy analysis."""
    top_strategies: List[AnalyzedStrategy] = Field(..., min_length=3, max_length=3, description="Top 3 strategies")
    situational_context: SituationalContext


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    demo_mode: bool = Field(..., description="Whether demo mode is enabled")
    enrichment_service_url: str = Field(..., description="URL of enrichment service")
