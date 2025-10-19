from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import math


# --- Contracts ---
# Input telemetry (example, extensible):
# {
#   "lap": 27,
#   "speed": 282,              # km/h
#   "throttle": 0.91,          # 0..1
#   "brake": 0.05,             # 0..1
#   "tire_compound": "medium",# soft|medium|hard|inter|wet
#   "fuel_level": 0.47,        # 0..1 (fraction of race fuel)
#   "ers": 0.72,               # optional 0..1
#   "track_temp": 38,          # optional Celsius
#   "rain_probability": 0.2    # optional 0..1
# }
#
# Output enrichment:
# {
#   "lap": 27,
#   "aero_efficiency": 0.83,           # 0..1
#   "tire_degradation_index": 0.65,    # 0..1 (higher=worse)
#   "ers_charge": 0.72,                 # 0..1
#   "fuel_optimization_score": 0.91,    # 0..1
#   "driver_consistency": 0.89,         # 0..1
#   "weather_impact": "low|medium|high"
# }


_TIRES_BASE_WEAR = {
    "soft": 0.012,
    "medium": 0.008,
    "hard": 0.006,
    "inter": 0.015,
    "wet": 0.02,
}


@dataclass
class EnricherState:
    last_lap: Optional[int] = None
    lap_speeds: Dict[int, float] = field(default_factory=dict)
    lap_throttle_avg: Dict[int, float] = field(default_factory=dict)
    cumulative_wear: float = 0.0  # 0..1 approx


class Enricher:
    """Heuristic enrichment engine to simulate HPC analytics on telemetry.

    Stateless inputs are enriched with stateful estimates (wear, consistency, etc.).
    Designed for predictable, dependency-free behavior.
    """

    def __init__(self):
        self.state = EnricherState()

    # --- Public API ---
    def enrich(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        lap = int(telemetry.get("lap", 0))
        speed = float(telemetry.get("speed", 0.0))
        throttle = float(telemetry.get("throttle", 0.0))
        brake = float(telemetry.get("brake", 0.0))
        tire_compound = str(telemetry.get("tire_compound", "medium")).lower()
        fuel_level = float(telemetry.get("fuel_level", 0.5))
        ers = telemetry.get("ers")
        track_temp = telemetry.get("track_temp")
        rain_prob = telemetry.get("rain_probability")

        # Update per-lap aggregates
        self._update_lap_stats(lap, speed, throttle)

        # Metrics
        aero_eff = self._compute_aero_efficiency(speed, throttle, brake)
        tire_deg = self._compute_tire_degradation(lap, speed, throttle, tire_compound, track_temp)
        ers_charge = self._compute_ers_charge(ers, throttle, brake)
        fuel_opt = self._compute_fuel_optimization(fuel_level, throttle)
        consistency = self._compute_driver_consistency()
        weather_impact = self._compute_weather_impact(rain_prob, track_temp)

        return {
            "lap": lap,
            "aero_efficiency": round(aero_eff, 3),
            "tire_degradation_index": round(tire_deg, 3),
            "ers_charge": round(ers_charge, 3),
            "fuel_optimization_score": round(fuel_opt, 3),
            "driver_consistency": round(consistency, 3),
            "weather_impact": weather_impact,
        }

    # --- Internals ---
    def _update_lap_stats(self, lap: int, speed: float, throttle: float) -> None:
        if lap <= 0:
            return
        # Store simple aggregates for consistency metrics
        self.state.lap_speeds[lap] = speed
        self.state.lap_throttle_avg[lap] = 0.8 * self.state.lap_throttle_avg.get(lap, throttle) + 0.2 * throttle
        self.state.last_lap = lap

    def _compute_aero_efficiency(self, speed: float, throttle: float, brake: float) -> float:
        # Heuristic: favor high speed with low throttle variance (efficiency) and minimal braking at high speeds
        # Normalize speed into 0..1 assuming 0..330 km/h typical
        speed_n = max(0.0, min(1.0, speed / 330.0))
        brake_penalty = 0.4 * brake
        throttle_bonus = 0.2 * throttle
        base = 0.5 * speed_n + throttle_bonus - brake_penalty
        return max(0.0, min(1.0, base))

    def _compute_tire_degradation(self, lap: int, speed: float, throttle: float, tire_compound: str, track_temp: Optional[float]) -> float:
        base_wear = _TIRES_BASE_WEAR.get(tire_compound, _TIRES_BASE_WEAR["medium"])  # per lap
        temp_factor = 1.0
        if isinstance(track_temp, (int, float)):
            if track_temp > 42:
                temp_factor = 1.25
            elif track_temp < 15:
                temp_factor = 0.9
        stress = 0.5 + 0.5 * throttle + 0.2 * max(0.0, (speed - 250.0) / 100.0)
        wear_this_lap = base_wear * stress * temp_factor
        # Update cumulative wear but cap at 1.0
        self.state.cumulative_wear = min(1.0, self.state.cumulative_wear + wear_this_lap)
        return self.state.cumulative_wear

    def _compute_ers_charge(self, ers: Optional[float], throttle: float, brake: float) -> float:
        if isinstance(ers, (int, float)):
            # simple recovery under braking, depletion under throttle
            ers_level = float(ers) + 0.1 * brake - 0.05 * throttle
        else:
            # infer ers trend if not provided
            ers_level = 0.6 + 0.05 * brake - 0.03 * throttle
        return max(0.0, min(1.0, ers_level))

    def _compute_fuel_optimization(self, fuel_level: float, throttle: float) -> float:
        # Reward keeping throttle moderate when fuel is low and pushing when fuel is high
        fuel_n = max(0.0, min(1.0, fuel_level))
        ideal_throttle = 0.5 + 0.4 * fuel_n  # higher fuel -> higher ideal throttle
        penalty = abs(throttle - ideal_throttle)
        score = 1.0 - penalty
        return max(0.0, min(1.0, score))

    def _compute_driver_consistency(self) -> float:
        # Use last up to 5 laps speed variance to estimate consistency (lower variance -> higher consistency)
        laps = sorted(self.state.lap_speeds.keys())[-5:]
        if not laps:
            return 0.5
        speeds = [self.state.lap_speeds[l] for l in laps]
        mean = sum(speeds) / len(speeds)
        var = sum((s - mean) ** 2 for s in speeds) / len(speeds)
        # Map variance to 0..1; assume 0..(30 km/h)^2 typical range
        norm = min(1.0, var / (30.0 ** 2))
        return max(0.0, 1.0 - norm)

    def _compute_weather_impact(self, rain_prob: Optional[float], track_temp: Optional[float]) -> str:
        score = 0.0
        if isinstance(rain_prob, (int, float)):
            score += 0.7 * float(rain_prob)
        if isinstance(track_temp, (int, float)):
            if track_temp < 12:  # cold tires harder
                score += 0.2
            if track_temp > 45:  # overheating
                score += 0.2
        if score < 0.3:
            return "low"
        if score < 0.6:
            return "medium"
        return "high"
