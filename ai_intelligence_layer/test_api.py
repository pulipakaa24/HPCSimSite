#!/usr/bin/env python3
"""
Simple Python test script for AI Intelligence Layer.
No external dependencies required (just standard library).
"""
import json
import time
import urllib.request
import urllib.error

BASE_URL = "http://localhost:9000"


def make_request(endpoint, method="GET", data=None):
    """Make an HTTP request."""
    url = f"{BASE_URL}{endpoint}"
    
    if data:
        data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={
            'Content-Type': 'application/json'
        })
        if method == "POST":
            req.get_method = lambda: "POST"
    else:
        req = urllib.request.Request(url)
    
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"✗ HTTP Error {e.code}: {error_body}")
        return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def test_health():
    """Test health endpoint."""
    print("1. Testing health endpoint...")
    result = make_request("/api/health")
    if result:
        print(f"   ✓ Status: {result['status']}")
        print(f"   ✓ Service: {result['service']}")
        print(f"   ✓ Demo mode: {result['demo_mode']}")
        return True
    return False


def test_brainstorm():
    """Test brainstorm endpoint."""
    print("\n2. Testing brainstorm endpoint...")
    print("   (This may take 15-30 seconds...)")
    
    # Load sample data
    with open('sample_data/sample_enriched_telemetry.json') as f:
        telemetry = json.load(f)
    
    with open('sample_data/sample_race_context.json') as f:
        context = json.load(f)
    
    # Make request
    start = time.time()
    result = make_request("/api/strategy/brainstorm", method="POST", data={
        "enriched_telemetry": telemetry,
        "race_context": context
    })
    elapsed = time.time() - start
    
    if result and 'strategies' in result:
        strategies = result['strategies']
        print(f"   ✓ Generated {len(strategies)} strategies in {elapsed:.1f}s")
        print("\n   Sample strategies:")
        for s in strategies[:3]:
            print(f"     {s['strategy_id']}. {s['strategy_name']}")
            print(f"        Stops: {s['stop_count']}, Risk: {s['risk_level']}")
        
        # Save for next test
        with open('/tmp/brainstorm_result.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        return result
    return None


def test_analyze(brainstorm_result):
    """Test analyze endpoint."""
    print("\n3. Testing analyze endpoint...")
    print("   (This may take 20-40 seconds...)")
    
    # Load sample data
    with open('sample_data/sample_enriched_telemetry.json') as f:
        telemetry = json.load(f)
    
    with open('sample_data/sample_race_context.json') as f:
        context = json.load(f)
    
    # Make request
    start = time.time()
    result = make_request("/api/strategy/analyze", method="POST", data={
        "enriched_telemetry": telemetry,
        "race_context": context,
        "strategies": brainstorm_result['strategies']
    })
    elapsed = time.time() - start
    
    if result and 'top_strategies' in result:
        print(f"   ✓ Analysis complete in {elapsed:.1f}s")
        print("\n   Top 3 strategies:")
        
        for s in result['top_strategies']:
            outcome = s['predicted_outcome']
            podium_prob = outcome['p1_probability'] + outcome['p2_probability'] + outcome['p3_probability']
            
            print(f"\n     {s['rank']}. {s['strategy_name']} ({s['classification']})")
            print(f"        Predicted: P{outcome['finish_position_most_likely']}")
            print(f"        P3 or better: {podium_prob}%")
            print(f"        Risk: {s['risk_assessment']['risk_level']}")
        
        # Show recommended strategy details
        rec = result['top_strategies'][0]
        print("\n" + "="*70)
        print("RECOMMENDED STRATEGY DETAILS:")
        print("="*70)
        print(f"\nEngineer Brief:")
        print(f"  {rec['engineer_brief']['summary']}")
        print(f"\nDriver Radio:")
        print(f"  \"{rec['driver_audio_script']}\"")
        print(f"\nECU Commands:")
        print(f"  Fuel: {rec['ecu_commands']['fuel_mode']}")
        print(f"  ERS: {rec['ecu_commands']['ers_strategy']}")
        print(f"  Engine: {rec['ecu_commands']['engine_mode']}")
        print("\n" + "="*70)
        
        # Save result
        with open('/tmp/analyze_result.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        return True
    return False


def main():
    """Run all tests."""
    print("="*70)
    print("AI Intelligence Layer - Test Suite")
    print("="*70)
    
    # Test health
    if not test_health():
        print("\n✗ Health check failed. Is the service running?")
        print("  Start with: python main.py")
        return
    
    # Test brainstorm
    brainstorm_result = test_brainstorm()
    if not brainstorm_result:
        print("\n✗ Brainstorm test failed")
        return
    
    # Test analyze
    if not test_analyze(brainstorm_result):
        print("\n✗ Analyze test failed")
        return
    
    print("\n" + "="*70)
    print("✓ ALL TESTS PASSED!")
    print("="*70)
    print("\nResults saved to:")
    print("  - /tmp/brainstorm_result.json")
    print("  - /tmp/analyze_result.json")


if __name__ == "__main__":
    main()
