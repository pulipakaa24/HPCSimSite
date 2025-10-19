"""
AI Intelligence Layer - FastAPI Application
Port: 9000
Provides F1 race strategy generation and analysis using Gemini AI.
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import Dict, Any

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


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.ai_service_host,
        port=settings.ai_service_port,
        reload=True
    )

