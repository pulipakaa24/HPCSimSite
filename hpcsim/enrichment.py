from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import pandas as pd


# --- LAP-LEVEL TELEMETRY CONTRACT ---
# Input from Raspberry Pi (lap-level data):
# {
#   "lap_number": 27,
#   "total_laps": 51,
#   "lap_time": "0 days 00:01:27.318000",
#   "average_speed": 234.62,
#   "max_speed": 333.0,
#   "tire_compound": "MEDIUM",
#   "tire_life_laps": 19,
#   "track_temperature": 43.6,
#   "rainfall": false
# }


_TIRE_DEGRADATION_RATES = {
    "soft": 0.030,      # Fast degradation
    "medium": 0.020,    # Moderate degradation  
    "hard": 0.015,      # Slow degradation
    "inter": 0.025,
    "wet": 0.022,
}

_TIRE_CLIFF_THRESHOLD = 25  # Laps before cliff risk increases significantly


@dataclass
class EnricherState:
    """Maintains race state across laps for trend analysis."""
    lap_times: List[float] = field(default_factory=list)  # Recent lap times in seconds
    lap_speeds: List[float] = field(default_factory=list)  # Recent average speeds
    current_tire_age: int = 0
    current_tire_compound: str = "medium"
    tire_stint_start_lap: int = 1
    total_laps: int = 51
    track_name: str = "Monza"


class Enricher:
    """
    HPC-simulated enrichment for lap-level F1 telemetry.
    
    Accepts lap-level data from Raspberry Pi and generates performance insights
    that simulate HPC computational analysis.
    """

    def __init__(self):
        self.state = EnricherState()
        self._baseline_lap_time: Optional[float] = None  # Best lap time as baseline

    def enrich_lap_data(self, lap_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main enrichment method for lap-level data.
        Returns enriched telemetry + race context for AI layer.
        """
        # Extract lap data
        lap_number = int(lap_data.get("lap_number", 0))
        total_laps = int(lap_data.get("total_laps", 51))
        lap_time_str = lap_data.get("lap_time")
        average_speed = float(lap_data.get("average_speed", 0.0))
        max_speed = float(lap_data.get("max_speed", 0.0))
        tire_compound = str(lap_data.get("tire_compound", "MEDIUM")).lower()
        tire_life_laps = int(lap_data.get("tire_life_laps", 0))
        track_temperature = float(lap_data.get("track_temperature", 25.0))
        rainfall = bool(lap_data.get("rainfall", False))
        
        # Convert lap time to seconds
        lap_time_seconds = self._parse_lap_time(lap_time_str)
        
        # Update state
        self.state.lap_times.append(lap_time_seconds)
        self.state.lap_speeds.append(average_speed)
        self.state.current_tire_age = tire_life_laps
        self.state.current_tire_compound = tire_compound
        self.state.total_laps = total_laps
        
        # Keep only last 10 laps for analysis
        if len(self.state.lap_times) > 10:
            self.state.lap_times = self.state.lap_times[-10:]
            self.state.lap_speeds = self.state.lap_speeds[-10:]
        
        # Set baseline (best lap time)
        if self._baseline_lap_time is None or lap_time_seconds < self._baseline_lap_time:
            self._baseline_lap_time = lap_time_seconds
        
        # Compute HPC-simulated insights
        tire_deg_rate = self._compute_tire_degradation_rate(tire_compound, tire_life_laps, track_temperature)
        pace_trend = self._compute_pace_trend()
        tire_cliff_risk = self._compute_tire_cliff_risk(tire_compound, tire_life_laps)
        pit_window = self._compute_optimal_pit_window(lap_number, total_laps, tire_life_laps, tire_compound)
        performance_delta = self._compute_performance_delta(lap_time_seconds)
        
        # Build enriched telemetry
        enriched_telemetry = {
            "lap": lap_number,
            "tire_degradation_rate": round(tire_deg_rate, 3),
            "pace_trend": pace_trend,
            "tire_cliff_risk": round(tire_cliff_risk, 3),
            "optimal_pit_window": pit_window,
            "performance_delta": round(performance_delta, 2)
        }
        
        # Build race context
        race_context = {
            "race_info": {
                "track_name": self.state.track_name,
                "total_laps": total_laps,
                "current_lap": lap_number,
                "weather_condition": "Wet" if rainfall else "Dry",
                "track_temp_celsius": track_temperature
            },
            "driver_state": {
                "driver_name": "Alonso",
                "current_position": 5,  # Mock - could be passed in
                "current_tire_compound": tire_compound,
                "tire_age_laps": tire_life_laps,
                "fuel_remaining_percent": self._estimate_fuel(lap_number, total_laps)
            }
        }
        
        return {
            "enriched_telemetry": enriched_telemetry,
            "race_context": race_context
        }
    
    # --- HPC-Simulated Computation Methods ---
    
    def _compute_tire_degradation_rate(self, tire_compound: str, tire_age: int, track_temp: float) -> float:
        """
        Simulate HPC computation of tire degradation rate.
        Returns 0-1 value (higher = worse degradation).
        """
        base_rate = _TIRE_DEGRADATION_RATES.get(tire_compound, 0.020)
        
        # Temperature effect: higher temp = more degradation
        temp_multiplier = 1.0
        if track_temp > 45:
            temp_multiplier = 1.3
        elif track_temp > 40:
            temp_multiplier = 1.15
        elif track_temp < 20:
            temp_multiplier = 0.9
        
        # Age effect: exponential increase after certain threshold
        age_multiplier = 1.0
        if tire_age > 20:
            age_multiplier = 1.0 + ((tire_age - 20) * 0.05)  # +5% per lap over 20
        
        degradation = base_rate * tire_age * temp_multiplier * age_multiplier
        return min(1.0, degradation)
    
    def _compute_pace_trend(self) -> str:
        """
        Analyze recent lap times to determine pace trend.
        Returns: "improving", "stable", or "declining"
        """
        if len(self.state.lap_times) < 3:
            return "stable"
        
        recent_laps = self.state.lap_times[-5:]  # Last 5 laps
        
        # Calculate trend (simple linear regression)
        avg_first_half = sum(recent_laps[:len(recent_laps)//2]) / max(1, len(recent_laps)//2)
        avg_second_half = sum(recent_laps[len(recent_laps)//2:]) / max(1, len(recent_laps) - len(recent_laps)//2)
        
        diff = avg_second_half - avg_first_half
        
        if diff < -0.5:  # Getting faster by more than 0.5s
            return "improving"
        elif diff > 0.5:  # Getting slower by more than 0.5s
            return "declining"
        else:
            return "stable"
    
    def _compute_tire_cliff_risk(self, tire_compound: str, tire_age: int) -> float:
        """
        Compute probability of hitting tire performance cliff.
        Returns 0-1 (0 = no risk, 1 = imminent cliff).
        """
        # Different compounds have different cliff points
        cliff_points = {
            "soft": 15,
            "medium": 25,
            "hard": 35,
            "inter": 20,
            "wet": 18
        }
        
        cliff_point = cliff_points.get(tire_compound, 25)
        
        if tire_age < cliff_point - 5:
            return 0.0
        elif tire_age >= cliff_point + 5:
            return 1.0
        else:
            # Linear risk increase in 10-lap window around cliff point
            return (tire_age - (cliff_point - 5)) / 10.0
    
    def _compute_optimal_pit_window(self, current_lap: int, total_laps: int, tire_age: int, tire_compound: str) -> List[int]:
        """
        Calculate optimal pit stop window based on tire degradation.
        Returns [start_lap, end_lap] for pit window.
        """
        cliff_risk = self._compute_tire_cliff_risk(tire_compound, tire_age)
        
        if cliff_risk > 0.7:
            # Urgent pit needed
            return [current_lap + 1, current_lap + 3]
        elif cliff_risk > 0.4:
            # Pit soon
            return [current_lap + 3, current_lap + 6]
        else:
            # Tire still good, estimate based on compound
            if tire_compound == "soft":
                laps_remaining = max(0, 18 - tire_age)
            elif tire_compound == "medium":
                laps_remaining = max(0, 28 - tire_age)
            else:  # hard
                laps_remaining = max(0, 38 - tire_age)
            
            pit_lap = min(current_lap + laps_remaining, total_laps - 5)
            return [max(current_lap + 1, pit_lap - 2), pit_lap + 2]
    
    def _compute_performance_delta(self, current_lap_time: float) -> float:
        """
        Calculate performance delta vs baseline lap time.
        Negative = slower than baseline, Positive = faster.
        """
        if self._baseline_lap_time is None:
            return 0.0
        
        return self._baseline_lap_time - current_lap_time  # Negative if slower
    
    def _estimate_fuel(self, current_lap: int, total_laps: int) -> float:
        """Estimate remaining fuel percentage based on lap progression."""
        return max(0.0, 100.0 * (1.0 - (current_lap / total_laps)))
    
    def _parse_lap_time(self, lap_time_str: Optional[str]) -> float:
        """Convert lap time string to seconds."""
        if not lap_time_str:
            return 90.0  # Default ~1:30
        
        try:
            # Handle pandas Timedelta string format
            td = pd.to_timedelta(lap_time_str)
            return td.total_seconds()
        except:
            return 90.0
