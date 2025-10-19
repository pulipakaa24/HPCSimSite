"""
Raspberry Pi Telemetry Stream Simulator - Lap-Level Data

Reads the ALONSO_2023_MONZA_LAPS.csv file lap by lap and simulates
live telemetry streaming from a Raspberry Pi sensor.
Sends data to the HPC simulation layer via HTTP POST at fixed 
1-minute intervals between laps.

Usage:
    python simulate_pi_stream.py
    python simulate_pi_stream.py --interval 30  # 30 seconds between laps
"""

import argparse
import time
import sys
from pathlib import Path
from typing import Dict, Any
import pandas as pd
import requests


def load_lap_csv(filepath: Path) -> pd.DataFrame:
    """Load lap-level telemetry data from CSV file."""
    df = pd.read_csv(filepath)
    
    # Convert lap_time to timedelta if it's not already
    if 'lap_time' in df.columns and df['lap_time'].dtype == 'object':
        df['lap_time'] = pd.to_timedelta(df['lap_time'])
    
    print(f"✓ Loaded {len(df)} laps from {filepath}")
    print(f"   Laps: {df['lap_number'].min():.0f} → {df['lap_number'].max():.0f}")
    
    return df


def lap_to_json(row: pd.Series) -> Dict[str, Any]:
    """Convert a lap DataFrame row to a JSON-compatible dictionary."""
    data = {
        'lap_number': int(row['lap_number']) if pd.notna(row['lap_number']) else None,
        'total_laps': int(row['total_laps']) if pd.notna(row['total_laps']) else None,
        'lap_time': str(row['lap_time']) if pd.notna(row['lap_time']) else None,
        'average_speed': float(row['average_speed']) if pd.notna(row['average_speed']) else 0.0,
        'max_speed': float(row['max_speed']) if pd.notna(row['max_speed']) else 0.0,
        'tire_compound': str(row['tire_compound']) if pd.notna(row['tire_compound']) else 'UNKNOWN',
        'tire_life_laps': int(row['tire_life_laps']) if pd.notna(row['tire_life_laps']) else 0,
        'track_temperature': float(row['track_temperature']) if pd.notna(row['track_temperature']) else 0.0,
        'rainfall': bool(row['rainfall'])
    }
    return data


def simulate_stream(
    df: pd.DataFrame,
    endpoint: str,
    interval: int = 60,
    start_lap: int = 1,
    end_lap: int = None
):
    """
    Simulate live telemetry streaming with fixed interval between laps.
    
    Args:
        df: DataFrame with lap-level telemetry data
        endpoint: HPC API endpoint URL
        interval: Fixed interval in seconds between laps (default: 60 seconds)
        start_lap: Starting lap number
        end_lap: Ending lap number (None = all laps)
    """
    # Filter by lap range
    filtered_df = df[df['lap_number'] >= start_lap].copy()
    if end_lap:
        filtered_df = filtered_df[filtered_df['lap_number'] <= end_lap].copy()
    
    if len(filtered_df) == 0:
        print("❌ No laps in specified lap range")
        return
    
    # Reset index for easier iteration
    filtered_df = filtered_df.reset_index(drop=True)
    
    print(f"\n🏁 Starting lap-level telemetry stream simulation")
    print(f"   Endpoint: {endpoint}")
    print(f"   Laps: {start_lap} → {end_lap or 'end'}")
    print(f"   Interval: {interval} seconds between laps")
    print(f"   Total laps: {len(filtered_df)}")
    print(f"   Est. duration: {len(filtered_df) * interval / 60:.1f} minutes\n")
    
    sent_count = 0
    error_count = 0
    
    try:
        for i in range(len(filtered_df)):
            row = filtered_df.iloc[i]
            lap_num = int(row['lap_number'])
            
            # Convert lap to JSON
            lap_data = lap_to_json(row)
            
            # Send lap data
            try:
                response = requests.post(
                    endpoint,
                    json=lap_data,
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    sent_count += 1
                    progress = (i + 1) / len(filtered_df) * 100
                    
                    # Print lap info
                    print(f"  📡 Lap {lap_num}/{int(row['total_laps'])}: "
                          f"Avg Speed: {row['average_speed']:.1f} km/h, "
                          f"Tire: {row['tire_compound']} (age: {int(row['tire_life_laps'])} laps) "
                          f"[{progress:.0f}%]")
                    
                    # Show response if it contains strategies
                    try:
                        response_data = response.json()
                        if 'strategies_generated' in response_data:
                            print(f"       ✓ Generated {response_data['strategies_generated']} strategies")
                    except:
                        pass
                else:
                    error_count += 1
                    print(f"  ⚠ Lap {lap_num}: HTTP {response.status_code}: {response.text[:100]}")
                    
            except requests.RequestException as e:
                error_count += 1
                print(f"  ⚠ Lap {lap_num}: Connection error: {str(e)[:100]}")
            
            # Sleep for fixed interval before next lap (except for last lap)
            if i < len(filtered_df) - 1:
                time.sleep(interval)
        
        print(f"\n✅ Stream complete!")
        print(f"   Sent: {sent_count} laps")
        print(f"   Errors: {error_count}")
        
    except KeyboardInterrupt:
        print(f"\n⏸ Stream interrupted by user")
        print(f"   Sent: {sent_count}/{len(filtered_df)} laps")


def main():
    parser = argparse.ArgumentParser(
        description="Simulate Raspberry Pi lap-level telemetry streaming"
    )
    parser.add_argument("--endpoint", type=str, default="http://localhost:8000/ingest/telemetry",
                        help="HPC API endpoint (default: http://localhost:8000/ingest/telemetry)")
    parser.add_argument("--interval", type=int, default=60, 
                        help="Fixed interval in seconds between laps (default: 60)")
    parser.add_argument("--start-lap", type=int, default=1, help="Starting lap number")
    parser.add_argument("--end-lap", type=int, default=None, help="Ending lap number")
    
    args = parser.parse_args()
    
    try:
        # Hardcoded CSV file location in the same folder as this script
        script_dir = Path(__file__).parent
        data_path = script_dir / "ALONSO_2023_MONZA_LAPS.csv"
        
        df = load_lap_csv(data_path)
        simulate_stream(
            df,
            args.endpoint,
            args.interval,
            args.start_lap,
            args.end_lap
        )
    except FileNotFoundError:
        print(f"❌ File not found: {data_path}")
        print(f"   Make sure ALONSO_2023_MONZA_LAPS.csv is in the scripts/ folder")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()