"""
Prompt template for strategy brainstorming.
"""
from typing import List
from models.input_models import EnrichedTelemetryWebhook, RaceContext
from utils.validators import TelemetryAnalyzer
from config import get_settings


def build_brainstorm_prompt_fast(
    enriched_telemetry: List[EnrichedTelemetryWebhook],
    race_context: RaceContext
) -> str:
    """Build a faster, more concise prompt for quicker responses (lap-level data)."""
    settings = get_settings()
    count = settings.strategy_count
    latest = max(enriched_telemetry, key=lambda x: x.lap)
    pit_window = latest.optimal_pit_window
    
    if count == 1:
        # Ultra-fast mode: just generate 1 strategy
        return f"""Generate 1 F1 race strategy for {race_context.driver_state.driver_name} at {race_context.race_info.track_name}.

CURRENT: Lap {race_context.race_info.current_lap}/{race_context.race_info.total_laps}, P{race_context.driver_state.current_position}, {race_context.driver_state.current_tire_compound} tires ({race_context.driver_state.tire_age_laps} laps old)

TELEMETRY: Tire deg rate {latest.tire_degradation_rate:.2f}, Cliff risk {latest.tire_cliff_risk:.2f}, Pace {latest.pace_trend}, Pit window laps {pit_window[0]}-{pit_window[1]}

Generate 1 optimal strategy. Min 2 tire compounds required.

JSON: {{"strategies": [{{"strategy_id": 1, "strategy_name": "name", "stop_count": 1, "pit_laps": [32], "tire_sequence": ["medium", "hard"], "brief_description": "one sentence", "risk_level": "medium", "key_assumption": "main assumption"}}]}}"""
    
    elif count <= 5:
        # Fast mode: 2-5 strategies with different approaches
        return f"""Generate {count} diverse F1 race strategies for {race_context.driver_state.driver_name} at {race_context.race_info.track_name}.

CURRENT: Lap {race_context.race_info.current_lap}/{race_context.race_info.total_laps}, P{race_context.driver_state.current_position}, {race_context.driver_state.current_tire_compound} tires ({race_context.driver_state.tire_age_laps} laps old)

TELEMETRY: Tire deg {latest.tire_degradation_rate:.2f}, Cliff risk {latest.tire_cliff_risk:.2f}, Pace {latest.pace_trend}, Delta {latest.performance_delta:+.2f}s, Pit window {pit_window[0]}-{pit_window[1]}

Generate {count} strategies: conservative (1-stop), standard (1-2 stop), aggressive (undercut). Min 2 tire compounds each.

JSON: {{"strategies": [{{"strategy_id": 1, "strategy_name": "Conservative Stay Out", "stop_count": 1, "pit_laps": [35], "tire_sequence": ["medium", "hard"], "brief_description": "extend current stint then hard tires to end", "risk_level": "low", "key_assumption": "tire cliff risk stays below 0.7"}}]}}"""
    
    return f"""Generate {count} F1 race strategies for {race_context.driver_state.driver_name} at {race_context.race_info.track_name}.

CURRENT: Lap {race_context.race_info.current_lap}/{race_context.race_info.total_laps}, P{race_context.driver_state.current_position}, {race_context.driver_state.current_tire_compound} tires ({race_context.driver_state.tire_age_laps} laps old)

TELEMETRY: Tire deg rate {latest.tire_degradation_rate:.2f}, Cliff risk {latest.tire_cliff_risk:.2f}, Pace {latest.pace_trend}, Performance delta {latest.performance_delta:+.2f}s, Pit window laps {pit_window[0]}-{pit_window[1]}

Generate {count} diverse strategies. Min 2 compounds.

JSON: {{"strategies": [{{"strategy_id": 1, "strategy_name": "name", "stop_count": 1, "pit_laps": [32], "tire_sequence": ["medium", "hard"], "brief_description": "one sentence", "risk_level": "low|medium|high|critical", "key_assumption": "main assumption"}}]}}"""


def build_brainstorm_prompt(
    enriched_telemetry: List[EnrichedTelemetryWebhook],
    race_context: RaceContext
) -> str:
    """
    Build the brainstorm prompt for Gemini.
    
    Args:
        enriched_telemetry: Recent enriched telemetry data
        race_context: Current race context
        
    Returns:
        Formatted prompt string
    """
    # Get latest telemetry
    latest = max(enriched_telemetry, key=lambda x: x.lap)
    
    # Format telemetry data (lap-level)
    telemetry_data = []
    for t in sorted(enriched_telemetry, key=lambda x: x.lap, reverse=True)[:10]:
        telemetry_data.append({
            "lap": t.lap,
            "tire_degradation_rate": round(t.tire_degradation_rate, 3),
            "pace_trend": t.pace_trend,
            "tire_cliff_risk": round(t.tire_cliff_risk, 3),
            "optimal_pit_window": t.optimal_pit_window,
            "performance_delta": round(t.performance_delta, 2)
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
    
    prompt = f"""You are an expert F1 strategist. Generate 20 diverse race strategies based on lap-level telemetry.

LAP-LEVEL TELEMETRY METRICS:
- tire_degradation_rate: 0-1 (higher = worse tire wear)
- tire_cliff_risk: 0-1 (probability of hitting tire cliff)
- pace_trend: "improving", "stable", or "declining"
- optimal_pit_window: [start_lap, end_lap] recommended pit range
- performance_delta: seconds vs baseline (negative = slower)

RACE STATE:
Track: {race_context.race_info.track_name}
Current Lap: {race_context.race_info.current_lap} / {race_context.race_info.total_laps}
Weather: {race_context.race_info.weather_condition}
Track Temperature: {race_context.race_info.track_temp_celsius}°C

DRIVER STATE:
Driver: {race_context.driver_state.driver_name}
Position: P{race_context.driver_state.current_position}
Current Tires: {race_context.driver_state.current_tire_compound} ({race_context.driver_state.tire_age_laps} laps old)
Fuel Remaining: {race_context.driver_state.fuel_remaining_percent}%

COMPETITORS:
{competitors_data}

ENRICHED TELEMETRY (Last {len(telemetry_data)} laps, newest first):
{telemetry_data}

KEY INSIGHTS:
- Latest tire degradation rate: {latest.tire_degradation_rate:.3f}
- Latest tire cliff risk: {latest.tire_cliff_risk:.3f}
- Latest pace trend: {latest.pace_trend}
- Optimal pit window: Laps {latest.optimal_pit_window[0]}-{latest.optimal_pit_window[1]}
- Laps remaining: {race_context.race_info.total_laps - race_context.race_info.current_lap}

TASK: Generate exactly 20 diverse strategies.

DIVERSITY: Conservative (1-stop), Standard (balanced), Aggressive (undercut), Reactive (competitor), Contingency (safety car)

RULES:
- Pit laps: {race_context.race_info.current_lap + 1} to {race_context.race_info.total_laps - 1}
- Min 2 tire compounds (F1 rule)
- Consider optimal pit window and tire cliff risk

For each strategy provide:
- strategy_id: 1-20
- strategy_name: Short descriptive name
- stop_count: 1, 2, or 3
- pit_laps: [array of lap numbers]
- tire_sequence: [array of compounds: "soft", "medium", "hard"]
- brief_description: One sentence rationale
- risk_level: "low", "medium", "high", or "critical"
- key_assumption: Main assumption this strategy relies on

OUTPUT FORMAT (JSON only, no markdown):
{{
  "strategies": [
    {{
      "strategy_id": 1,
      "strategy_name": "Conservative 1-Stop",
      "stop_count": 1,
      "pit_laps": [32],
      "tire_sequence": ["medium", "hard"],
      "brief_description": "Extend mediums to lap 32, safe finish on hards",
      "risk_level": "low",
      "key_assumption": "Tire degradation stays below 0.85 until lap 32"
    }}
  ]
}}"""
    
    return prompt
