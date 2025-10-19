"""
Prompt template for strategy analysis.
"""
from typing import List
from models.input_models import EnrichedTelemetryWebhook, RaceContext, Strategy
from utils.validators import TelemetryAnalyzer
from config import get_settings


def build_analyze_prompt_fast(
    enriched_telemetry: List[EnrichedTelemetryWebhook],
    race_context: RaceContext,
    strategies: List[Strategy]
) -> str:
    """Build a faster, more concise analyze prompt."""
    latest = max(enriched_telemetry, key=lambda x: x.lap)
    tire_rate = TelemetryAnalyzer.calculate_tire_degradation_rate(enriched_telemetry)
    tire_cliff = TelemetryAnalyzer.project_tire_cliff(enriched_telemetry, race_context.race_info.current_lap)
    
    strategies_summary = [f"#{s.strategy_id}: {s.strategy_name} ({s.stop_count}-stop, laps {s.pit_laps}, {s.tire_sequence}, {s.risk_level})" for s in strategies[:20]]
    
    return f"""Analyze {len(strategies)} strategies and select TOP 3 for {race_context.driver_state.driver_name} at {race_context.race_info.track_name}.

CURRENT: Lap {race_context.race_info.current_lap}/{race_context.race_info.total_laps}, P{race_context.driver_state.current_position}
TELEMETRY: Tire deg {latest.tire_degradation_index:.2f} (cliff lap {tire_cliff}), Aero {latest.aero_efficiency:.2f}, Fuel {latest.fuel_optimization_score:.2f}, Driver {latest.driver_consistency:.2f}

STRATEGIES:
{chr(10).join(strategies_summary)}

Select TOP 3:
1. RECOMMENDED (highest podium %)
2. ALTERNATIVE (viable backup)
3. CONSERVATIVE (safest)

Return JSON in this EXACT format:
{{
  "top_strategies": [
    {{
      "rank": 1,
      "strategy_id": 7,
      "strategy_name": "Strategy Name",
      "classification": "RECOMMENDED",
      "predicted_outcome": {{
        "finish_position_most_likely": 3,
        "p1_probability": 10,
        "p2_probability": 25,
        "p3_probability": 40,
        "p4_or_worse_probability": 25,
        "confidence_score": 75
      }},
      "risk_assessment": {{
        "risk_level": "medium",
        "key_risks": ["Risk 1", "Risk 2"],
        "success_factors": ["Factor 1", "Factor 2"]
      }},
      "telemetry_insights": {{
        "tire_wear_projection": "Tire analysis based on {latest.tire_degradation_index:.2f}",
        "aero_status": "Aero at {latest.aero_efficiency:.2f}",
        "fuel_margin": "Fuel at {latest.fuel_optimization_score:.2f}",
        "driver_form": "Driver at {latest.driver_consistency:.2f}"
      }},
      "engineer_brief": {{
        "title": "Brief title",
        "summary": "One sentence",
        "key_points": ["Point 1", "Point 2"],
        "execution_steps": ["Step 1", "Step 2"]
      }},
      "driver_audio_script": "Radio message to driver",
      "ecu_commands": {{
        "fuel_mode": "RICH",
        "ers_strategy": "AGGRESSIVE_DEPLOY",
        "engine_mode": "PUSH",
        "brake_balance_adjustment": 0,
        "differential_setting": "BALANCED"
      }}
    }},
    {{
      "rank": 2,
      "strategy_id": 12,
      "strategy_name": "Alternative",
      "classification": "ALTERNATIVE",
      "predicted_outcome": {{"finish_position_most_likely": 4, "p1_probability": 5, "p2_probability": 20, "p3_probability": 35, "p4_or_worse_probability": 40, "confidence_score": 70}},
      "risk_assessment": {{"risk_level": "medium", "key_risks": ["Risk 1"], "success_factors": ["Factor 1"]}},
      "telemetry_insights": {{"tire_wear_projection": "...", "aero_status": "...", "fuel_margin": "...", "driver_form": "..."}},
      "engineer_brief": {{"title": "...", "summary": "...", "key_points": ["..."], "execution_steps": ["..."]}},
      "driver_audio_script": "...",
      "ecu_commands": {{"fuel_mode": "STANDARD", "ers_strategy": "BALANCED", "engine_mode": "STANDARD", "brake_balance_adjustment": 0, "differential_setting": "BALANCED"}}
    }},
    {{
      "rank": 3,
      "strategy_id": 3,
      "strategy_name": "Conservative",
      "classification": "CONSERVATIVE",
      "predicted_outcome": {{"finish_position_most_likely": 5, "p1_probability": 2, "p2_probability": 15, "p3_probability": 28, "p4_or_worse_probability": 55, "confidence_score": 80}},
      "risk_assessment": {{"risk_level": "low", "key_risks": ["Risk 1"], "success_factors": ["Factor 1", "Factor 2"]}},
      "telemetry_insights": {{"tire_wear_projection": "...", "aero_status": "...", "fuel_margin": "...", "driver_form": "..."}},
      "engineer_brief": {{"title": "...", "summary": "...", "key_points": ["..."], "execution_steps": ["..."]}},
      "driver_audio_script": "...",
      "ecu_commands": {{"fuel_mode": "LEAN", "ers_strategy": "CONSERVATIVE", "engine_mode": "SAVE", "brake_balance_adjustment": 0, "differential_setting": "CONSERVATIVE"}}
    }}
  ],
  "situational_context": {{
    "critical_decision_point": "Key decision info",
    "telemetry_alert": "Important telemetry status",
    "key_assumption": "Main assumption",
    "time_sensitivity": "Timing requirement"
  }}
}}"""


def build_analyze_prompt(
    enriched_telemetry: List[EnrichedTelemetryWebhook],
    race_context: RaceContext,
    strategies: List[Strategy]
) -> str:
    """
    Build the analyze prompt for Gemini.
    
    Args:
        enriched_telemetry: Recent enriched telemetry data
        race_context: Current race context
        strategies: Strategies to analyze
        
    Returns:
        Formatted prompt string
    """
    # Generate telemetry summary
    telemetry_summary = TelemetryAnalyzer.generate_telemetry_summary(enriched_telemetry)
    
    # Calculate key metrics
    tire_rate = TelemetryAnalyzer.calculate_tire_degradation_rate(enriched_telemetry)
    tire_cliff_lap = TelemetryAnalyzer.project_tire_cliff(
        enriched_telemetry,
        race_context.race_info.current_lap
    )
    aero_avg = TelemetryAnalyzer.calculate_aero_efficiency_avg(enriched_telemetry)
    ers_pattern = TelemetryAnalyzer.analyze_ers_pattern(enriched_telemetry)
    fuel_critical = TelemetryAnalyzer.is_fuel_critical(enriched_telemetry)
    driver_form = TelemetryAnalyzer.assess_driver_form(enriched_telemetry)
    
    # Get latest telemetry
    latest = max(enriched_telemetry, key=lambda x: x.lap)
    
    # Format strategies for prompt
    strategies_data = []
    for s in strategies:
        strategies_data.append({
            "strategy_id": s.strategy_id,
            "strategy_name": s.strategy_name,
            "stop_count": s.stop_count,
            "pit_laps": s.pit_laps,
            "tire_sequence": s.tire_sequence,
            "brief_description": s.brief_description,
            "risk_level": s.risk_level,
            "key_assumption": s.key_assumption
        })
    
    # Format competitors
    competitors_data = []
    for c in race_context.competitors:
        competitors_data.append({
            "position": c.position,
            "driver": c.driver,
            "tire_compound": c.tire_compound,
            "tire_age_laps": c.tire_age_laps,
            "gap_seconds": round(c.gap_seconds, 1)
        })
    
    prompt = f"""You are Stratega, expert F1 Chief Strategist AI. Analyze the 20 proposed strategies and select the TOP 3.

CURRENT RACE STATE:
Track: {race_context.race_info.track_name}
Current Lap: {race_context.race_info.current_lap} / {race_context.race_info.total_laps}
Weather: {race_context.race_info.weather_condition}

DRIVER STATE:
Driver: {race_context.driver_state.driver_name}
Position: P{race_context.driver_state.current_position}
Current Tires: {race_context.driver_state.current_tire_compound} ({race_context.driver_state.tire_age_laps} laps old)
Fuel Remaining: {race_context.driver_state.fuel_remaining_percent}%

COMPETITORS:
{competitors_data}

TELEMETRY ANALYSIS:
{telemetry_summary}

KEY METRICS:
- Current tire degradation index: {latest.tire_degradation_index:.3f}
- Tire degradation rate: {tire_rate:.3f} per lap
- Projected tire cliff: Lap {tire_cliff_lap}
- Aero efficiency: {aero_avg:.3f} average
- ERS pattern: {ers_pattern}
- Fuel critical: {'YES' if fuel_critical else 'NO'}
- Driver form: {driver_form}

PROPOSED STRATEGIES ({len(strategies_data)} total):
{strategies_data}

ANALYSIS FRAMEWORK:

1. TIRE DEGRADATION PROJECTION:
   - Current tire_degradation_index: {latest.tire_degradation_index:.3f}
   - Rate of change: {tire_rate:.3f} per lap
   - Performance cliff (0.85): Projected lap {tire_cliff_lap}
   - Strategies pitting before cliff = higher probability

2. AERO EFFICIENCY IMPACT:
   - Current aero_efficiency: {aero_avg:.3f}
   - If <0.7: Lap times degrading, prioritize earlier stops
   - If >0.8: Car performing well, can extend stints

3. FUEL MANAGEMENT:
   - Fuel optimization score: {latest.fuel_optimization_score:.3f}
   - Fuel critical: {'YES - Must save fuel' if fuel_critical else 'NO - Can push'}
   - Remaining: {race_context.driver_state.fuel_remaining_percent}%

4. DRIVER CONSISTENCY:
   - Driver consistency: {latest.driver_consistency:.3f}
   - Form: {driver_form}
   - If <0.75: Higher margin for error needed, prefer conservative
   - If >0.9: Can execute aggressive/risky strategies

5. WEATHER & TRACK POSITION:
   - Weather impact: {latest.weather_impact}
   - Track: {race_context.race_info.track_name}
   - Overtaking difficulty consideration

6. COMPETITOR ANALYSIS:
   - Current position: P{race_context.driver_state.current_position}
   - Our tire age: {race_context.driver_state.tire_age_laps} laps
   - Compare with competitors for undercut/overcut opportunities

SELECTION CRITERIA:
- Rank 1 (RECOMMENDED): Highest probability of podium (P1-P3), balanced risk
- Rank 2 (ALTERNATIVE): Different approach, viable if conditions change
- Rank 3 (CONSERVATIVE): Safest option, minimize risk of finishing outside points

OUTPUT FORMAT (JSON only, no markdown):
{{
  "top_strategies": [
    {{
      "rank": 1,
      "strategy_id": 7,
      "strategy_name": "Aggressive Undercut",
      "classification": "RECOMMENDED",
      "predicted_outcome": {{
        "finish_position_most_likely": 3,
        "p1_probability": 8,
        "p2_probability": 22,
        "p3_probability": 45,
        "p4_or_worse_probability": 25,
        "confidence_score": 78
      }},
      "risk_assessment": {{
        "risk_level": "medium",
        "key_risks": [
          "Requires pit stop under 2.5s",
          "Traffic on out-lap could cost 3-5s"
        ],
        "success_factors": [
          "Tire degradation index trending at {tire_rate:.3f} per lap",
          "Window open for undercut"
        ]
      }},
      "telemetry_insights": {{
        "tire_wear_projection": "Current tire_degradation_index {latest.tire_degradation_index:.3f}, will hit 0.85 cliff by lap {tire_cliff_lap}",
        "aero_status": "aero_efficiency {aero_avg:.3f} - car performing {'well' if aero_avg > 0.8 else 'adequately' if aero_avg > 0.7 else 'poorly'}",
        "fuel_margin": "fuel_optimization_score {latest.fuel_optimization_score:.3f} - {'excellent, no fuel saving needed' if latest.fuel_optimization_score > 0.85 else 'adequate' if latest.fuel_optimization_score > 0.7 else 'critical, fuel saving required'}",
        "driver_form": "driver_consistency {latest.driver_consistency:.3f} - {driver_form} confidence in execution"
      }},
      "engineer_brief": {{
        "title": "Recommended: Strategy Name",
        "summary": "One sentence summary with win probability",
        "key_points": [
          "Tire degradation accelerating: {latest.tire_degradation_index:.3f} index now, cliff projected lap {tire_cliff_lap}",
          "Key tactical consideration",
          "Performance advantage analysis",
          "Critical execution requirement"
        ],
        "execution_steps": [
          "Lap X: Action 1",
          "Lap Y: Action 2",
          "Lap Z: Expected outcome"
        ]
      }},
      "driver_audio_script": "Clear radio message to driver about the strategy execution",
      "ecu_commands": {{
        "fuel_mode": "RICH",
        "ers_strategy": "AGGRESSIVE_DEPLOY",
        "engine_mode": "PUSH",
        "brake_balance_adjustment": 0,
        "differential_setting": "BALANCED"
      }}
    }},
    {{
      "rank": 2,
      "strategy_id": 12,
      "strategy_name": "Alternative Strategy",
      "classification": "ALTERNATIVE",
      "predicted_outcome": {{ "finish_position_most_likely": 4, "p1_probability": 5, "p2_probability": 18, "p3_probability": 38, "p4_or_worse_probability": 39, "confidence_score": 72 }},
      "risk_assessment": {{ "risk_level": "medium", "key_risks": ["Risk 1", "Risk 2"], "success_factors": ["Factor 1", "Factor 2"] }},
      "telemetry_insights": {{ "tire_wear_projection": "...", "aero_status": "...", "fuel_margin": "...", "driver_form": "..." }},
      "engineer_brief": {{ "title": "...", "summary": "...", "key_points": ["..."], "execution_steps": ["..."] }},
      "driver_audio_script": "...",
      "ecu_commands": {{ "fuel_mode": "STANDARD", "ers_strategy": "BALANCED", "engine_mode": "STANDARD", "brake_balance_adjustment": 0, "differential_setting": "BALANCED" }}
    }},
    {{
      "rank": 3,
      "strategy_id": 3,
      "strategy_name": "Conservative Strategy",
      "classification": "CONSERVATIVE",
      "predicted_outcome": {{ "finish_position_most_likely": 5, "p1_probability": 2, "p2_probability": 10, "p3_probability": 25, "p4_or_worse_probability": 63, "confidence_score": 85 }},
      "risk_assessment": {{ "risk_level": "low", "key_risks": ["Risk 1"], "success_factors": ["Factor 1", "Factor 2", "Factor 3"] }},
      "telemetry_insights": {{ "tire_wear_projection": "...", "aero_status": "...", "fuel_margin": "...", "driver_form": "..." }},
      "engineer_brief": {{ "title": "...", "summary": "...", "key_points": ["..."], "execution_steps": ["..."] }},
      "driver_audio_script": "...",
      "ecu_commands": {{ "fuel_mode": "STANDARD", "ers_strategy": "CONSERVATIVE", "engine_mode": "SAVE", "brake_balance_adjustment": 0, "differential_setting": "CONSERVATIVE" }}
    }}
  ],
  "situational_context": {{
    "critical_decision_point": "Next 3 laps crucial. Tire degradation index rising faster than expected.",
    "telemetry_alert": "aero_efficiency status and any concerns",
    "key_assumption": "Analysis assumes no safety car. If SC deploys, recommend boxing immediately.",
    "time_sensitivity": "Decision needed within 2 laps to execute strategy effectively."
  }}
}}"""
    
    return prompt
