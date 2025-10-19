"""
Strategy generator service - Step 1: Brainstorming.
"""
import logging
from typing import List
from config import get_settings
from models.input_models import EnrichedTelemetryWebhook, RaceContext, Strategy
from models.output_models import BrainstormResponse
from services.gemini_client import GeminiClient
from prompts.brainstorm_prompt import build_brainstorm_prompt
from utils.validators import StrategyValidator

logger = logging.getLogger(__name__)


class StrategyGenerator:
    """Generates diverse race strategies using Gemini AI."""
    
    def __init__(self):
        """Initialize strategy generator."""
        self.gemini_client = GeminiClient()
        self.settings = get_settings()
        logger.info("Strategy generator initialized")
    
    async def generate(
        self,
        enriched_telemetry: List[EnrichedTelemetryWebhook],
        race_context: RaceContext,
        strategy_history: List[dict] = None
    ) -> BrainstormResponse:
        """
        Generate 20 diverse race strategies.
        
        Args:
            enriched_telemetry: Recent enriched telemetry data
            race_context: Current race context
            strategy_history: List of previous strategies for continuity
            
        Returns:
            BrainstormResponse with 20 strategies
            
        Raises:
            Exception: If generation fails
        """
        logger.info(f"Generating strategies using {len(enriched_telemetry)} laps of telemetry")
        if strategy_history:
            logger.info(f"Including {len(strategy_history)} previous strategies in context")
        
        # Build prompt (use fast mode if enabled)
        if self.settings.fast_mode:
            from prompts.brainstorm_prompt import build_brainstorm_prompt_fast
            prompt = build_brainstorm_prompt_fast(enriched_telemetry, race_context, strategy_history or [])
        else:
            prompt = build_brainstorm_prompt(enriched_telemetry, race_context, strategy_history or [])
        
        # Generate with Gemini (high temperature for creativity)
        response_data = await self.gemini_client.generate_json(
            prompt=prompt,
            temperature=0.9,
            timeout=self.settings.brainstorm_timeout
        )
        
        # Parse strategies
        if "strategies" not in response_data:
            raise Exception("Response missing 'strategies' field")
        
        strategies_data = response_data["strategies"]
        
        # Validate and parse strategies
        strategies = []
        for s_data in strategies_data:
            try:
                strategy = Strategy(**s_data)
                strategies.append(strategy)
            except Exception as e:
                logger.warning(f"Failed to parse strategy: {e}")
        
        logger.info(f"Generated {len(strategies)} valid strategies")
        
        # Validate strategies
        valid_strategies = StrategyValidator.validate_strategies(strategies, race_context)
        
        # Return response
        return BrainstormResponse(strategies=valid_strategies)
