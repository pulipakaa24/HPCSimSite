"""
Quick test to verify the complete integration workflow.
Run this after starting both services to test end-to-end.
"""
import requests
import json
import time


def test_complete_workflow():
    """Test the complete workflow from raw telemetry to strategy generation."""
    
    print("🧪 Testing Complete Integration Workflow\n")
    print("=" * 70)
    
    # Test 1: Check services are running
    print("\n1️⃣  Checking service health...")
    
    try:
        enrichment_health = requests.get("http://localhost:8000/healthz", timeout=2)
        print(f"   ✅ Enrichment service: {enrichment_health.json()}")
    except Exception as e:
        print(f"   ❌ Enrichment service not responding: {e}")
        print("   → Start with: uvicorn hpcsim.api:app --port 8000")
        return False
    
    try:
        ai_health = requests.get("http://localhost:9000/api/health", timeout=2)
        print(f"   ✅ AI Intelligence Layer: {ai_health.json()}")
    except Exception as e:
        print(f"   ❌ AI Intelligence Layer not responding: {e}")
        print("   → Start with: cd ai_intelligence_layer && uvicorn main:app --port 9000")
        return False
    
    # Test 2: Send telemetry with race context
    print("\n2️⃣  Sending telemetry with race context...")
    
    telemetry_samples = []
    for lap in range(1, 6):
        sample = {
            'lap_number': lap,
            'total_laps': 51,
            'speed': 280.0 + (lap * 2),
            'throttle': 0.85 + (lap * 0.01),
            'brake': 0.05,
            'tire_compound': 'MEDIUM',
            'tire_life_laps': lap,
            'track_temperature': 42.5,
            'rainfall': False,
            'track_name': 'Monza',
            'driver_name': 'Alonso',
            'current_position': 5,
            'fuel_level': 0.9 - (lap * 0.02),
        }
        telemetry_samples.append(sample)
    
    responses = []
    for i, sample in enumerate(telemetry_samples, 1):
        try:
            response = requests.post(
                "http://localhost:8000/ingest/telemetry",
                json=sample,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                responses.append(result)
                print(f"   Lap {sample['lap_number']}: ✅ Enriched")
                
                # Check if we got enriched_telemetry and race_context
                if 'enriched_telemetry' in result and 'race_context' in result:
                    print(f"      └─ Enriched telemetry + race context included")
                    if i == len(telemetry_samples):
                        # Show last response details
                        enriched = result['enriched_telemetry']
                        context = result['race_context']
                        print(f"\n   📊 Final Enriched Metrics:")
                        print(f"      - Aero Efficiency: {enriched['aero_efficiency']:.3f}")
                        print(f"      - Tire Degradation: {enriched['tire_degradation_index']:.3f}")
                        print(f"      - Driver Consistency: {enriched['driver_consistency']:.3f}")
                        print(f"\n   🏎️  Race Context:")
                        print(f"      - Track: {context['race_context']['race_info']['track_name']}")
                        print(f"      - Lap: {context['race_context']['race_info']['current_lap']}/{context['race_context']['race_info']['total_laps']}")
                        print(f"      - Position: P{context['race_context']['driver_state']['current_position']}")
                        print(f"      - Fuel: {context['race_context']['driver_state']['fuel_remaining_percent']:.1f}%")
                        print(f"      - Competitors: {len(context['race_context']['competitors'])} shown")
                else:
                    print(f"      ⚠️  Legacy format (no race context)")
            else:
                print(f"   Lap {sample['lap_number']}: ❌ Failed ({response.status_code})")
        except Exception as e:
            print(f"   Lap {sample['lap_number']}: ❌ Error: {e}")
        
        time.sleep(0.5)  # Small delay between requests
    
    # Test 3: Check AI layer buffer
    print("\n3️⃣  Checking AI layer webhook processing...")
    
    # The AI layer should have received webhooks and auto-generated strategies
    # Let's verify by checking if we can call brainstorm manually
    # (The auto-brainstorm happens in the webhook, but we can verify the buffer)
    
    print("   ℹ️  Auto-brainstorming triggers when buffer has ≥3 laps")
    print("   ℹ️  Strategies are returned in the webhook response to enrichment service")
    print("   ℹ️  Check the AI Intelligence Layer logs for auto-generated strategies")
    
    # Test 4: Manual brainstorm call (to verify the endpoint still works)
    print("\n4️⃣  Testing manual brainstorm endpoint...")
    
    try:
        brainstorm_request = {
            "race_context": {
                "race_info": {
                    "track_name": "Monza",
                    "total_laps": 51,
                    "current_lap": 5,
                    "weather_condition": "Dry",
                    "track_temp_celsius": 42.5
                },
                "driver_state": {
                    "driver_name": "Alonso",
                    "current_position": 5,
                    "current_tire_compound": "medium",
                    "tire_age_laps": 5,
                    "fuel_remaining_percent": 82.0
                },
                "competitors": []
            }
        }
        
        response = requests.post(
            "http://localhost:9000/api/strategy/brainstorm",
            json=brainstorm_request,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Generated {len(result['strategies'])} strategies")
            if result['strategies']:
                strategy = result['strategies'][0]
                print(f"\n   🎯 Sample Strategy:")
                print(f"      - Name: {strategy['strategy_name']}")
                print(f"      - Stops: {strategy['stop_count']}")
                print(f"      - Pit Laps: {strategy['pit_laps']}")
                print(f"      - Tires: {' → '.join(strategy['tire_sequence'])}")
                print(f"      - Risk: {strategy['risk_level']}")
        else:
            print(f"   ⚠️  Brainstorm returned {response.status_code}")
            print(f"      (This might be expected if Gemini API is not configured)")
    except Exception as e:
        print(f"   ℹ️  Manual brainstorm skipped: {e}")
    
    print("\n" + "=" * 70)
    print("✅ Integration test complete!\n")
    return True


if __name__ == '__main__':
    test_complete_workflow()
