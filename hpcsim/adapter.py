from __future__ import annotations

from typing import Dict, Any


def normalize_telemetry(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize lap-level telemetry payload from Pi stream to Enricher schema.

    Accepted aliases for lap-level data:
    - lap_number: lap, Lap, LapNumber, lap_number
    - total_laps: TotalLaps, total_laps
    - position: position, Position, Pos
    - gap_to_leader: gap_to_leader, GapToLeader, gap_leader
    - gap_to_ahead: gap_to_ahead, GapToAhead, gap_ahead
    - lap_time: lap_time, LapTime, Time
    - average_speed: average_speed, avg_speed, AvgSpeed
    - max_speed: max_speed, MaxSpeed, max
    - tire_compound: tire_compound, Compound, TyreCompound, Tire
    - tire_life_laps: tire_life_laps, TireAge, tire_age
    - track_temperature: track_temperature, TrackTemp, track_temp
    - rainfall: rainfall, Rainfall, Rain
    
    Returns normalized dict ready for enrichment layer.
    """
    aliases = {
        "lap_number": ["lap_number", "lap", "Lap", "LapNumber"],
        "total_laps": ["total_laps", "TotalLaps"],
        "position": ["position", "Position", "Pos"],
        "gap_to_leader": ["gap_to_leader", "GapToLeader", "gap_leader"],
        "gap_to_ahead": ["gap_to_ahead", "GapToAhead", "gap_ahead"],
        "lap_time": ["lap_time", "LapTime", "Time"],
        "average_speed": ["average_speed", "avg_speed", "AvgSpeed"],
        "max_speed": ["max_speed", "MaxSpeed", "max"],
        "tire_compound": ["tire_compound", "Compound", "TyreCompound", "Tire"],
        "tire_life_laps": ["tire_life_laps", "TireAge", "tire_age"],
        "track_temperature": ["track_temperature", "TrackTemp", "track_temp"],
        "rainfall": ["rainfall", "Rainfall", "Rain"],
    }

    out: Dict[str, Any] = {}

    def pick(key: str, default=None):
        """Pick first matching alias from payload."""
        for k in aliases.get(key, [key]):
            if k in payload and payload[k] is not None:
                return payload[k]
        return default

    # Extract and validate lap-level fields
    lap_number = pick("lap_number", 0)
    try:
        lap_number = int(lap_number)
    except (TypeError, ValueError):
        lap_number = 0

    total_laps = pick("total_laps", 51)
    try:
        total_laps = int(total_laps)
    except (TypeError, ValueError):
        total_laps = 51

    position = pick("position", 10)
    try:
        position = int(position)
    except (TypeError, ValueError):
        position = 10

    gap_to_leader = pick("gap_to_leader", 0.0)
    try:
        gap_to_leader = float(gap_to_leader)
    except (TypeError, ValueError):
        gap_to_leader = 0.0

    gap_to_ahead = pick("gap_to_ahead", 0.0)
    try:
        gap_to_ahead = float(gap_to_ahead)
    except (TypeError, ValueError):
        gap_to_ahead = 0.0

    lap_time = pick("lap_time", None)
    if lap_time:
        out["lap_time"] = str(lap_time)

    average_speed = pick("average_speed", 0.0)
    try:
        average_speed = float(average_speed)
    except (TypeError, ValueError):
        average_speed = 0.0

    max_speed = pick("max_speed", 0.0)
    try:
        max_speed = float(max_speed)
    except (TypeError, ValueError):
        max_speed = 0.0

    tire_compound = pick("tire_compound", "medium")
    if isinstance(tire_compound, str):
        tire_compound = tire_compound.upper()  # Keep uppercase for consistency
    else:
        tire_compound = "MEDIUM"

    tire_life_laps = pick("tire_life_laps", 0)
    try:
        tire_life_laps = int(tire_life_laps)
    except (TypeError, ValueError):
        tire_life_laps = 0

    track_temperature = pick("track_temperature", 25.0)
    try:
        track_temperature = float(track_temperature)
    except (TypeError, ValueError):
        track_temperature = 25.0

    rainfall = pick("rainfall", False)
    try:
        rainfall = bool(rainfall)
    except (TypeError, ValueError):
        rainfall = False

    # Build normalized output
    out.update({
        "lap_number": lap_number,
        "total_laps": total_laps,
        "position": position,
        "gap_to_leader": gap_to_leader,
        "gap_to_ahead": gap_to_ahead,
        "average_speed": average_speed,
        "max_speed": max_speed,
        "tire_compound": tire_compound,
        "tire_life_laps": tire_life_laps,
        "track_temperature": track_temperature,
        "rainfall": rainfall,
    })

    return out
