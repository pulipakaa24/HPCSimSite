#!/usr/bin/env python3
"""
Quick test to verify the AI layer uses buffered telemetry from webhooks.
This tests the complete push model workflow:
1. Webhook receives telemetry -> stores in buffer
2. Brainstorm called without telemetry -> uses buffer automatically
"""
import json
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

BRAINSTORM_URL = "http://localhost:9000/api/strategy/brainstorm"

# Race context (no telemetry included - will use buffer!)
REQUEST_BODY = {
    "race_context": {
        "race_info": {
            "track_name": "Monaco",
            "current_lap": 27,
            "total_laps": 58,
            "weather_condition": "Dry",
            "track_temp_celsius": 42
        },
        "driver_state": {
            "driver_name": "Hamilton",
            "current_position": 4,
            "current_tire_compound": "medium",
            "tire_age_laps": 14,
            "fuel_remaining_percent": 47
        },
        "competitors": []
    }
}

def test_brainstorm_with_buffer():
    """Test brainstorm using buffered telemetry."""
    body = json.dumps(REQUEST_BODY).encode('utf-8')
    req = Request(
        BRAINSTORM_URL,
        data=body,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        method='POST'
    )
    
    print("Testing FAST brainstorm with buffered telemetry...")
    print("(Configured for 3 strategies - fast and diverse!)")
    print("(No telemetry in request - should use webhook buffer)\n")
    
    try:
        with urlopen(req, timeout=60) as resp:
            response_body = resp.read().decode('utf-8')
            result = json.loads(response_body)
            
            # Save to file
            output_file = '/tmp/brainstorm_strategies.json'
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            print("✓ Brainstorm succeeded!")
            print(f"  Generated {len(result.get('strategies', []))} strategies")
            print(f"  Saved to: {output_file}")
            
            if result.get('strategies'):
                print("\n  Strategies:")
                for i, strategy in enumerate(result['strategies'], 1):
                    print(f"    {i}. {strategy.get('strategy_name')} ({strategy.get('stop_count')}-stop, {strategy.get('risk_level')} risk)")
                    print(f"       Tires: {' → '.join(strategy.get('tire_sequence', []))}")
                    print(f"       Pits at: laps {strategy.get('pit_laps', [])}")
                    print(f"       {strategy.get('brief_description')}")
                    print()
            
            print("✓ SUCCESS: AI layer is using webhook buffer!")
            print(f"  Full JSON saved to {output_file}")
            print("  Check the service logs - should see:")
            print("  'Using N telemetry records from webhook buffer'")
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
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    import sys
    success = test_brainstorm_with_buffer()
    sys.exit(0 if success else 1)
