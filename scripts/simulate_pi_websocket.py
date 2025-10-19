#!/usr/bin/env python3
"""
WebSocket-based Raspberry Pi Telemetry Simulator.

Connects to AI Intelligence Layer via WebSocket and:
1. Streams lap telemetry to AI layer
2. Receives control commands (brake_bias, differential_slip) from AI layer
3. Applies control adjustments in real-time

Usage:
    python simulate_pi_websocket.py --interval 5 --ws-url ws://localhost:9000/ws/pi
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import sys

try:
    import pandas as pd
    import websockets
    from websockets.client import WebSocketClientProtocol
except ImportError:
    print("Error: Required packages not installed.")
    print("Run: pip install pandas websockets")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PiSimulator:
    """WebSocket-based Pi simulator with control feedback."""
    
    def __init__(self, csv_path: Path, ws_url: str, interval: float = 60.0, enrichment_url: str = "http://localhost:8000"):
        self.csv_path = csv_path
        self.ws_url = ws_url
        self.enrichment_url = enrichment_url
        self.interval = interval
        self.df: Optional[pd.DataFrame] = None
        self.current_controls = {
            "brake_bias": 5,
            "differential_slip": 5
        }
    
    def load_lap_csv(self) -> pd.DataFrame:
        """Load lap-level CSV data."""
        logger.info(f"Loading CSV from {self.csv_path}")
        df = pd.read_csv(self.csv_path)
        logger.info(f"Loaded {len(df)} laps")
        return df
    
    def lap_to_raw_payload(self, row: pd.Series) -> Dict[str, Any]:
        """
        Convert CSV row to raw lap telemetry (for enrichment service).
        This is what the real Pi would send.
        """
        return {
            "lap_number": int(row["lap_number"]),
            "total_laps": int(row["total_laps"]),
            "lap_time": str(row["lap_time"]),
            "average_speed": float(row["average_speed"]),
            "max_speed": float(row["max_speed"]),
            "tire_compound": str(row["tire_compound"]),
            "tire_life_laps": int(row["tire_life_laps"]),
            "track_temperature": float(row["track_temperature"]),
            "rainfall": bool(row.get("rainfall", False))
        }
    
    async def enrich_telemetry(self, raw_telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send raw telemetry to enrichment service and get back enriched data.
        This simulates the Pi → Enrichment → AI flow.
        """
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.enrichment_url}/ingest/telemetry",
                    json=raw_telemetry,
                    timeout=aiohttp.ClientTimeout(total=5.0)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"  ✓ Enrichment service processed lap {raw_telemetry['lap_number']}")
                        return result
                    else:
                        logger.error(f"  ✗ Enrichment service error: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"  ✗ Failed to connect to enrichment service: {e}")
            logger.error(f"  Make sure enrichment service is running: python scripts/serve.py")
            return None
    
    def lap_to_enriched_payload(self, row: pd.Series) -> Dict[str, Any]:
        """
        Convert CSV row to enriched telemetry payload.
        Simulates the enrichment layer output.
        """
        # Basic enrichment simulation (would normally come from enrichment service)
        lap_number = int(row["lap_number"])
        tire_age = int(row["tire_life_laps"])
        
        # Simple tire degradation simulation
        tire_deg_rate = min(1.0, 0.02 * tire_age)
        tire_cliff_risk = max(0.0, min(1.0, (tire_age - 20) / 10.0))
        
        # Pace trend (simplified)
        pace_trend = "stable"
        if tire_age > 25:
            pace_trend = "declining"
        elif tire_age < 5:
            pace_trend = "improving"
        
        # Optimal pit window
        if tire_age > 20:
            pit_window = [lap_number + 1, lap_number + 3]
        else:
            pit_window = [lap_number + 10, lap_number + 15]
        
        # Performance delta (random for simulation)
        import random
        performance_delta = random.uniform(-1.5, 1.0)
        
        enriched_telemetry = {
            "lap": lap_number,
            "tire_degradation_rate": round(tire_deg_rate, 3),
            "pace_trend": pace_trend,
            "tire_cliff_risk": round(tire_cliff_risk, 3),
            "optimal_pit_window": pit_window,
            "performance_delta": round(performance_delta, 2)
        }
        
        race_context = {
            "race_info": {
                "track_name": "Monza",
                "total_laps": int(row["total_laps"]),
                "current_lap": lap_number,
                "weather_condition": "Wet" if row.get("rainfall", False) else "Dry",
                "track_temp_celsius": float(row["track_temperature"])
            },
            "driver_state": {
                "driver_name": "Alonso",
                "current_position": 5,
                "current_tire_compound": str(row["tire_compound"]).lower(),
                "tire_age_laps": tire_age,
                "fuel_remaining_percent": max(0.0, 100.0 * (1.0 - (lap_number / int(row["total_laps"]))))
            },
            "competitors": []
        }
        
        return {
            "type": "telemetry",
            "lap_number": lap_number,
            "enriched_telemetry": enriched_telemetry,
            "race_context": race_context
        }
    
    async def stream_telemetry(self):
        """Main WebSocket streaming loop."""
        self.df = self.load_lap_csv()
        
        # Reset enrichment service state for fresh session
        logger.info(f"Resetting enrichment service state...")
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.enrichment_url}/reset",
                    timeout=aiohttp.ClientTimeout(total=5.0)
                ) as response:
                    if response.status == 200:
                        logger.info("✓ Enrichment service reset successfully")
                    else:
                        logger.warning(f"⚠ Enrichment reset returned status {response.status}")
        except Exception as e:
            logger.warning(f"⚠ Could not reset enrichment service: {e}")
            logger.warning("  Continuing anyway (enricher may have stale state)")
        
        logger.info(f"Connecting to WebSocket: {self.ws_url}")
        
        try:
            async with websockets.connect(self.ws_url) as websocket:
                logger.info("WebSocket connected!")
                
                # Wait for welcome message
                welcome = await websocket.recv()
                logger.info(f"Received: {welcome}")
                
                # Stream each lap
                for idx, row in self.df.iterrows():
                    lap_number = int(row["lap_number"])
                    
                    logger.info(f"\n{'='*60}")
                    logger.info(f"Lap {lap_number}/{int(row['total_laps'])}")
                    logger.info(f"{'='*60}")
                    
                    # Build raw telemetry payload (what real Pi would send)
                    raw_telemetry = self.lap_to_raw_payload(row)
                    logger.info(f"[RAW] Lap {lap_number} telemetry prepared")
                    
                    # Send to enrichment service for processing
                    enriched_data = await self.enrich_telemetry(raw_telemetry)
                    
                    if not enriched_data:
                        logger.error("Failed to get enrichment, skipping lap")
                        await asyncio.sleep(self.interval)
                        continue
                    
                    # Extract enriched telemetry and race context from enrichment service
                    enriched_telemetry = enriched_data.get("enriched_telemetry")
                    race_context = enriched_data.get("race_context")
                    
                    if not enriched_telemetry or not race_context:
                        logger.error("Invalid enrichment response, skipping lap")
                        await asyncio.sleep(self.interval)
                        continue
                    
                    # Build WebSocket payload for AI layer
                    ws_payload = {
                        "type": "telemetry",
                        "lap_number": lap_number,
                        "enriched_telemetry": enriched_telemetry,
                        "race_context": race_context
                    }
                    
                    # Send enriched telemetry to AI layer via WebSocket
                    await websocket.send(json.dumps(ws_payload))
                    logger.info(f"[SENT] Lap {lap_number} enriched telemetry to AI layer")
                    
                    # Wait for control command response(s)
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response)
                        
                        if response_data.get("type") == "control_command":
                            brake_bias = response_data.get("brake_bias", 5)
                            diff_slip = response_data.get("differential_slip", 5)
                            strategy_name = response_data.get("strategy_name", "N/A")
                            message = response_data.get("message")
                            
                            self.current_controls["brake_bias"] = brake_bias
                            self.current_controls["differential_slip"] = diff_slip
                            
                            logger.info(f"[RECEIVED] Control Command:")
                            logger.info(f"  ├─ Brake Bias: {brake_bias}/10")
                            logger.info(f"  ├─ Differential Slip: {diff_slip}/10")
                            if strategy_name != "N/A":
                                logger.info(f"  └─ Strategy: {strategy_name}")
                            if message:
                                logger.info(f"  └─ {message}")
                            
                            # Apply controls (in real Pi, this would adjust hardware)
                            self.apply_controls(brake_bias, diff_slip)
                            
                            # If message indicates processing, wait for update
                            if message and "Processing" in message:
                                logger.info("  AI is generating strategies, waiting for update...")
                                try:
                                    update = await asyncio.wait_for(websocket.recv(), timeout=45.0)
                                    update_data = json.loads(update)
                                    
                                    if update_data.get("type") == "control_command_update":
                                        brake_bias = update_data.get("brake_bias", 5)
                                        diff_slip = update_data.get("differential_slip", 5)
                                        strategy_name = update_data.get("strategy_name", "N/A")
                                        
                                        self.current_controls["brake_bias"] = brake_bias
                                        self.current_controls["differential_slip"] = diff_slip
                                        
                                        logger.info(f"[UPDATED] Strategy-Based Control:")
                                        logger.info(f"  ├─ Brake Bias: {brake_bias}/10")
                                        logger.info(f"  ├─ Differential Slip: {diff_slip}/10")
                                        logger.info(f"  └─ Strategy: {strategy_name}")
                                        
                                        self.apply_controls(brake_bias, diff_slip)
                                except asyncio.TimeoutError:
                                    logger.warning("[TIMEOUT] Strategy generation took too long")
                        
                        elif response_data.get("type") == "error":
                            logger.error(f"[ERROR] {response_data.get('message')}")
                    
                    except asyncio.TimeoutError:
                        logger.warning("[TIMEOUT] No control command received within 5s")
                    
                    # Wait before next lap
                    logger.info(f"Waiting {self.interval}s before next lap...")
                    await asyncio.sleep(self.interval)
                
                # All laps complete
                logger.info("\n" + "="*60)
                logger.info("RACE COMPLETE - All laps streamed")
                logger.info("="*60)
                
                # Send disconnect message
                await websocket.send(json.dumps({"type": "disconnect"}))
        
        except websockets.exceptions.WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            logger.error("Is the AI Intelligence Layer running on port 9000?")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
    
    def apply_controls(self, brake_bias: int, differential_slip: int):
        """
        Apply control adjustments to the car.
        In real Pi, this would interface with hardware controllers.
        """
        logger.info(f"[APPLYING] Setting brake_bias={brake_bias}, diff_slip={differential_slip}")
        
        # Simulate applying controls (in real implementation, this would:
        # - Adjust brake bias actuator
        # - Modify differential slip controller
        # - Send CAN bus messages to ECU
        # - Update dashboard display)
        
        # For simulation, just log the change
        if brake_bias > 6:
            logger.info("  → Brake bias shifted REAR (protecting front tires)")
        elif brake_bias < 5:
            logger.info("  → Brake bias shifted FRONT (aggressive turn-in)")
        else:
            logger.info("  → Brake bias NEUTRAL")
        
        if differential_slip > 6:
            logger.info("  → Differential slip INCREASED (gentler on tires)")
        elif differential_slip < 5:
            logger.info("  → Differential slip DECREASED (aggressive cornering)")
        else:
            logger.info("  → Differential slip NEUTRAL")


async def main():
    parser = argparse.ArgumentParser(
        description="WebSocket-based Raspberry Pi Telemetry Simulator"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=60.0,
        help="Seconds between laps (default: 60s)"
    )
    parser.add_argument(
        "--ws-url",
        type=str,
        default="ws://localhost:9000/ws/pi",
        help="WebSocket URL for AI layer (default: ws://localhost:9000/ws/pi)"
    )
    parser.add_argument(
        "--enrichment-url",
        type=str,
        default="http://localhost:8000",
        help="Enrichment service URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Path to lap CSV file (default: scripts/ALONSO_2023_MONZA_LAPS.csv)"
    )
    
    args = parser.parse_args()
    
    # Determine CSV path
    if args.csv:
        csv_path = Path(args.csv)
    else:
        script_dir = Path(__file__).parent
        csv_path = script_dir / "ALONSO_2023_MONZA_LAPS.csv"
    
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        sys.exit(1)
    
    # Create simulator and run
    simulator = PiSimulator(
        csv_path=csv_path,
        ws_url=args.ws_url,
        enrichment_url=args.enrichment_url,
        interval=args.interval
    )
    
    logger.info("Starting WebSocket Pi Simulator")
    logger.info(f"CSV: {csv_path}")
    logger.info(f"Enrichment Service: {args.enrichment_url}")
    logger.info(f"WebSocket URL: {args.ws_url}")
    logger.info(f"Interval: {args.interval}s per lap")
    logger.info("-" * 60)
    
    await simulator.stream_telemetry()


if __name__ == "__main__":
    asyncio.run(main())
