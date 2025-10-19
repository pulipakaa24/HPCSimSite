"""
Raspberry Pi Telemetry Stream Simulator

Replays downloaded FastF1 data as if it's coming from a live Raspberry Pi sensor.
Sends data to the HPC simulation layer via HTTP POST.

Usage:
    python simulate_pi_stream.py --data data/race_data/VER_telemetry.json --speed 1.0
"""

import argparse
import json
import time
import sys
from pathlib import Path
from typing import Dict, List, Any

import requests


def load_telemetry(filepath: Path) -> List[Dict[str, Any]]:
    """Load telemetry data from JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    print(f"✓ Loaded {len(data)} telemetry points from {filepath}")
    return data


def simulate_stream(
    telemetry: List[Dict[str, Any]],
    endpoint: str,
    speed: float = 1.0,
    start_lap: int = 1,
    end_lap: int = None
):
    """
    Simulate live telemetry streaming.
    
    Args:
        telemetry: List of telemetry points
        endpoint: HPC API endpoint URL
        speed: Playback speed multiplier (1.0 = real-time, 2.0 = 2x speed)
        start_lap: Starting lap number
        end_lap: Ending lap number (None = all laps)
    """
    # Filter by lap range
    filtered = [p for p in telemetry if p['lap'] >= start_lap]
    if end_lap:
        filtered = [p for p in filtered if p['lap'] <= end_lap]
    
    if not filtered:
        print("❌ No telemetry points in specified lap range")
        return
    
    print(f"\n🏁 Starting telemetry stream simulation")
    print(f"   Endpoint: {endpoint}")
    print(f"   Laps: {start_lap} → {end_lap or 'end'}")
    print(f"   Speed: {speed}x")
    print(f"   Points: {len(filtered)}")
    print(f"   Duration: {filtered[-1]['timestamp_ms'] / 1000.0:.1f}s\n")
    
    start_time = time.time()
    start_ts = filtered[0]['timestamp_ms']
    
    sent_count = 0
    error_count = 0
    
    try:
        for i, point in enumerate(filtered):
            # Calculate when this point should be sent
            point_offset = (point['timestamp_ms'] - start_ts) / 1000.0 / speed
            target_time = start_time + point_offset
            
            # Wait until the right time
            sleep_time = target_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            # Send telemetry point
            try:
                response = requests.post(
                    endpoint,
                    json=point,
                    timeout=2.0
                )
                
                if response.status_code == 200:
                    sent_count += 1
                    if sent_count % 100 == 0:
                        elapsed = time.time() - start_time
                        progress = (i + 1) / len(filtered) * 100
                        print(f"  📡 Lap {point['lap']}: {sent_count} points sent "
                              f"({progress:.1f}% complete, {elapsed:.1f}s elapsed)")
                else:
                    error_count += 1
                    print(f"  ⚠ HTTP {response.status_code}: {response.text[:50]}")
                    
            except requests.RequestException as e:
                error_count += 1
                if error_count % 10 == 0:
                    print(f"  ⚠ Connection error ({error_count} total): {e}")
        
        print(f"\n✅ Stream complete!")
        print(f"   Sent: {sent_count} points")
        print(f"   Errors: {error_count}")
        print(f"   Duration: {time.time() - start_time:.1f}s")
        
    except KeyboardInterrupt:
        print(f"\n⏸ Stream interrupted by user")
        print(f"   Sent: {sent_count}/{len(filtered)} points")


def main():
    parser = argparse.ArgumentParser(
        description="Simulate Raspberry Pi telemetry streaming"
    )
    parser.add_argument("--data", type=str, required=True, help="Path to telemetry JSON file")
    parser.add_argument("--endpoint", type=str, default="http://localhost:8000/telemetry",
                        help="HPC API endpoint")
    parser.add_argument("--speed", type=float, default=1.0, help="Playback speed (1.0 = real-time)")
    parser.add_argument("--start-lap", type=int, default=1, help="Starting lap number")
    parser.add_argument("--end-lap", type=int, default=None, help="Ending lap number")
    
    args = parser.parse_args()
    
    try:
        telemetry = load_telemetry(Path(args.data))
        simulate_stream(
            telemetry,
            args.endpoint,
            args.speed,
            args.start_lap,
            args.end_lap
        )
    except FileNotFoundError:
        print(f"❌ File not found: {args.data}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()