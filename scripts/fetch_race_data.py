"""
FastF1 Data Fetcher for HPC F1 AI Strategy System

Downloads telemetry and race data from a specific F1 session to simulate
live telemetry streaming from a Raspberry Pi "racecar" to the HPC layer.

Usage:
    python fetch_race_data.py --year 2024 --race "Monaco" --driver VER --output data/
"""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Any
import warnings

import fastf1
import pandas as pd
import numpy as np

# Suppress FastF1 warnings
warnings.filterwarnings('ignore')

# Enable FastF1 cache for faster subsequent loads
CACHE_DIR = Path.home() / ".cache" / "fastf1"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))


def fetch_session_data(year: int, race: str, session_type: str = "R") -> fastf1.core.Session:
    """
    Load a FastF1 session.
    
    Args:
        year: Race year (e.g., 2024)
        race: Race name or round number (e.g., "Monaco" or 6)
        session_type: 'R' (Race), 'Q' (Quali), 'FP1', 'FP2', 'FP3', 'S' (Sprint)
    
    Returns:
        Loaded FastF1 session
    """
    print(f"Loading {year} {race} - {session_type}...")
    session = fastf1.get_session(year, race, session_type)
    session.load()
    print(f"✓ Session loaded: {session.event['EventName']} - {session.name}")
    return session


def extract_driver_telemetry(session: fastf1.core.Session, driver: str) -> pd.DataFrame:
    """
    Extract comprehensive telemetry for a specific driver.
    
    Args:
        session: Loaded FastF1 session
        driver: Driver abbreviation (e.g., 'VER', 'HAM', 'LEC')
    
    Returns:
        DataFrame with telemetry data
    """
    print(f"Extracting telemetry for driver {driver}...")
    
    driver_laps = session.laps.pick_driver(driver)
    if driver_laps.empty:
        raise ValueError(f"No laps found for driver {driver}")
    
    # Get telemetry for all laps
    telemetry_data = []
    
    for lap_num in driver_laps['LapNumber'].unique():
        lap = driver_laps[driver_laps['LapNumber'] == lap_num].iloc[0]
        
        try:
            telemetry = lap.get_telemetry()
            
            if telemetry.empty:
                continue
            
            # Add lap metadata to each telemetry point
            telemetry['LapNumber'] = lap_num
            telemetry['Compound'] = lap['Compound']
            telemetry['TyreLife'] = lap['TyreLife']
            telemetry['LapTime'] = lap['LapTime'].total_seconds() if pd.notna(lap['LapTime']) else None
            telemetry['IsPersonalBest'] = lap['IsPersonalBest']
            
            telemetry_data.append(telemetry)
            
        except Exception as e:
            print(f"  ⚠ Warning: Could not get telemetry for lap {lap_num}: {e}")
            continue
    
    if not telemetry_data:
        raise ValueError(f"No telemetry data extracted for {driver}")
    
    full_telemetry = pd.concat(telemetry_data, ignore_index=True)
    print(f"✓ Extracted {len(full_telemetry)} telemetry points across {len(driver_laps)} laps")
    
    return full_telemetry


def extract_race_context(session: fastf1.core.Session) -> Dict[str, Any]:
    """
    Extract race-level context data.
    
    Returns:
        Dictionary with weather, track, and competitor data
    """
    print("Extracting race context...")
    
    context = {
        "event": {
            "name": session.event['EventName'],
            "location": session.event['Location'],
            "country": session.event['Country'],
            "circuit": session.event.get('CircuitKey', 'unknown'),
        },
        "session": {
            "type": session.name,
            "date": str(session.date),
            "total_laps": int(session.total_laps) if hasattr(session, 'total_laps') else None,
        },
        "weather": {},
        "competitors": [],
    }
    
    # Weather data
    try:
        weather = session.weather_data
        if not weather.empty:
            # Average weather conditions
            context["weather"] = {
                "track_temp_avg": float(weather['TrackTemp'].mean()),
                "track_temp_min": float(weather['TrackTemp'].min()),
                "track_temp_max": float(weather['TrackTemp'].max()),
                "air_temp_avg": float(weather['AirTemp'].mean()),
                "humidity_avg": float(weather['Humidity'].mean()),
                "pressure_avg": float(weather['Pressure'].mean()),
                "rainfall": bool(weather['Rainfall'].any()),
            }
    except Exception as e:
        print(f"  ⚠ Warning: Could not extract weather data: {e}")
    
    # Competitor positions and pace
    try:
        results = session.results
        if not results.empty:
            for _, driver in results.iterrows():
                context["competitors"].append({
                    "driver": driver['Abbreviation'],
                    "team": driver['TeamName'],
                    "position": int(driver['Position']) if pd.notna(driver['Position']) else None,
                    "grid_position": int(driver['GridPosition']) if pd.notna(driver['GridPosition']) else None,
                    "status": driver.get('Status', 'Unknown'),
                })
    except Exception as e:
        print(f"  ⚠ Warning: Could not extract competitor data: {e}")
    
    print("✓ Race context extracted")
    return context


def prepare_telemetry_stream(telemetry: pd.DataFrame, sample_rate_hz: float = 10.0) -> List[Dict[str, Any]]:
    """
    Convert telemetry DataFrame to stream-ready format.
    
    Args:
        telemetry: Raw telemetry DataFrame
        sample_rate_hz: Target sampling rate (Hz) for simulation
    
    Returns:
        List of telemetry dictionaries ready for streaming
    """
    print(f"Preparing telemetry stream at {sample_rate_hz} Hz...")
    
    # Resample to target rate if needed
    telemetry = telemetry.copy()
    telemetry['Time'] = pd.to_timedelta(telemetry['Time'])
    telemetry = telemetry.sort_values('Time')
    
    # Convert to milliseconds for easier time tracking
    telemetry['TimeMs'] = (telemetry['Time'].dt.total_seconds() * 1000).astype(int)
    
    stream = []
    
    for _, row in telemetry.iterrows():
        point = {
            "timestamp_ms": int(row['TimeMs']),
            "lap": int(row['LapNumber']),
            "speed": float(row['Speed']) if pd.notna(row['Speed']) else 0.0,
            "throttle": float(row['Throttle']) / 100.0 if pd.notna(row['Throttle']) else 0.0,
            "brake": float(row['Brake']) if pd.notna(row['Brake']) else 0.0,
            "gear": int(row['nGear']) if pd.notna(row['nGear']) else 0,
            "rpm": int(row['RPM']) if pd.notna(row['RPM']) else 0,
            "drs": int(row['DRS']) if pd.notna(row['DRS']) else 0,
            "tire_compound": str(row['Compound']).lower() if pd.notna(row['Compound']) else "unknown",
            "tire_life": int(row['TyreLife']) if pd.notna(row['TyreLife']) else 0,
        }
        
        stream.append(point)
    
    print(f"✓ Prepared {len(stream)} telemetry points")
    return stream


def save_dataset(output_dir: Path, driver: str, telemetry_stream: List[Dict], context: Dict):
    """
    Save the dataset to disk for later replay.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save telemetry stream
    telemetry_file = output_dir / f"{driver}_telemetry.json"
    with open(telemetry_file, 'w') as f:
        json.dump(telemetry_stream, f, indent=2)
    print(f"✓ Saved telemetry: {telemetry_file}")
    
    # Save race context
    context_file = output_dir / f"{driver}_context.json"
    with open(context_file, 'w') as f:
        json.dump(context, f, indent=2)
    print(f"✓ Saved context: {context_file}")
    
    # Save summary metadata
    summary = {
        "driver": driver,
        "telemetry_points": len(telemetry_stream),
        "laps": len(set(p['lap'] for p in telemetry_stream)),
        "duration_seconds": telemetry_stream[-1]['timestamp_ms'] / 1000.0 if telemetry_stream else 0,
        "event": context['event']['name'],
        "session": context['session']['type'],
    }
    
    summary_file = output_dir / f"{driver}_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"✓ Saved summary: {summary_file}")
    
    print(f"\n📦 Dataset ready for simulation:")
    print(f"   Driver: {driver}")
    print(f"   Laps: {summary['laps']}")
    print(f"   Duration: {summary['duration_seconds']:.1f}s")
    print(f"   Points: {summary['telemetry_points']}")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch FastF1 data for HPC F1 AI Strategy System"
    )
    parser.add_argument("--year", type=int, default=2024, help="Race year")
    parser.add_argument("--race", type=str, default="Monaco", help="Race name or round number")
    parser.add_argument("--driver", type=str, default="VER", help="Driver abbreviation (VER, HAM, LEC, etc.)")
    parser.add_argument("--session", type=str, default="R", help="Session type (R, Q, FP1, etc.)")
    parser.add_argument("--output", type=str, default="data/race_data", help="Output directory")
    parser.add_argument("--sample-rate", type=float, default=10.0, help="Target sampling rate (Hz)")
    
    args = parser.parse_args()
    
    try:
        # Fetch session
        session = fetch_session_data(args.year, args.race, args.session)
        
        # Extract driver telemetry
        telemetry = extract_driver_telemetry(session, args.driver)
        
        # Extract race context
        context = extract_race_context(session)
        
        # Prepare telemetry stream
        stream = prepare_telemetry_stream(telemetry, args.sample_rate)
        
        # Save dataset
        save_dataset(Path(args.output), args.driver, stream, context)
        
        print("\n✅ Data fetch complete! Ready for Pi simulation.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()