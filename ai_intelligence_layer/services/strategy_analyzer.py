"""
Strategy analyzer service - Step 2: Analysis & Selection.
"""
import logging
from typing import List
from config import get_settings
from models.input_models import EnrichedTelemetryWebhook, RaceContext, Strategy
from models.output_models import (
    AnalyzeResponse,
    AnalyzedStrategy,
    PredictedOutcome,
    RiskAssessment,
    TelemetryInsights,
    EngineerBrief,
    ECUCommands,
    SituationalContext
)
from services.gemini_client import GeminiClient
from prompts.analyze_prompt import build_analyze_prompt

logger = logging.getLogger(__name__)


class StrategyAnalyzer:
    """Analyzes strategies and selects top 3 using Gemini AI."""
    
    def __init__(self):
        """Initialize strategy analyzer."""
        self.gemini_client = GeminiClient()
        self.settings = get_settings()
        logger.info("Strategy analyzer initialized")
    
    async def analyze(
        self,
        enriched_telemetry: List[EnrichedTelemetryWebhook],
        race_context: RaceContext,
        strategies: List[Strategy]
    ) -> AnalyzeResponse:
        """
        Analyze strategies and select top 3.
        
        Args:
            enriched_telemetry: Recent enriched telemetry data
            race_context: Current race context
            strategies: Strategies to analyze
            
        Returns:
            AnalyzeResponse with top 3 strategies
            
        Raises:
            Exception: If analysis fails
        """
        logger.info(f"Starting strategy analysis for {len(strategies)} strategies...")
        
        # Build prompt (use fast mode if enabled)
        if self.settings.fast_mode:
            from prompts.analyze_prompt import build_analyze_prompt_fast
            prompt = build_analyze_prompt_fast(enriched_telemetry, race_context, strategies)
            logger.info("Using FAST MODE prompt")
        else:
            prompt = build_analyze_prompt(enriched_telemetry, race_context, strategies)
        logger.debug(f"Prompt length: {len(prompt)} chars")
        
        # Generate with Gemini (lower temperature for analytical consistency)
        response_data = await self.gemini_client.generate_json(
            prompt=prompt,
            temperature=0.3,
            timeout=self.settings.analyze_timeout
        )
        
        # Log the response structure for debugging
        logger.info(f"Gemini response keys: {list(response_data.keys())}")
        
        # Parse top strategies
        if "top_strategies" not in response_data:
            # Log first 500 chars of response for debugging
            response_preview = str(response_data)[:500]
            logger.error(f"Response preview: {response_preview}...")
            raise Exception(f"Response missing 'top_strategies' field. Got keys: {list(response_data.keys())}. Check logs for details.")
        
        if "situational_context" not in response_data:
            raise Exception("Response missing 'situational_context' field")
        
        top_strategies_data = response_data["top_strategies"]
        situational_context_data = response_data["situational_context"]
        
        logger.info(f"Received {len(top_strategies_data)} top strategies from Gemini")
        
        # Parse top strategies
        top_strategies = []
        for ts_data in top_strategies_data:
            try:
                # Parse nested structures
                predicted_outcome = PredictedOutcome(**ts_data["predicted_outcome"])
                risk_assessment = RiskAssessment(**ts_data["risk_assessment"])
                telemetry_insights = TelemetryInsights(**ts_data["telemetry_insights"])
                engineer_brief = EngineerBrief(**ts_data["engineer_brief"])
                ecu_commands = ECUCommands(**ts_data["ecu_commands"])
                
                # Create analyzed strategy
                analyzed_strategy = AnalyzedStrategy(
                    rank=ts_data["rank"],
                    strategy_id=ts_data["strategy_id"],
                    strategy_name=ts_data["strategy_name"],
                    classification=ts_data["classification"],
                    predicted_outcome=predicted_outcome,
                    risk_assessment=risk_assessment,
                    telemetry_insights=telemetry_insights,
                    engineer_brief=engineer_brief,
                    driver_audio_script=ts_data["driver_audio_script"],
                    ecu_commands=ecu_commands
                )
                
                top_strategies.append(analyzed_strategy)
                
            except Exception as e:
                logger.warning(f"Failed to parse strategy rank {ts_data.get('rank', '?')}: {e}")
        
        # Parse situational context
        situational_context = SituationalContext(**situational_context_data)
        
        # Validate we have 3 strategies
        if len(top_strategies) != 3:
            logger.warning(f"Expected 3 top strategies, got {len(top_strategies)}")
        
        logger.info(f"Successfully analyzed and selected {len(top_strategies)} strategies")
        
        # Return response
        return AnalyzeResponse(
            top_strategies=top_strategies,
            situational_context=situational_context
        )
