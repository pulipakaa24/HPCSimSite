#!/usr/bin/env python3
"""
Test script that:
1. POSTs raw telemetry to enrichment service (port 8000)
2. Enrichment service processes it and POSTs to AI layer webhook (port 9000)
3. AI layer generates strategies from the enriched data

This tests the REAL flow: Raw telemetry → Enrichment → AI
"""
import json
import time
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

ENRICHMENT_URL = "http://localhost:8000/enriched"  # POST enriched data directly
AI_BRAINSTORM_URL = "http://localhost:9000/api/strategy/brainstorm"

# Sample enriched telemetry matching EnrichedRecord model
SAMPLE_ENRICHED = {
    "lap": 27,
    "aero_efficiency": 0.85,
    "tire_degradation_index": 0.72,
    "ers_charge": 0.78,
    "fuel_optimization_score": 0.82,
    "driver_consistency": 0.88,
    "weather_impact": "low"
}

RACE_CONTEXT = {
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

def post_to_enrichment(enriched_data):
    """POST enriched data to enrichment service."""
    body = json.dumps(enriched_data).encode('utf-8')
    req = Request(
        ENRICHMENT_URL,
        data=body,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    try:
        with urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            print(f"✓ Posted to enrichment service - lap {enriched_data['lap']}")
            return True
    except HTTPError as e:
        print(f"✗ Enrichment service error {e.code}: {e.reason}")
        return False
    except URLError as e:
        print(f"✗ Cannot connect to enrichment service: {e.reason}")
        print("  Is it running on port 8000?")
        return False

def get_from_enrichment(limit=10):
    """GET enriched telemetry from enrichment service."""
    try:
        with urlopen(f"{ENRICHMENT_URL}?limit={limit}", timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"✓ Fetched {len(data)} records from enrichment service")
            return data
    except Exception as e:
        print(f"✗ Could not fetch from enrichment service: {e}")
        return []

def call_brainstorm(enriched_telemetry=None):
    """Call AI brainstorm endpoint."""
    payload = {"race_context": RACE_CONTEXT}
    if enriched_telemetry:
        payload["enriched_telemetry"] = enriched_telemetry
    
    body = json.dumps(payload).encode('utf-8')
    req = Request(
        AI_BRAINSTORM_URL,
        data=body,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    print("\nGenerating strategies...")
    try:
        with urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            
            # Save to file
            output_file = '/tmp/brainstorm_strategies.json'
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"✓ Generated {len(result.get('strategies', []))} strategies")
            print(f"  Saved to: {output_file}\n")
            
            for i, s in enumerate(result.get('strategies', []), 1):
                print(f"  {i}. {s.get('strategy_name')} ({s.get('stop_count')}-stop, {s.get('risk_level')} risk)")
                print(f"     Tires: {' → '.join(s.get('tire_sequence', []))}")
                print(f"     {s.get('brief_description')}")
                print()
            
            return True
    except HTTPError as e:
        print(f"✗ AI layer error {e.code}: {e.reason}")
        try:
            print(f"  Details: {e.read().decode('utf-8')}")
        except:
            pass
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    print("🏎️  Testing Real Enrichment Service Integration")
    print("=" * 60)
    
    # Step 1: Post enriched data to enrichment service
    print("\n1. Posting enriched telemetry to enrichment service...")
    for i in range(5):
        enriched = SAMPLE_ENRICHED.copy()
        enriched['lap'] = 27 + i
        enriched['tire_degradation_index'] = min(1.0, round(0.72 + i * 0.02, 3))
        enriched['weather_impact'] = ["low", "low", "medium", "medium", "high"][i % 5]
        
        if not post_to_enrichment(enriched):
            print("\n✗ Failed to post to enrichment service")
            print("  Make sure it's running: python3 scripts/serve.py")
            return 1
        time.sleep(0.3)
    
    print()
    time.sleep(1)
    
    # Step 2: Fetch from enrichment service
    print("2. Fetching enriched data from enrichment service...")
    enriched_data = get_from_enrichment(limit=10)
    
    if not enriched_data:
        print("\n✗ No data in enrichment service")
        return 1
    
    print(f"   Using {len(enriched_data)} most recent records\n")
    
    # Step 3: Call AI brainstorm with enriched data
    print("3. Calling AI layer with enriched telemetry from service...")
    if call_brainstorm(enriched_telemetry=enriched_data):
        print("\n✅ SUCCESS! Used real enrichment service data")
        print("=" * 60)
        return 0
    else:
        print("\n✗ Failed to generate strategies")
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
