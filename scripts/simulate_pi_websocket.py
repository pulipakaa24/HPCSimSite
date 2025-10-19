#!/usr/bin/env python3
"""
WebSocket-based Raspberry Pi Telemetry Simulator.

Connects to AI Intelligence Layer via WebSocket and:
1. Streams lap telemetry to AI layer
2. Receives control commands (brake_bias, differential_slip) from AI layer
3. Applies control adjustments in real-time
4. Generates voice announcements for strategy updates

Usage:
    python simulate_pi_websocket.py --interval 5 --ws-url ws://192.168.137.134:9000/ws/pi --enable-voice
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import sys
import os
from datetime import datetime

try:
    import pandas as pd
    import websockets
    from websockets.client import WebSocketClientProtocol
except ImportError:
    print("Error: Required packages not installed.")
    print("Run: pip install pandas websockets")
    sys.exit(1)

# Optional voice support
try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import save
    from dotenv import load_dotenv
    # Load .env from root directory (default behavior)
    load_dotenv()
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    print("Note: elevenlabs not installed. Voice features disabled.")
    print("To enable voice: pip install elevenlabs python-dotenv")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VoiceAnnouncer:
    """ElevenLabs text-to-speech announcer for race engineer communications."""
    
    def __init__(self, enabled: bool = True):
        """Initialize ElevenLabs voice engine if available."""
        self.enabled = enabled and VOICE_AVAILABLE
        self.client = None
        self.audio_dir = Path("data/audio")
        # Use exact same voice as voice_service.py
        self.voice_id = "mbBupyLcEivjpxh8Brkf"  # Rachel voice
        
        if self.enabled:
            try:
                api_key = os.getenv("ELEVENLABS_API_KEY")
                if not api_key:
                    logger.warning("⚠ ELEVENLABS_API_KEY not found in environment")
                    self.enabled = False
                    return
                
                self.client = ElevenLabs(api_key=api_key)
                self.audio_dir.mkdir(parents=True, exist_ok=True)
                logger.info("✓ Voice announcer initialized (ElevenLabs)")
            except Exception as e:
                logger.warning(f"⚠ Voice engine initialization failed: {e}")
                self.enabled = False
    
    def _format_strategy_message(self, data: Dict[str, Any]) -> str:
        """
        Format strategy update into natural race engineer speech.
        
        Args:
            data: Control command update from AI layer
            
        Returns:
            Formatted message string
        """
        lap = data.get('lap', 0)
        strategy_name = data.get('strategy_name', 'Unknown')
        brake_bias = data.get('brake_bias', 5)
        diff_slip = data.get('differential_slip', 5)
        reasoning = data.get('reasoning', '')
        risk_level = data.get('risk_level', '')
        
        # Build natural message
        parts = []
        
        # Opening with lap number
        parts.append(f"Lap {lap}.")
        
        # Strategy announcement with risk level
        if strategy_name and strategy_name != "N/A":
            # Simplify strategy name for speech
            clean_strategy = strategy_name.replace('-', ' ').replace('_', ' ')
            if risk_level:
                parts.append(f"Running {clean_strategy} strategy, {risk_level} risk.")
            else:
                parts.append(f"Running {clean_strategy} strategy.")
        
        # Control adjustments with specific values
        control_messages = []
        
        # Brake bias announcement with context
        if brake_bias < 4:
            control_messages.append(f"Brake bias set to {brake_bias}, forward biased for sharper turn in response")
        elif brake_bias == 4:
            control_messages.append(f"Brake bias {brake_bias}, slightly forward to help rotation")
        elif brake_bias > 6:
            control_messages.append(f"Brake bias set to {brake_bias}, rearward to protect front tire wear")
        elif brake_bias == 6:
            control_messages.append(f"Brake bias {brake_bias}, slightly rear for front tire management")
        else:
            control_messages.append(f"Brake bias neutral at {brake_bias}")
        
        # Differential slip announcement with context
        if diff_slip < 4:
            control_messages.append(f"Differential at {diff_slip}, tightened for better rotation through corners")
        elif diff_slip == 4:
            control_messages.append(f"Differential {diff_slip}, slightly tight for rotation")
        elif diff_slip > 6:
            control_messages.append(f"Differential set to {diff_slip}, loosened to reduce rear tire degradation")
        elif diff_slip == 6:
            control_messages.append(f"Differential {diff_slip}, slightly loose for tire preservation")
        else:
            control_messages.append(f"Differential neutral at {diff_slip}")
        
        if control_messages:
            parts.append(". ".join(control_messages) + ".")
        
        # Key reasoning excerpt (first sentence only)
        if reasoning:
            # Extract first meaningful sentence
            sentences = reasoning.split('.')
            if sentences:
                key_reason = sentences[0].strip()
                if len(key_reason) > 20 and len(key_reason) < 150:  # Slightly longer for more context
                    parts.append(key_reason + ".")
        
        return " ".join(parts)
    
    def _format_control_message(self, data: Dict[str, Any]) -> str:
        """
        Format control command into brief message.
        
        Args:
            data: Control command from AI layer
            
        Returns:
            Formatted message string
        """
        lap = data.get('lap', 0)
        brake_bias = data.get('brake_bias', 5)
        diff_slip = data.get('differential_slip', 5)
        message = data.get('message', '')
        
        # For early laps or non-strategy updates
        if message and "Collecting data" in message:
            return f"Lap {lap}. Collecting baseline data."
        
        if brake_bias == 5 and diff_slip == 5:
            return f"Lap {lap}. Maintaining neutral settings."
        
        return f"Lap {lap}. Controls adjusted."
    
    async def announce_strategy(self, data: Dict[str, Any]):
        """
        Announce strategy update with ElevenLabs voice synthesis.
        
        Args:
            data: Control command update from AI layer
        """
        if not self.enabled:
            return
        
        try:
            # Format message
            message = self._format_strategy_message(data)
            
            logger.info(f"[VOICE] Announcing: {message}")
            
            # Generate unique audio filename
            lap = data.get('lap', 0)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_path = self.audio_dir / f"lap_{lap}_{timestamp}.mp3"
            
            # Synthesize with ElevenLabs (exact same settings as voice_service.py)
            def synthesize():
                try:
                    audio = self.client.text_to_speech.convert(
                        voice_id=self.voice_id,
                        text=message,
                        model_id="eleven_multilingual_v2",  # Fast, low-latency model
                        voice_settings={
                            "stability": 0.4,
                            "similarity_boost": 0.95,
                            "style": 0.7,
                            "use_speaker_boost": True
                        }
                    )
                    save(audio, str(audio_path))
                    logger.info(f"[VOICE] Saved to {audio_path}")
                    
                    # Play the audio
                    if sys.platform == "darwin":  # macOS
                        os.system(f"afplay {audio_path}")
                    elif sys.platform == "linux":
                        os.system(f"mpg123 {audio_path} || ffplay -nodisp -autoexit {audio_path}")
                    elif sys.platform == "win32":
                        os.system(f"start {audio_path}")
                    
                    # Clean up audio file after playing
                    try:
                        if audio_path.exists():
                            audio_path.unlink()
                            logger.info(f"[VOICE] Cleaned up {audio_path}")
                    except Exception as cleanup_error:
                        logger.warning(f"[VOICE] Failed to delete audio file: {cleanup_error}")
                except Exception as e:
                    logger.error(f"[VOICE] Synthesis error: {e}")
            
            # Run in separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, synthesize)
            
        except Exception as e:
            logger.error(f"[VOICE] Announcement failed: {e}")
    
    async def announce_control(self, data: Dict[str, Any]):
        """
        Announce control command with ElevenLabs voice synthesis (brief version).
        
        Args:
            data: Control command from AI layer
        """
        if not self.enabled:
            return
        
        try:
            # Format message
            message = self._format_control_message(data)
            
            logger.info(f"[VOICE] Announcing: {message}")
            
            # Generate unique audio filename
            lap = data.get('lap', 0)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_path = self.audio_dir / f"lap_{lap}_control_{timestamp}.mp3"
            
            # Synthesize with ElevenLabs (exact same settings as voice_service.py)
            def synthesize():
                try:
                    audio = self.client.text_to_speech.convert(
                        voice_id=self.voice_id,
                        text=message,
                        model_id="eleven_multilingual_v2",  # Fast, low-latency model
                        voice_settings={
                            "stability": 0.4,
                            "similarity_boost": 0.95,
                            "style": 0.7,
                            "use_speaker_boost": True
                        }
                    )
                    save(audio, str(audio_path))
                    logger.info(f"[VOICE] Saved to {audio_path}")
                    
                    # Play the audio
                    if sys.platform == "darwin":  # macOS
                        os.system(f"afplay {audio_path}")
                    elif sys.platform == "linux":
                        os.system(f"mpg123 {audio_path} || ffplay -nodisp -autoexit {audio_path}")
                    elif sys.platform == "win32":
                        os.system(f"start {audio_path}")
                    
                    # Clean up audio file after playing
                    try:
                        if audio_path.exists():
                            audio_path.unlink()
                            logger.info(f"[VOICE] Cleaned up {audio_path}")
                    except Exception as cleanup_error:
                        logger.warning(f"[VOICE] Failed to delete audio file: {cleanup_error}")
                except Exception as e:
                    logger.error(f"[VOICE] Synthesis error: {e}")
            
            # Run in separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, synthesize)
            
        except Exception as e:
            logger.error(f"[VOICE] Announcement failed: {e}")


class PiSimulator:
    """WebSocket-based Pi simulator with control feedback and voice announcements."""
    
    def __init__(self, csv_path: Path, ws_url: str, interval: float = 60.0, enrichment_url: str = "http://192.168.137.134:8000", voice_enabled: bool = False):
        self.csv_path = csv_path
        self.ws_url = ws_url
        self.enrichment_url = enrichment_url
        self.interval = interval
        self.df: Optional[pd.DataFrame] = None
        self.current_controls = {
            "brake_bias": 5,
            "differential_slip": 5
        }
        self.previous_controls = {
            "brake_bias": 5,
            "differential_slip": 5
        }
        self.current_risk_level: Optional[str] = None
        self.voice_announcer = VoiceAnnouncer(enabled=voice_enabled)
    
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
            "position": int(row["position"]) if pd.notna(row["position"]) else 10,
            "gap_to_leader": float(row["gap_to_leader"]) if pd.notna(row["gap_to_leader"]) else 0.0,
            "gap_to_ahead": float(row["gap_to_ahead"]) if pd.notna(row["gap_to_ahead"]) else 0.0,
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
                        
                        # Handle silent acknowledgment (no control update, no voice)
                        if response_data.get("type") == "acknowledgment":
                            message = response_data.get("message", "")
                            logger.info(f"[ACK] {message}")
                            
                            # Now wait for the actual control command update
                            try:
                                update = await asyncio.wait_for(websocket.recv(), timeout=45.0)
                                update_data = json.loads(update)
                                
                                if update_data.get("type") == "control_command_update":
                                    brake_bias = update_data.get("brake_bias", 5)
                                    diff_slip = update_data.get("differential_slip", 5)
                                    strategy_name = update_data.get("strategy_name", "N/A")
                                    risk_level = update_data.get("risk_level", "medium")
                                    reasoning = update_data.get("reasoning", "")
                                    
                                    # Check if controls changed from previous
                                    controls_changed = (
                                        self.current_controls["brake_bias"] != brake_bias or
                                        self.current_controls["differential_slip"] != diff_slip
                                    )
                                    
                                    # Check if risk level changed
                                    risk_level_changed = (
                                        self.current_risk_level is not None and
                                        self.current_risk_level != risk_level
                                    )
                                    
                                    self.previous_controls = self.current_controls.copy()
                                    self.current_controls["brake_bias"] = brake_bias
                                    self.current_controls["differential_slip"] = diff_slip
                                    self.current_risk_level = risk_level
                                    
                                    logger.info(f"[UPDATED] Strategy-Based Control:")
                                    logger.info(f"  ├─ Brake Bias: {brake_bias}/10")
                                    logger.info(f"  ├─ Differential Slip: {diff_slip}/10")
                                    logger.info(f"  ├─ Strategy: {strategy_name}")
                                    logger.info(f"  ├─ Risk Level: {risk_level}")
                                    if reasoning:
                                        logger.info(f"  └─ Reasoning: {reasoning[:100]}...")
                                    
                                    self.apply_controls(brake_bias, diff_slip)
                                    
                                    # Voice announcement if controls OR risk level changed
                                    if controls_changed or risk_level_changed:
                                        if risk_level_changed and not controls_changed:
                                            logger.info(f"[VOICE] Risk level changed to {risk_level}")
                                        await self.voice_announcer.announce_strategy(update_data)
                                    else:
                                        logger.info(f"[VOICE] Skipping announcement - controls and risk level unchanged")
                            except asyncio.TimeoutError:
                                logger.warning("[TIMEOUT] Strategy generation took too long")
                        
                        elif response_data.get("type") == "control_command":
                            brake_bias = response_data.get("brake_bias", 5)
                            diff_slip = response_data.get("differential_slip", 5)
                            strategy_name = response_data.get("strategy_name", "N/A")
                            message = response_data.get("message")
                            
                            # Store previous values before updating
                            controls_changed = (
                                self.current_controls["brake_bias"] != brake_bias or
                                self.current_controls["differential_slip"] != diff_slip
                            )
                            
                            self.previous_controls = self.current_controls.copy()
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
                            
                            # Voice announcement ONLY if controls changed
                            if controls_changed:
                                await self.voice_announcer.announce_control(response_data)
                            
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
                                        risk_level = update_data.get("risk_level", "medium")
                                        reasoning = update_data.get("reasoning", "")
                                        
                                        # Check if controls changed from previous
                                        controls_changed = (
                                            self.current_controls["brake_bias"] != brake_bias or
                                            self.current_controls["differential_slip"] != diff_slip
                                        )
                                        
                                        # Check if risk level changed
                                        risk_level_changed = (
                                            self.current_risk_level is not None and
                                            self.current_risk_level != risk_level
                                        )
                                        
                                        self.previous_controls = self.current_controls.copy()
                                        self.current_controls["brake_bias"] = brake_bias
                                        self.current_controls["differential_slip"] = diff_slip
                                        self.current_risk_level = risk_level
                                        
                                        logger.info(f"[UPDATED] Strategy-Based Control:")
                                        logger.info(f"  ├─ Brake Bias: {brake_bias}/10")
                                        logger.info(f"  ├─ Differential Slip: {diff_slip}/10")
                                        logger.info(f"  ├─ Strategy: {strategy_name}")
                                        logger.info(f"  ├─ Risk Level: {risk_level}")
                                        if reasoning:
                                            logger.info(f"  └─ Reasoning: {reasoning[:100]}...")
                                        
                                        self.apply_controls(brake_bias, diff_slip)
                                        
                                        # Voice announcement if controls OR risk level changed
                                        if controls_changed or risk_level_changed:
                                            if risk_level_changed and not controls_changed:
                                                logger.info(f"[VOICE] Risk level changed to {risk_level}")
                                            await self.voice_announcer.announce_strategy(update_data)
                                        else:
                                            logger.info(f"[VOICE] Skipping announcement - controls and risk level unchanged")
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
        description="WebSocket-based Raspberry Pi Telemetry Simulator with Voice Announcements"
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
        default="ws://192.168.137.134:9000/ws/pi",
        help="WebSocket URL for AI layer (default: ws://192.168.137.134:9000/ws/pi)"
    )
    parser.add_argument(
        "--enrichment-url",
        type=str,
        default="http://192.168.137.134:8000",
        help="Enrichment service URL (default: http://192.168.137.134:8000)"
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Path to lap CSV file (default: scripts/ALONSO_2023_MONZA_LAPS.csv)"
    )
    parser.add_argument(
        "--enable-voice",
        action="store_true",
        help="Enable voice announcements for strategy updates (requires elevenlabs and ELEVENLABS_API_KEY)"
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
        interval=args.interval,
        voice_enabled=args.enable_voice
    )
    
    logger.info("Starting WebSocket Pi Simulator")
    logger.info(f"CSV: {csv_path}")
    logger.info(f"Enrichment Service: {args.enrichment_url}")
    logger.info(f"WebSocket URL: {args.ws_url}")
    logger.info(f"Interval: {args.interval}s per lap")
    logger.info(f"Voice Announcements: {'Enabled' if args.enable_voice and VOICE_AVAILABLE else 'Disabled'}")
    logger.info("-" * 60)
    
    await simulator.stream_telemetry()


if __name__ == "__main__":
    asyncio.run(main())
