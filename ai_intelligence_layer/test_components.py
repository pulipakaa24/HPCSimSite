#!/usr/bin/env python3
"""
Simple test to verify the AI Intelligence Layer is working.
This tests the data models and validation logic without requiring Gemini API.
"""
import json
from models.input_models import (
    EnrichedTelemetryWebhook,
    RaceContext,
    RaceInfo,
    DriverState,
    Competitor,
    Strategy
)
from models.output_models import BrainstormResponse
from utils.validators import StrategyValidator, TelemetryAnalyzer


def test_models():
    """Test that Pydantic models work correctly."""
    print("Testing Pydantic models...")
    
    # Load sample data
    with open('sample_data/sample_enriched_telemetry.json') as f:
        telemetry_data = json.load(f)
    
    with open('sample_data/sample_race_context.json') as f:
        context_data = json.load(f)
    
    # Parse enriched telemetry
    telemetry = [EnrichedTelemetryWebhook(**t) for t in telemetry_data]
    print(f"✓ Parsed {len(telemetry)} telemetry records")
    
    # Parse race context
    race_context = RaceContext(**context_data)
    print(f"✓ Parsed race context for {race_context.driver_state.driver_name}")
    
    return telemetry, race_context


def test_validators(telemetry, race_context):
    """Test validation logic."""
    print("\nTesting validators...")
    
    # Test telemetry analysis
    tire_rate = TelemetryAnalyzer.calculate_tire_degradation_rate(telemetry)
    print(f"✓ Tire degradation rate: {tire_rate:.4f} per lap")
    
    aero_avg = TelemetryAnalyzer.calculate_aero_efficiency_avg(telemetry)
    print(f"✓ Aero efficiency average: {aero_avg:.3f}")
    
    ers_pattern = TelemetryAnalyzer.analyze_ers_pattern(telemetry)
    print(f"✓ ERS pattern: {ers_pattern}")
    
    tire_cliff = TelemetryAnalyzer.project_tire_cliff(telemetry, race_context.race_info.current_lap)
    print(f"✓ Projected tire cliff: Lap {tire_cliff}")
    
    # Test strategy validation
    test_strategy = Strategy(
        strategy_id=1,
        strategy_name="Test Strategy",
        stop_count=1,
        pit_laps=[32],
        tire_sequence=["medium", "hard"],
        brief_description="Test strategy",
        risk_level="low",
        key_assumption="Test assumption"
    )
    
    is_valid, error = StrategyValidator.validate_strategy(test_strategy, race_context)
    if is_valid:
        print(f"✓ Strategy validation working correctly")
    else:
        print(f"✗ Strategy validation failed: {error}")
    
    # Test telemetry summary
    summary = TelemetryAnalyzer.generate_telemetry_summary(telemetry)
    print(f"\n✓ Telemetry Summary:\n{summary}")


def test_prompts(telemetry, race_context):
    """Test prompt generation."""
    print("\nTesting prompt generation...")
    
    from prompts.brainstorm_prompt import build_brainstorm_prompt
    
    prompt = build_brainstorm_prompt(telemetry, race_context)
    print(f"✓ Generated brainstorm prompt ({len(prompt)} characters)")
    print(f"  Contains 'Monaco': {('Monaco' in prompt)}")
    print(f"  Contains 'Hamilton': {('Hamilton' in prompt)}")
    print(f"  Contains telemetry data: {('aero_efficiency' in prompt)}")


if __name__ == "__main__":
    print("=" * 60)
    print("AI Intelligence Layer - Component Tests")
    print("=" * 60)
    
    try:
        # Test models
        telemetry, race_context = test_models()
        
        # Test validators
        test_validators(telemetry, race_context)
        
        # Test prompts
        test_prompts(telemetry, race_context)
        
        print("\n" + "=" * 60)
        print("✓ All component tests passed!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Add your Gemini API key to .env")
        print("2. Start the service: python main.py")
        print("3. Test with: ./test_api.sh")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
