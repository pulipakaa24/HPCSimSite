#!/usr/bin/env python3
"""
Test script to simulate the enrichment service POSTing enriched telemetry
to the AI Intelligence Layer webhook endpoint.

This mimics the behavior when NEXT_STAGE_CALLBACK_URL is configured in the
enrichment service to push data to http://localhost:9000/api/ingest/enriched

Usage:
    python3 test_webhook_push.py           # Post sample telemetry
    python3 test_webhook_push.py --loop 5  # Post 5 times with delays
"""
import sys
import json
import time
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

WEBHOOK_URL = "http://localhost:9000/api/ingest/enriched"

# Sample enriched telemetry (lap 27 from Monaco)
# Matches EnrichedTelemetryWebhook model exactly
SAMPLE_TELEMETRY = {
    "lap": 27,
    "aero_efficiency": 0.85,
    "tire_degradation_index": 0.72,
    "ers_charge": 0.78,
    "fuel_optimization_score": 0.82,
    "driver_consistency": 0.88,
    "weather_impact": "low"
}

def post_telemetry(telemetry_data):
    """POST telemetry to the webhook endpoint."""
    body = json.dumps(telemetry_data).encode('utf-8')
    req = Request(
        WEBHOOK_URL,
        data=body,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        method='POST'
    )
    
    try:
        with urlopen(req, timeout=10) as resp:
            response_body = resp.read().decode('utf-8')
            result = json.loads(response_body)
            print(f"✓ Posted lap {telemetry_data['lap']}")
            print(f"  Status: {result.get('status')}")
            print(f"  Buffer size: {result.get('buffer_size')} records")
            return True
    except HTTPError as e:
        print(f"✗ HTTP Error {e.code}: {e.reason}")
        try:
            error_body = e.read().decode('utf-8')
            print(f"  Details: {error_body}")
        except:
            pass
        return False
    except URLError as e:
        print(f"✗ Connection Error: {e.reason}")
        print(f"  Is the AI service running on port 9000?")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Test webhook push to AI layer')
    parser.add_argument('--loop', type=int, default=1, help='Number of telemetry records to post')
    parser.add_argument('--delay', type=int, default=2, help='Delay between posts (seconds)')
    args = parser.parse_args()
    
    print(f"Testing webhook push to {WEBHOOK_URL}")
    print(f"Will post {args.loop} telemetry record(s)\n")
    
    success_count = 0
    for i in range(args.loop):
        # Increment lap number for each post
        telemetry = SAMPLE_TELEMETRY.copy()
        telemetry['lap'] = SAMPLE_TELEMETRY['lap'] + i
        
        # Slight variations in metrics (simulate degradation)
        telemetry['tire_degradation_index'] = min(1.0, round(SAMPLE_TELEMETRY['tire_degradation_index'] + (i * 0.02), 3))
        telemetry['aero_efficiency'] = max(0.0, round(SAMPLE_TELEMETRY['aero_efficiency'] - (i * 0.01), 3))
        telemetry['ers_charge'] = round(0.5 + (i % 5) * 0.1, 2)  # Varies between 0.5-0.9
        telemetry['weather_impact'] = ["low", "low", "medium", "medium", "high"][i % 5]
        
        if post_telemetry(telemetry):
            success_count += 1
        
        if i < args.loop - 1:
            time.sleep(args.delay)
    
    print(f"\n{'='*50}")
    print(f"Posted {success_count}/{args.loop} records successfully")
    
    if success_count > 0:
        print(f"\n✓ Telemetry is now in the AI layer's buffer")
        print(f"  Next: Call /api/strategy/brainstorm (without enriched_telemetry)")
        print(f"  The service will use buffered data automatically\n")
    
    return 0 if success_count == args.loop else 1

if __name__ == '__main__':
    sys.exit(main())
