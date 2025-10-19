from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
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
#   
#   # Additional fields for race context:
#   "track_name": "Monza",     # optional
#   "total_laps": 51,          # optional
#   "driver_name": "Alonso",   # optional
#   "current_position": 5,     # optional
#   "tire_life_laps": 12,      # optional (tire age)
#   "rainfall": False          # optional (boolean)
# }
#
# Output enrichment + race context:
# {
#   "enriched_telemetry": {
#     "lap": 27,
#     "aero_efficiency": 0.83,
#     "tire_degradation_index": 0.65,
#     "ers_charge": 0.72,
#     "fuel_optimization_score": 0.91,
#     "driver_consistency": 0.89,
#     "weather_impact": "low|medium|high"
#   },
#   "race_context": {
#     "race_info": {...},
#     "driver_state": {...},
#     "competitors": [...]
#   }
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
    
    # Race context state
    track_name: str = "Unknown Circuit"
    total_laps: int = 50
    driver_name: str = "Driver"
    current_position: int = 10
    tire_compound_history: List[str] = field(default_factory=list)


class Enricher:
    """Heuristic enrichment engine to simulate HPC analytics on telemetry.

    Stateless inputs are enriched with stateful estimates (wear, consistency, etc.).
    Designed for predictable, dependency-free behavior.
    """

    def __init__(self):
        self.state = EnricherState()

    # --- Public API ---
    def enrich(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method - returns only enriched telemetry metrics."""
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
    
    def enrich_with_context(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich telemetry and build complete race context for AI layer."""
        # Extract all fields
        lap = int(telemetry.get("lap", telemetry.get("lap_number", 0)))
        speed = float(telemetry.get("speed", 0.0))
        throttle = float(telemetry.get("throttle", 0.0))
        brake = float(telemetry.get("brake", 0.0))
        tire_compound = str(telemetry.get("tire_compound", "medium")).lower()
        fuel_level = float(telemetry.get("fuel_level", 0.5))
        ers = telemetry.get("ers")
        track_temp = telemetry.get("track_temp", telemetry.get("track_temperature"))
        rain_prob = telemetry.get("rain_probability")
        rainfall = telemetry.get("rainfall", False)
        
        # Race context fields
        track_name = telemetry.get("track_name", self.state.track_name)
        total_laps = int(telemetry.get("total_laps", self.state.total_laps))
        driver_name = telemetry.get("driver_name", self.state.driver_name)
        current_position = int(telemetry.get("current_position", self.state.current_position))
        tire_life_laps = int(telemetry.get("tire_life_laps", 0))
        
        # Update state with race context
        if track_name:
            self.state.track_name = track_name
        if total_laps:
            self.state.total_laps = total_laps
        if driver_name:
            self.state.driver_name = driver_name
        if current_position:
            self.state.current_position = current_position
            
        # Track tire compound changes
        if tire_compound and (not self.state.tire_compound_history or 
                              self.state.tire_compound_history[-1] != tire_compound):
            self.state.tire_compound_history.append(tire_compound)

        # Update per-lap aggregates
        self._update_lap_stats(lap, speed, throttle)

        # Compute enriched metrics
        aero_eff = self._compute_aero_efficiency(speed, throttle, brake)
        tire_deg = self._compute_tire_degradation(lap, speed, throttle, tire_compound, track_temp)
        ers_charge = self._compute_ers_charge(ers, throttle, brake)
        fuel_opt = self._compute_fuel_optimization(fuel_level, throttle)
        consistency = self._compute_driver_consistency()
        weather_impact = self._compute_weather_impact(rain_prob, track_temp)

        # Build enriched telemetry
        enriched_telemetry = {
            "lap": lap,
            "aero_efficiency": round(aero_eff, 3),
            "tire_degradation_index": round(tire_deg, 3),
            "ers_charge": round(ers_charge, 3),
            "fuel_optimization_score": round(fuel_opt, 3),
            "driver_consistency": round(consistency, 3),
            "weather_impact": weather_impact,
        }
        
        # Build race context
        race_context = self._build_race_context(
            lap=lap,
            total_laps=total_laps,
            track_name=track_name,
            track_temp=track_temp,
            rainfall=rainfall,
            driver_name=driver_name,
            current_position=current_position,
            tire_compound=tire_compound,
            tire_life_laps=tire_life_laps,
            fuel_level=fuel_level
        )
        
        return {
            "enriched_telemetry": enriched_telemetry,
            "race_context": race_context
        }
    
    def _build_race_context(
        self,
        lap: int,
        total_laps: int,
        track_name: str,
        track_temp: Optional[float],
        rainfall: bool,
        driver_name: str,
        current_position: int,
        tire_compound: str,
        tire_life_laps: int,
        fuel_level: float
    ) -> Dict[str, Any]:
        """Build complete race context structure for AI layer."""
        
        # Normalize tire compound for output
        tire_map = {
            "soft": "soft",
            "medium": "medium", 
            "hard": "hard",
            "inter": "intermediate",
            "intermediate": "intermediate",
            "wet": "wet"
        }
        normalized_tire = tire_map.get(tire_compound.lower(), "medium")
        
        # Determine weather condition
        if rainfall:
            weather_condition = "Wet"
        else:
            weather_condition = "Dry"
            
        race_context = {
            "race_info": {
                "track_name": track_name,
                "total_laps": total_laps,
                "current_lap": lap,
                "weather_condition": weather_condition,
                "track_temp_celsius": float(track_temp) if track_temp is not None else 25.0
            },
            "driver_state": {
                "driver_name": driver_name,
                "current_position": current_position,
                "current_tire_compound": normalized_tire,
                "tire_age_laps": tire_life_laps,
                "fuel_remaining_percent": fuel_level * 100.0  # Convert 0..1 to 0..100
            },
            "competitors": self._generate_mock_competitors(current_position, normalized_tire, tire_life_laps)
        }
        
        return race_context
    
    def _generate_mock_competitors(
        self, 
        current_position: int, 
        current_tire: str,
        current_tire_age: int
    ) -> List[Dict[str, Any]]:
        """Generate realistic mock competitor data for race context."""
        competitors = []
        
        # Driver names pool
        driver_names = [
            "Verstappen", "Hamilton", "Leclerc", "Perez", "Sainz",
            "Russell", "Norris", "Piastri", "Alonso", "Stroll",
            "Gasly", "Ocon", "Tsunoda", "Ricciardo", "Bottas",
            "Zhou", "Magnussen", "Hulkenberg", "Albon", "Sargeant"
        ]
        
        tire_compounds = ["soft", "medium", "hard"]
        
        # Generate positions around the current driver (±3 positions)
        positions_to_show = []
        for offset in [-3, -2, -1, 1, 2, 3]:
            pos = current_position + offset
            if 1 <= pos <= 20 and pos != current_position:
                positions_to_show.append(pos)
        
        for pos in sorted(positions_to_show):
            # Calculate gap (negative if ahead, positive if behind)
            gap_base = (pos - current_position) * 2.5  # ~2.5s per position
            gap_variation = (hash(str(pos)) % 100) / 50.0 - 1.0  # -1 to +1 variation
            gap = gap_base + gap_variation
            
            # Choose tire compound (bias towards similar strategy)
            tire_choice = current_tire
            if abs(hash(str(pos)) % 3) == 0:  # 33% different strategy
                tire_choice = tire_compounds[pos % 3]
            
            # Tire age variation
            tire_age = max(0, current_tire_age + (hash(str(pos * 7)) % 11) - 5)
            
            competitor = {
                "position": pos,
                "driver": driver_names[(pos - 1) % len(driver_names)],
                "tire_compound": tire_choice,
                "tire_age_laps": tire_age,
                "gap_seconds": round(gap, 2)
            }
            competitors.append(competitor)
        
        return competitors

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
