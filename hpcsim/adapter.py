from __future__ import annotations

from typing import Dict, Any


def normalize_telemetry(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize Pi/FastF1-like telemetry payload to Enricher expected schema.

    Accepted aliases:
    - speed: Speed
    - throttle: Throttle
    - brake: Brake, Brakes
    - tire_compound: Compound, TyreCompound, Tire
    - fuel_level: Fuel, FuelRel, FuelLevel
    - ers: ERS, ERSCharge
    - track_temp: TrackTemp, track_temperature
    - rain_probability: RainProb, PrecipProb
    - lap: Lap, LapNumber, lap_number
    - total_laps: TotalLaps, total_laps
    - track_name: TrackName, track_name, Circuit
    - driver_name: DriverName, driver_name, Driver
    - current_position: Position, current_position
    - tire_life_laps: TireAge, tire_age, tire_life_laps
    - rainfall: Rainfall, rainfall, Rain
    
    Values are clamped and defaulted if missing.
    """
    aliases = {
        "lap": ["lap", "Lap", "LapNumber", "lap_number"],
        "speed": ["speed", "Speed"],
        "throttle": ["throttle", "Throttle"],
        "brake": ["brake", "Brake", "Brakes"],
        "tire_compound": ["tire_compound", "Compound", "TyreCompound", "Tire"],
        "fuel_level": ["fuel_level", "Fuel", "FuelRel", "FuelLevel"],
        "ers": ["ers", "ERS", "ERSCharge"],
        "track_temp": ["track_temp", "TrackTemp", "track_temperature"],
        "rain_probability": ["rain_probability", "RainProb", "PrecipProb"],
        "total_laps": ["total_laps", "TotalLaps"],
        "track_name": ["track_name", "TrackName", "Circuit"],
        "driver_name": ["driver_name", "DriverName", "Driver"],
        "current_position": ["current_position", "Position"],
        "tire_life_laps": ["tire_life_laps", "TireAge", "tire_age"],
        "rainfall": ["rainfall", "Rainfall", "Rain"],
    }

    out: Dict[str, Any] = {}

    def pick(key: str, default=None):
        for k in aliases.get(key, [key]):
            if k in payload and payload[k] is not None:
                return payload[k]
        return default

    def clamp01(x, default=0.0):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return default
        return max(0.0, min(1.0, v))

    # Map values with sensible defaults
    lap = pick("lap", 0)
    try:
        lap = int(lap)
    except (TypeError, ValueError):
        lap = 0

    speed = pick("speed", 0.0)
    try:
        speed = float(speed)
    except (TypeError, ValueError):
        speed = 0.0

    throttle = clamp01(pick("throttle", 0.0), 0.0)
    brake = clamp01(pick("brake", 0.0), 0.0)

    tire_compound = pick("tire_compound", "medium")
    if isinstance(tire_compound, str):
        tire_compound = tire_compound.lower()
    else:
        tire_compound = "medium"

    fuel_level = clamp01(pick("fuel_level", 0.5), 0.5)

    ers = pick("ers", None)
    if ers is not None:
        ers = clamp01(ers, None)

    track_temp = pick("track_temp", None)
    try:
        track_temp = float(track_temp) if track_temp is not None else None
    except (TypeError, ValueError):
        track_temp = None

    rain_prob = pick("rain_probability", None)
    try:
        rain_prob = clamp01(rain_prob, None) if rain_prob is not None else None
    except Exception:
        rain_prob = None

    out.update({
        "lap": lap,
        "speed": speed,
        "throttle": throttle,
        "brake": brake,
        "tire_compound": tire_compound,
        "fuel_level": fuel_level,
    })
    if ers is not None:
        out["ers"] = ers
    if track_temp is not None:
        out["track_temp"] = track_temp
    if rain_prob is not None:
        out["rain_probability"] = rain_prob
    
    # Add race context fields if present
    total_laps = pick("total_laps", None)
    if total_laps is not None:
        try:
            out["total_laps"] = int(total_laps)
        except (TypeError, ValueError):
            pass
    
    track_name = pick("track_name", None)
    if track_name:
        out["track_name"] = str(track_name)
    
    driver_name = pick("driver_name", None)
    if driver_name:
        out["driver_name"] = str(driver_name)
    
    current_position = pick("current_position", None)
    if current_position is not None:
        try:
            out["current_position"] = int(current_position)
        except (TypeError, ValueError):
            pass
    
    tire_life_laps = pick("tire_life_laps", None)
    if tire_life_laps is not None:
        try:
            out["tire_life_laps"] = int(tire_life_laps)
        except (TypeError, ValueError):
            pass
    
    rainfall = pick("rainfall", None)
    if rainfall is not None:
        out["rainfall"] = bool(rainfall)

    return out
