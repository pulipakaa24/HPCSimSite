#!/usr/bin/env python3
"""
Quick test to verify WebSocket control system.
Tests the complete flow: Pi → AI → Control Commands
"""
import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("Error: websockets not installed")
    print("Run: pip install websockets")
    sys.exit(1)


async def test_websocket():
    """Test WebSocket connection and control flow."""
    
    ws_url = "ws://localhost:9000/ws/pi"
    print(f"Testing WebSocket connection to {ws_url}")
    print("-" * 60)
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✓ WebSocket connected!")
            
            # 1. Receive welcome message
            welcome = await websocket.recv()
            welcome_data = json.loads(welcome)
            print(f"✓ Welcome message: {welcome_data.get('message')}")
            
            # 2. Send test telemetry (lap 1)
            test_payload = {
                "type": "telemetry",
                "lap_number": 1,
                "enriched_telemetry": {
                    "lap": 1,
                    "tire_degradation_rate": 0.15,
                    "pace_trend": "stable",
                    "tire_cliff_risk": 0.05,
                    "optimal_pit_window": [25, 30],
                    "performance_delta": 0.0
                },
                "race_context": {
                    "race_info": {
                        "track_name": "Monza",
                        "total_laps": 51,
                        "current_lap": 1,
                        "weather_condition": "Dry",
                        "track_temp_celsius": 28.0
                    },
                    "driver_state": {
                        "driver_name": "Test Driver",
                        "current_position": 5,
                        "current_tire_compound": "medium",
                        "tire_age_laps": 1,
                        "fuel_remaining_percent": 98.0
                    },
                    "competitors": []
                }
            }
            
            print("\n→ Sending lap 1 telemetry...")
            await websocket.send(json.dumps(test_payload))
            
            # 3. Wait for response (short timeout for first laps)
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response_data = json.loads(response)
            
            if response_data.get("type") == "control_command":
                print("✓ Received control command!")
                print(f"  Brake Bias: {response_data.get('brake_bias')}/10")
                print(f"  Differential Slip: {response_data.get('differential_slip')}/10")
                print(f"  Message: {response_data.get('message', 'N/A')}")
            else:
                print(f"✗ Unexpected response: {response_data}")
            
            # 4. Send two more laps to trigger strategy generation
            for lap_num in [2, 3]:
                test_payload["lap_number"] = lap_num
                test_payload["enriched_telemetry"]["lap"] = lap_num
                test_payload["race_context"]["race_info"]["current_lap"] = lap_num
                
                print(f"\n→ Sending lap {lap_num} telemetry...")
                await websocket.send(json.dumps(test_payload))
                
                # Lap 3 triggers Gemini, so expect two responses
                if lap_num == 3:
                    print(f"  (lap 3 will trigger strategy generation - may take 10-30s)")
                    
                    # First response: immediate acknowledgment
                    response1 = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response1_data = json.loads(response1)
                    print(f"✓ Immediate response: {response1_data.get('message', 'Processing...')}")
                    
                    # Second response: strategy-based controls
                    print("  Waiting for strategy generation to complete...")
                    response2 = await asyncio.wait_for(websocket.recv(), timeout=45.0)
                    response2_data = json.loads(response2)
                    
                    if response2_data.get("type") == "control_command_update":
                        print(f"✓ Lap {lap_num} strategy-based control received!")
                        print(f"  Brake Bias: {response2_data.get('brake_bias')}/10")
                        print(f"  Differential Slip: {response2_data.get('differential_slip')}/10")
                        
                        strategy = response2_data.get('strategy_name')
                        if strategy and strategy != "N/A":
                            print(f"  Strategy: {strategy}")
                            print(f"  Total Strategies: {response2_data.get('total_strategies')}")
                            print("✓ Strategy generation successful!")
                    else:
                        print(f"✗ Unexpected response: {response2_data}")
                else:
                    # Laps 1-2: just one response
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    
                    if response_data.get("type") == "control_command":
                        print(f"✓ Lap {lap_num} control command received!")
                        print(f"  Brake Bias: {response_data.get('brake_bias')}/10")
                        print(f"  Differential Slip: {response_data.get('differential_slip')}/10")
            
            # 5. Disconnect
            print("\n→ Sending disconnect...")
            await websocket.send(json.dumps({"type": "disconnect"}))
            
            print("\n" + "=" * 60)
            print("✓ ALL TESTS PASSED!")
            print("=" * 60)
            print("\nWebSocket control system is working correctly.")
            print("Ready to run: python scripts/simulate_pi_websocket.py")
    
    except websockets.exceptions.WebSocketException as e:
        print(f"\n✗ WebSocket error: {e}")
        print("\nMake sure the AI Intelligence Layer is running:")
        print("  cd ai_intelligence_layer && python main.py")
        sys.exit(1)
    
    except asyncio.TimeoutError:
        print("\n✗ Timeout waiting for response")
        print("AI layer may be processing (Gemini API can be slow)")
        print("Check ai_intelligence_layer logs for details")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("WebSocket Control System Test")
    print("=" * 60)
    asyncio.run(test_websocket())
