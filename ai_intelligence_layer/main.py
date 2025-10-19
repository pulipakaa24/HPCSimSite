"""
AI Intelligence Layer - FastAPI Application
Port: 9000
Provides F1 race strategy generation and analysis using Gemini AI.
Supports WebSocket connections from Pi for bidirectional control.
"""
from fastapi import FastAPI, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio
import random
from typing import Dict, Any, List

from config import get_settings
from models.input_models import (
    BrainstormRequest,
    # AnalyzeRequest,  # Disabled - not using analysis
    EnrichedTelemetryWebhook,
    EnrichedTelemetryWithContext,
    RaceContext  # Import for global storage
)
from models.output_models import (
    BrainstormResponse,
    # AnalyzeResponse,  # Disabled - not using analysis
    HealthResponse
)
from services.strategy_generator import StrategyGenerator
# from services.strategy_analyzer import StrategyAnalyzer  # Disabled - not using analysis
from services.telemetry_client import TelemetryClient
from utils.telemetry_buffer import TelemetryBuffer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Global instances
telemetry_buffer: TelemetryBuffer = None
strategy_generator: StrategyGenerator = None
# strategy_analyzer: StrategyAnalyzer = None  # Disabled - not using analysis
telemetry_client: TelemetryClient = None
current_race_context: RaceContext = None  # Store race context globally
last_control_command: Dict[str, int] = {"brake_bias": 5, "differential_slip": 5}  # Store last command

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections from Pi clients."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Pi client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"Pi client disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_control_command(self, websocket: WebSocket, command: Dict[str, Any]):
        """Send control command to specific Pi client."""
        await websocket.send_json(command)
    
    async def broadcast_control_command(self, command: Dict[str, Any]):
        """Broadcast control command to all connected Pi clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(command)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")

websocket_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI application."""
    global telemetry_buffer, strategy_generator, telemetry_client
    
    settings = get_settings()
    logger.info(f"Starting AI Intelligence Layer on port {settings.ai_service_port}")
    logger.info(f"Demo mode: {settings.demo_mode}")
    logger.info(f"Strategy count: {settings.strategy_count}")
    
    # Initialize services
    telemetry_buffer = TelemetryBuffer()
    strategy_generator = StrategyGenerator()
    # strategy_analyzer = StrategyAnalyzer()  # Disabled - not using analysis
    telemetry_client = TelemetryClient()
    
    logger.info("All services initialized successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down AI Intelligence Layer")


# Create FastAPI app
app = FastAPI(
    title="F1 AI Intelligence Layer",
    description="Advanced race strategy generation and analysis using HPC telemetry data",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        service="AI Intelligence Layer",
        version="1.0.0",
        demo_mode=settings.demo_mode,
        enrichment_service_url=settings.enrichment_service_url
    )


@app.post("/api/ingest/enriched")
async def ingest_enriched_telemetry(data: EnrichedTelemetryWithContext):
    """
    Webhook receiver for enriched telemetry data from HPC enrichment module.
    This is called when enrichment service has NEXT_STAGE_CALLBACK_URL configured.
    
    Receives enriched telemetry + race context and automatically triggers strategy brainstorming.
    """
    global current_race_context
    
    try:
        logger.info(f"Received enriched telemetry webhook: lap {data.enriched_telemetry.lap}")
        
        # Store telemetry in buffer
        telemetry_buffer.add(data.enriched_telemetry)
        
        # Update global race context
        current_race_context = data.race_context
        
        # Automatically trigger strategy brainstorming
        buffer_data = telemetry_buffer.get_latest(limit=10)
        
        if buffer_data and len(buffer_data) >= 3:  # Wait for at least 3 laps of data
            logger.info(f"Auto-triggering strategy brainstorm with {len(buffer_data)} telemetry records")
            
            try:
                # Generate strategies
                response = await strategy_generator.generate(
                    enriched_telemetry=buffer_data,
                    race_context=data.race_context
                )
                
                logger.info(f"Auto-generated {len(response.strategies)} strategies for lap {data.enriched_telemetry.lap}")
                
                return {
                    "status": "received_and_processed",
                    "lap": data.enriched_telemetry.lap,
                    "buffer_size": telemetry_buffer.size(),
                    "strategies_generated": len(response.strategies),
                    "strategies": [s.model_dump() for s in response.strategies]
                }
            except Exception as e:
                logger.error(f"Error in auto-brainstorm: {e}", exc_info=True)
                # Still return success for ingestion even if brainstorm fails
                return {
                    "status": "received_but_brainstorm_failed",
                    "lap": data.enriched_telemetry.lap,
                    "buffer_size": telemetry_buffer.size(),
                    "error": str(e)
                }
        else:
            logger.info(f"Buffer has only {len(buffer_data) if buffer_data else 0} records, waiting for more data before brainstorming")
            return {
                "status": "received_waiting_for_more_data",
                "lap": data.enriched_telemetry.lap,
                "buffer_size": telemetry_buffer.size()
            }
            
    except Exception as e:
        logger.error(f"Error ingesting telemetry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest telemetry: {str(e)}"
        )


@app.post("/api/strategy/brainstorm", response_model=BrainstormResponse)
async def brainstorm_strategies(request: BrainstormRequest):
    """
    Generate 20 diverse race strategies based on enriched telemetry and race context.
    This is Step 1 of the AI strategy process.
    """
    try:
        logger.info(f"Brainstorming strategies for {request.race_context.driver_state.driver_name}")
        logger.info(f"Current lap: {request.race_context.race_info.current_lap}/{request.race_context.race_info.total_laps}")
        
        # If no enriched telemetry provided, try buffer first, then enrichment service
        enriched_data = request.enriched_telemetry
        if not enriched_data:
            # First try to get from webhook buffer (push model)
            buffer_data = telemetry_buffer.get_latest(limit=10)
            if buffer_data:
                logger.info(f"Using {len(buffer_data)} telemetry records from webhook buffer")
                enriched_data = buffer_data
            else:
                # Fallback: fetch from enrichment service (pull model)
                logger.info("No telemetry in buffer, fetching from enrichment service...")
                enriched_data = await telemetry_client.fetch_latest()
                if not enriched_data:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No enriched telemetry available. Please provide data, ensure enrichment service is running, or configure webhook push."
                    )
        
        # Generate strategies
        response = await strategy_generator.generate(
            enriched_telemetry=enriched_data,
            race_context=request.race_context
        )
        
        logger.info(f"Generated {len(response.strategies)} strategies")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in brainstorm: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Strategy generation failed: {str(e)}"
        )


# ANALYSIS ENDPOINT DISABLED FOR SPEED
# Uncomment below to re-enable full analysis workflow
"""
@app.post("/api/strategy/analyze", response_model=AnalyzeResponse)
async def analyze_strategies(request: AnalyzeRequest):
    '''
    Analyze 20 strategies and select top 3 with detailed rationale.
    This is Step 2 of the AI strategy process.
    '''
    try:
        logger.info(f"Analyzing {len(request.strategies)} strategies")
        logger.info(f"Current lap: {request.race_context.race_info.current_lap}")
        
        # If no enriched telemetry provided, try buffer first, then enrichment service
        enriched_data = request.enriched_telemetry
        if not enriched_data:
            # First try to get from webhook buffer (push model)
            buffer_data = telemetry_buffer.get_latest(limit=10)
            if buffer_data:
                logger.info(f"Using {len(buffer_data)} telemetry records from webhook buffer")
                enriched_data = buffer_data
            else:
                # Fallback: fetch from enrichment service (pull model)
                logger.info("No telemetry in buffer, fetching from enrichment service...")
                enriched_data = await telemetry_client.fetch_latest()
                if not enriched_data:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No enriched telemetry available. Please provide data, ensure enrichment service is running, or configure webhook push."
                    )
        
        # Analyze strategies
        response = await strategy_analyzer.analyze(
            enriched_telemetry=enriched_data,
            race_context=request.race_context,
            strategies=request.strategies
        )
        
        logger.info(f"Selected top 3 strategies: {[s.strategy_name for s in response.top_strategies]}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in analyze: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Strategy analysis failed: {str(e)}"
        )
"""


@app.websocket("/ws/pi")
async def websocket_pi_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for Raspberry Pi clients.
    
    Flow:
    1. Pi connects and streams lap telemetry via WebSocket
    2. AI layer processes telemetry and generates strategies
    3. AI layer pushes control commands back to Pi (brake_bias, differential_slip)
    """
    global current_race_context, last_control_command
    
    await websocket_manager.connect(websocket)
    
    # Clear telemetry buffer for fresh connection
    # This ensures lap counting starts from scratch for each Pi session
    telemetry_buffer.clear()
    
    # Reset last control command to neutral for new session
    last_control_command = {"brake_bias": 5, "differential_slip": 5}
    
    logger.info("[WebSocket] Telemetry buffer cleared for new connection")
    
    try:
        # Send initial welcome message
        await websocket.send_json({
            "type": "connection_established",
            "message": "Connected to AI Intelligence Layer",
            "status": "ready",
            "buffer_cleared": True
        })
        
        # Main message loop
        while True:
            # Receive telemetry from Pi
            data = await websocket.receive_json()
            
            message_type = data.get("type", "telemetry")
            
            if message_type == "telemetry":
                # Process incoming lap telemetry
                lap_number = data.get("lap_number", 0)
                
                # Store in buffer (convert to EnrichedTelemetryWebhook format)
                # Note: This assumes data is already enriched. If raw, route through enrichment first.
                enriched = data.get("enriched_telemetry")
                race_context_data = data.get("race_context")
                
                if enriched and race_context_data:
                    try:
                        # Parse enriched telemetry
                        enriched_obj = EnrichedTelemetryWebhook(**enriched)
                        telemetry_buffer.add(enriched_obj)
                        
                        # Update race context
                        current_race_context = RaceContext(**race_context_data)
                        
                        # Auto-generate strategies if we have enough data
                        buffer_data = telemetry_buffer.get_latest(limit=10)
                        
                        if len(buffer_data) >= 3:
                            logger.info(f"\n{'='*60}")
                            logger.info(f"LAP {lap_number} - GENERATING STRATEGY")
                            logger.info(f"{'='*60}")
                            
                            # Send immediate acknowledgment while processing
                            # Use last known control values instead of resetting to neutral
                            await websocket.send_json({
                                "type": "control_command",
                                "lap": lap_number,
                                "brake_bias": last_control_command["brake_bias"],
                                "differential_slip": last_control_command["differential_slip"],
                                "message": "Processing strategies (maintaining previous settings)..."
                            })
                            
                            # Generate strategies (this is the slow part)
                            try:
                                response = await strategy_generator.generate(
                                    enriched_telemetry=buffer_data,
                                    race_context=current_race_context
                                )
                                
                                # Extract top strategy (first one)
                                top_strategy = response.strategies[0] if response.strategies else None
                                
                                # Generate control commands based on strategy
                                control_command = generate_control_command(
                                    lap_number=lap_number,
                                    strategy=top_strategy,
                                    enriched_telemetry=enriched_obj,
                                    race_context=current_race_context
                                )
                                
                                # Update global last command
                                last_control_command = {
                                    "brake_bias": control_command["brake_bias"],
                                    "differential_slip": control_command["differential_slip"]
                                }
                                
                                # Send updated control command with strategies
                                await websocket.send_json({
                                    "type": "control_command_update",
                                    "lap": lap_number,
                                    "brake_bias": control_command["brake_bias"],
                                    "differential_slip": control_command["differential_slip"],
                                    "strategy_name": top_strategy.strategy_name if top_strategy else "N/A",
                                    "total_strategies": len(response.strategies),
                                    "reasoning": control_command.get("reasoning", "")
                                })
                                
                                logger.info(f"{'='*60}\n")
                            
                            except Exception as e:
                                logger.error(f"[WebSocket] Strategy generation failed: {e}")
                                # Send error but keep neutral controls
                                await websocket.send_json({
                                    "type": "error",
                                    "lap": lap_number,
                                    "message": f"Strategy generation failed: {str(e)}"
                                })
                        else:
                            # Not enough data yet, send neutral command
                            await websocket.send_json({
                                "type": "control_command",
                                "lap": lap_number,
                                "brake_bias": 5,  # Neutral
                                "differential_slip": 5,  # Neutral
                                "message": f"Collecting data ({len(buffer_data)}/3 laps)"
                            })
                    
                    except Exception as e:
                        logger.error(f"[WebSocket] Error processing telemetry: {e}")
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e)
                        })
                else:
                    logger.warning(f"[WebSocket] Received incomplete data from Pi")
            
            elif message_type == "ping":
                # Respond to ping
                await websocket.send_json({"type": "pong"})
            
            elif message_type == "disconnect":
                # Graceful disconnect
                logger.info("[WebSocket] Pi requested disconnect")
                break
    
    except WebSocketDisconnect:
        logger.info("[WebSocket] Pi client disconnected")
    except Exception as e:
        logger.error(f"[WebSocket] Unexpected error: {e}")
    finally:
        websocket_manager.disconnect(websocket)
        # Clear buffer when connection closes to ensure fresh start for next connection
        telemetry_buffer.clear()
        logger.info("[WebSocket] Telemetry buffer cleared on disconnect")


def generate_control_command(
    lap_number: int,
    strategy: Any,
    enriched_telemetry: EnrichedTelemetryWebhook,
    race_context: RaceContext
) -> Dict[str, Any]:
    """
    Generate control commands for Pi based on strategy and telemetry.
    
    Returns brake_bias and differential_slip values (0-10) with reasoning.
    
    Logic:
    - Brake bias: Adjust based on tire degradation (higher deg = more rear bias)
    - Differential slip: Adjust based on pace trend and tire cliff risk
    """
    # Default neutral values
    brake_bias = 5
    differential_slip = 5
    reasoning_parts = []
    
    # Adjust brake bias based on tire degradation
    if enriched_telemetry.tire_degradation_rate > 0.7:
        # High degradation: shift bias to rear (protect fronts)
        brake_bias = 7
        reasoning_parts.append(f"High tire degradation ({enriched_telemetry.tire_degradation_rate:.2f}) → Brake bias 7 (rear) to protect fronts")
    elif enriched_telemetry.tire_degradation_rate > 0.4:
        # Moderate degradation: slight rear bias
        brake_bias = 6
        reasoning_parts.append(f"Moderate tire degradation ({enriched_telemetry.tire_degradation_rate:.2f}) → Brake bias 6 (slight rear)")
    elif enriched_telemetry.tire_degradation_rate < 0.2:
        # Fresh tires: can use front bias for better turn-in
        brake_bias = 4
        reasoning_parts.append(f"Fresh tires ({enriched_telemetry.tire_degradation_rate:.2f}) → Brake bias 4 (front) for better turn-in")
    else:
        reasoning_parts.append(f"Normal tire degradation ({enriched_telemetry.tire_degradation_rate:.2f}) → Brake bias 5 (neutral)")
    
    # Adjust differential slip based on pace and tire cliff risk
    if enriched_telemetry.tire_cliff_risk > 0.7:
        # High cliff risk: increase slip for gentler tire treatment
        differential_slip = 7
        reasoning_parts.append(f"High tire cliff risk ({enriched_telemetry.tire_cliff_risk:.2f}) → Diff slip 7 (gentle tire treatment)")
    elif enriched_telemetry.pace_trend == "declining":
        # Pace declining: moderate slip increase
        differential_slip = 6
        reasoning_parts.append(f"Pace declining → Diff slip 6 (preserve performance)")
    elif enriched_telemetry.pace_trend == "improving":
        # Pace improving: can be aggressive, lower slip
        differential_slip = 4
        reasoning_parts.append(f"Pace improving → Diff slip 4 (aggressive, lower slip)")
    else:
        reasoning_parts.append(f"Pace stable → Diff slip 5 (neutral)")
    
    # Check if within pit window
    pit_window = enriched_telemetry.optimal_pit_window
    if pit_window and pit_window[0] <= lap_number <= pit_window[1]:
        # In pit window: conservative settings to preserve tires
        old_brake = brake_bias
        old_diff = differential_slip
        brake_bias = min(brake_bias + 1, 10)
        differential_slip = min(differential_slip + 1, 10)
        reasoning_parts.append(f"In pit window (laps {pit_window[0]}-{pit_window[1]}) → Conservative: brake {old_brake}→{brake_bias}, diff {old_diff}→{differential_slip}")
    
    # Format reasoning for terminal output
    reasoning_text = "\n".join(f"  • {part}" for part in reasoning_parts)
    
    # Print reasoning to terminal
    logger.info(f"CONTROL DECISION REASONING:")
    logger.info(reasoning_text)
    logger.info(f"FINAL COMMANDS: Brake Bias = {brake_bias}, Differential Slip = {differential_slip}")
    
    # Also include strategy info if available
    if strategy:
        logger.info(f"TOP STRATEGY: {strategy.strategy_name}")
        logger.info(f"  Risk Level: {strategy.risk_level}")
        logger.info(f"  Description: {strategy.brief_description}")
    
    return {
        "brake_bias": brake_bias,
        "differential_slip": differential_slip,
        "reasoning": reasoning_text
    }


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.ai_service_host,
        port=settings.ai_service_port,
        reload=True
    )


