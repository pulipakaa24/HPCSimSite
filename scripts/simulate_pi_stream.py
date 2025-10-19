"""
Raspberry Pi Telemetry Stream Simulator

Reads the ALONSO_2023_MONZA_RACE CSV file row by row and simulates
live telemetry streaming from a Raspberry Pi sensor.
Sends data to the HPC simulation layer via HTTP POST at intervals
determined by the time differences between consecutive rows.

Usage:
    python simulate_pi_stream.py --data ALONSO_2023_MONZA_RACE --speed 1.0
"""

import argparse
import time
import sys
from pathlib import Path
from typing import Dict, Any
import pandas as pd
import requests


def load_telemetry_csv(filepath: Path) -> pd.DataFrame:
    """Load telemetry data from CSV file."""
    df = pd.read_csv(filepath, index_col=0)
    
    # Convert overall_time to timedelta if it's not already
    if df['overall_time'].dtype == 'object':
        df['overall_time'] = pd.to_timedelta(df['overall_time'])
    
    print(f"✓ Loaded {len(df)} telemetry points from {filepath}")
    print(f"   Laps: {df['lap_number'].min():.0f} → {df['lap_number'].max():.0f}")
    print(f"   Duration: {df['overall_time'].iloc[-1]}")
    
    return df


def row_to_json(row: pd.Series) -> Dict[str, Any]:
    """Convert a DataFrame row to a JSON-compatible dictionary."""
    data = {
        'lap_number': int(row['lap_number']) if pd.notna(row['lap_number']) else None,
        'total_laps': int(row['total_laps']) if pd.notna(row['total_laps']) else None,
        'speed': float(row['speed']) if pd.notna(row['speed']) else 0.0,
        'throttle': float(row['throttle']) if pd.notna(row['throttle']) else 0.0,
        'brake': bool(row['brake']),
        'tire_compound': str(row['tire_compound']) if pd.notna(row['tire_compound']) else 'UNKNOWN',
        'tire_life_laps': float(row['tire_life_laps']) if pd.notna(row['tire_life_laps']) else 0.0,
        'track_temperature': float(row['track_temperature']) if pd.notna(row['track_temperature']) else 0.0,
        'rainfall': bool(row['rainfall'])
    }
    return data


def simulate_stream(
    df: pd.DataFrame,
    endpoint: str,
    speed: float = 1.0,
    start_lap: int = 1,
    end_lap: int = None
):
    """
    Simulate live telemetry streaming based on actual time intervals in the data.
    
    Args:
        df: DataFrame with telemetry data
        endpoint: HPC API endpoint URL
        speed: Playback speed multiplier (1.0 = real-time, 2.0 = 2x speed)
        start_lap: Starting lap number
        end_lap: Ending lap number (None = all laps)
    """
    # Filter by lap range
    filtered_df = df[df['lap_number'] >= start_lap].copy()
    if end_lap:
        filtered_df = filtered_df[filtered_df['lap_number'] <= end_lap].copy()
    
    if len(filtered_df) == 0:
        print("❌ No telemetry points in specified lap range")
        return
    
    # Reset index for easier iteration
    filtered_df = filtered_df.reset_index(drop=True)
    
    print(f"\n🏁 Starting telemetry stream simulation")
    print(f"   Endpoint: {endpoint}")
    print(f"   Laps: {start_lap} → {end_lap or 'end'}")
    print(f"   Speed: {speed}x")
    print(f"   Points: {len(filtered_df)}")
    
    total_duration = (filtered_df['overall_time'].iloc[-1] - filtered_df['overall_time'].iloc[0]).total_seconds()
    print(f"   Duration: {total_duration:.1f}s (real-time) → {total_duration / speed:.1f}s (playback)\n")
    
    sent_count = 0
    error_count = 0
    current_lap = start_lap
    
    try:
        for i in range(len(filtered_df)):
            row = filtered_df.iloc[i]
            
            # Calculate sleep time based on time difference to next row
            if i < len(filtered_df) - 1:
                next_row = filtered_df.iloc[i + 1]
                time_diff = (next_row['overall_time'] - row['overall_time']).total_seconds()
                sleep_time = time_diff / speed
                
                # Ensure positive sleep time
                if sleep_time < 0:
                    sleep_time = 0
            else:
                sleep_time = 0
            
            # Convert row to JSON
            telemetry_point = row_to_json(row)
            
            # Send telemetry point
            try:
                response = requests.post(
                    endpoint,
                    json=telemetry_point,
                    timeout=2.0
                )
                
                if response.status_code == 200:
                    sent_count += 1
                    
                    # Print progress updates
                    if row['lap_number'] > current_lap:
                        current_lap = row['lap_number']
                        progress = (i + 1) / len(filtered_df) * 100
                        print(f"  📡 Lap {int(current_lap)}: {sent_count} points sent "
                              f"({progress:.1f}% complete)")
                    elif sent_count % 500 == 0:
                        progress = (i + 1) / len(filtered_df) * 100
                        print(f"  📡 Lap {int(row['lap_number'])}: {sent_count} points sent "
                              f"({progress:.1f}% complete)")
                else:
                    error_count += 1
                    print(f"  ⚠ HTTP {response.status_code}: {response.text[:50]}")
                    
            except requests.RequestException as e:
                error_count += 1
                if error_count % 10 == 0:
                    print(f"  ⚠ Connection error ({error_count} total): {str(e)[:50]}")
            
            # Sleep until next point should be sent
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        print(f"\n✅ Stream complete!")
        print(f"   Sent: {sent_count} points")
        print(f"   Errors: {error_count}")
        
    except KeyboardInterrupt:
        print(f"\n⏸ Stream interrupted by user")
        print(f"   Sent: {sent_count}/{len(filtered_df)} points")


def main():
    parser = argparse.ArgumentParser(
        description="Simulate Raspberry Pi telemetry streaming from CSV data"
    )
    parser.add_argument("--endpoint", type=str, default="http://localhost:8000/telemetry",
                        help="HPC API endpoint")
    parser.add_argument("--speed", type=float, default=1.0, 
                        help="Playback speed (1.0 = real-time, 10.0 = 10x speed)")
    parser.add_argument("--start-lap", type=int, default=1, help="Starting lap number")
    parser.add_argument("--end-lap", type=int, default=None, help="Ending lap number")
    
    args = parser.parse_args()
    
    try:
        # Hardcoded CSV file location in the same folder as this script
        script_dir = Path(__file__).parent
        data_path = script_dir / "ALONSO_2023_MONZA_RACE.csv"
        
        df = load_telemetry_csv(data_path)
        simulate_stream(
            df,
            args.endpoint,
            args.speed,
            args.start_lap,
            args.end_lap
        )
    except FileNotFoundError:
        print(f"❌ File not found: {data_path}")
        print(f"   Make sure ALONSO_2023_MONZA_RACE.csv is in the scripts/ folder")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()