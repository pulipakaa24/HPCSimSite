#!/usr/bin/env python3
"""
Validation script to demonstrate the complete integration.
This shows that all pieces fit together correctly.
"""

from hpcsim.enrichment import Enricher
from hpcsim.adapter import normalize_telemetry
import json


def validate_task_1():
    """Validate Task 1: AI layer receives enriched_telemetry + race_context"""
    print("=" * 70)
    print("TASK 1 VALIDATION: AI Layer Input Structure")
    print("=" * 70)
    
    enricher = Enricher()
    
    # Simulate telemetry from Pi
    raw_telemetry = {
        'lap_number': 15,
        'total_laps': 51,
        'speed': 285.5,
        'throttle': 88.0,
        'brake': False,
        'tire_compound': 'MEDIUM',
        'tire_life_laps': 12,
        'track_temperature': 42.5,
        'rainfall': False,
        'track_name': 'Monza',
        'driver_name': 'Alonso',
        'current_position': 5,
        'fuel_level': 0.65,
    }
    
    # Process through pipeline
    normalized = normalize_telemetry(raw_telemetry)
    result = enricher.enrich_with_context(normalized)
    
    print("\n✅ Input to AI Layer (/api/ingest/enriched):")
    print(json.dumps(result, indent=2))
    
    # Validate structure
    assert 'enriched_telemetry' in result, "Missing enriched_telemetry"
    assert 'race_context' in result, "Missing race_context"
    
    enriched = result['enriched_telemetry']
    context = result['race_context']
    
    # Validate enriched telemetry fields
    required_enriched = ['lap', 'aero_efficiency', 'tire_degradation_index', 
                        'ers_charge', 'fuel_optimization_score', 
                        'driver_consistency', 'weather_impact']
    for field in required_enriched:
        assert field in enriched, f"Missing enriched field: {field}"
    
    # Validate race context structure
    assert 'race_info' in context, "Missing race_info"
    assert 'driver_state' in context, "Missing driver_state"
    assert 'competitors' in context, "Missing competitors"
    
    # Validate race_info
    race_info = context['race_info']
    assert race_info['track_name'] == 'Monza'
    assert race_info['total_laps'] == 51
    assert race_info['current_lap'] == 15
    
    # Validate driver_state
    driver_state = context['driver_state']
    assert driver_state['driver_name'] == 'Alonso'
    assert driver_state['current_position'] == 5
    assert driver_state['current_tire_compound'] in ['soft', 'medium', 'hard', 'intermediate', 'wet']
    
    print("\n✅ TASK 1 VALIDATION PASSED")
    print("   - enriched_telemetry: ✅")
    print("   - race_context.race_info: ✅")
    print("   - race_context.driver_state: ✅")
    print("   - race_context.competitors: ✅")
    
    return True


def validate_task_2():
    """Validate Task 2: Enrichment outputs complete race context"""
    print("\n" + "=" * 70)
    print("TASK 2 VALIDATION: Enrichment Output Structure")
    print("=" * 70)
    
    enricher = Enricher()
    
    # Test with minimal input
    minimal_input = {
        'lap': 10,
        'speed': 280.0,
        'throttle': 0.85,
        'brake': 0.05,
        'tire_compound': 'medium',
        'fuel_level': 0.7,
    }
    
    # Old method (legacy) - should still work
    legacy_result = enricher.enrich(minimal_input)
    print("\n📊 Legacy Output (enrich method):")
    print(json.dumps(legacy_result, indent=2))
    assert 'lap' in legacy_result
    assert 'aero_efficiency' in legacy_result
    assert 'race_context' not in legacy_result  # Legacy doesn't include context
    print("✅ Legacy method still works (backward compatible)")
    
    # New method - with context
    full_input = {
        'lap': 10,
        'speed': 280.0,
        'throttle': 0.85,
        'brake': 0.05,
        'tire_compound': 'medium',
        'fuel_level': 0.7,
        'track_temp': 42.5,
        'total_laps': 51,
        'track_name': 'Monza',
        'driver_name': 'Alonso',
        'current_position': 5,
        'tire_life_laps': 8,
        'rainfall': False,
    }
    
    new_result = enricher.enrich_with_context(full_input)
    print("\n📊 New Output (enrich_with_context method):")
    print(json.dumps(new_result, indent=2))
    
    # Validate new output
    assert 'enriched_telemetry' in new_result
    assert 'race_context' in new_result
    
    enriched = new_result['enriched_telemetry']
    context = new_result['race_context']
    
    # Check all 7 enriched fields
    assert enriched['lap'] == 10
    assert 0.0 <= enriched['aero_efficiency'] <= 1.0
    assert 0.0 <= enriched['tire_degradation_index'] <= 1.0
    assert 0.0 <= enriched['ers_charge'] <= 1.0
    assert 0.0 <= enriched['fuel_optimization_score'] <= 1.0
    assert 0.0 <= enriched['driver_consistency'] <= 1.0
    assert enriched['weather_impact'] in ['low', 'medium', 'high']
    
    # Check race context
    assert context['race_info']['track_name'] == 'Monza'
    assert context['race_info']['total_laps'] == 51
    assert context['race_info']['current_lap'] == 10
    assert context['driver_state']['driver_name'] == 'Alonso'
    assert context['driver_state']['current_position'] == 5
    assert context['driver_state']['fuel_remaining_percent'] == 70.0  # 0.7 * 100
    assert len(context['competitors']) > 0
    
    print("\n✅ TASK 2 VALIDATION PASSED")
    print("   - Legacy enrich() still works: ✅")
    print("   - New enrich_with_context() works: ✅")
    print("   - All 7 enriched fields present: ✅")
    print("   - race_info complete: ✅")
    print("   - driver_state complete: ✅")
    print("   - competitors generated: ✅")
    
    return True


def validate_data_transformations():
    """Validate data transformations and conversions"""
    print("\n" + "=" * 70)
    print("DATA TRANSFORMATIONS VALIDATION")
    print("=" * 70)
    
    enricher = Enricher()
    
    # Test tire compound normalization
    test_cases = [
        ('SOFT', 'soft'),
        ('Medium', 'medium'),
        ('HARD', 'hard'),
        ('inter', 'intermediate'),
        ('INTERMEDIATE', 'intermediate'),
        ('wet', 'wet'),
    ]
    
    print("\n🔧 Tire Compound Normalization:")
    for input_tire, expected_output in test_cases:
        result = enricher.enrich_with_context({
            'lap': 1,
            'speed': 280.0,
            'throttle': 0.85,
            'brake': 0.05,
            'tire_compound': input_tire,
            'fuel_level': 0.7,
        })
        actual = result['race_context']['driver_state']['current_tire_compound']
        assert actual == expected_output, f"Expected {expected_output}, got {actual}"
        print(f"   {input_tire} → {actual} ✅")
    
    # Test fuel conversion
    print("\n🔧 Fuel Level Conversion (0-1 → 0-100%):")
    fuel_tests = [0.0, 0.25, 0.5, 0.75, 1.0]
    for fuel_in in fuel_tests:
        result = enricher.enrich_with_context({
            'lap': 1,
            'speed': 280.0,
            'throttle': 0.85,
            'brake': 0.05,
            'tire_compound': 'medium',
            'fuel_level': fuel_in,
        })
        fuel_out = result['race_context']['driver_state']['fuel_remaining_percent']
        expected = fuel_in * 100.0
        assert fuel_out == expected, f"Expected {expected}, got {fuel_out}"
        print(f"   {fuel_in:.2f} → {fuel_out:.1f}% ✅")
    
    print("\n✅ DATA TRANSFORMATIONS VALIDATION PASSED")
    return True


def main():
    """Run all validations"""
    print("\n" + "🎯" * 35)
    print("COMPLETE INTEGRATION VALIDATION")
    print("🎯" * 35)
    
    try:
        # Task 1: AI layer receives enriched_telemetry + race_context
        validate_task_1()
        
        # Task 2: Enrichment outputs complete race context
        validate_task_2()
        
        # Data transformations
        validate_data_transformations()
        
        print("\n" + "=" * 70)
        print("🎉 ALL VALIDATIONS PASSED! 🎉")
        print("=" * 70)
        print("\n✅ Task 1: AI layer webhook receives enriched_telemetry + race_context")
        print("✅ Task 2: Enrichment outputs all expected fields")
        print("✅ All data transformations working correctly")
        print("✅ All pieces fit together properly")
        print("\n" + "=" * 70)
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ VALIDATION FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
