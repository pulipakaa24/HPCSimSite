"""
Validators for strategy validation and telemetry analysis.
"""
from typing import List, Tuple
import logging
from models.input_models import Strategy, RaceContext, EnrichedTelemetryWebhook

logger = logging.getLogger(__name__)


class StrategyValidator:
    """Validates race strategies against F1 rules and constraints."""
    
    @staticmethod
    def validate_strategy(strategy: Strategy, race_context: RaceContext) -> Tuple[bool, str]:
        """
        Validate a single strategy.
        
        Args:
            strategy: Strategy to validate
            race_context: Current race context
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        current_lap = race_context.race_info.current_lap
        total_laps = race_context.race_info.total_laps
        
        # Check pit laps are within valid range
        for pit_lap in strategy.pit_laps:
            if pit_lap <= current_lap:
                return False, f"Pit lap {pit_lap} is in the past (current lap: {current_lap})"
            if pit_lap >= total_laps:
                return False, f"Pit lap {pit_lap} is beyond race end (total laps: {total_laps})"
        
        # Check pit laps are in order
        if len(strategy.pit_laps) > 1:
            if strategy.pit_laps != sorted(strategy.pit_laps):
                return False, "Pit laps must be in ascending order"
        
        # Check stop count matches pit laps
        if len(strategy.pit_laps) != strategy.stop_count:
            return False, f"Stop count ({strategy.stop_count}) doesn't match pit laps ({len(strategy.pit_laps)})"
        
        # Check tire sequence length
        expected_tire_count = strategy.stop_count + 1
        if len(strategy.tire_sequence) != expected_tire_count:
            return False, f"Tire sequence length ({len(strategy.tire_sequence)}) doesn't match stops + 1"
        
        # Check at least 2 different compounds (F1 rule)
        unique_compounds = set(strategy.tire_sequence)
        if len(unique_compounds) < 2:
            return False, "Must use at least 2 different tire compounds (F1 rule)"
        
        return True, ""
    
    @staticmethod
    def validate_strategies(strategies: List[Strategy], race_context: RaceContext) -> List[Strategy]:
        """
        Validate all strategies and filter out invalid ones.
        
        Args:
            strategies: List of strategies to validate
            race_context: Current race context
            
        Returns:
            List of valid strategies
        """
        valid_strategies = []
        
        for strategy in strategies:
            is_valid, error = StrategyValidator.validate_strategy(strategy, race_context)
            if is_valid:
                valid_strategies.append(strategy)
            else:
                logger.warning(f"Strategy {strategy.strategy_id} invalid: {error}")
        
        logger.info(f"Validated {len(valid_strategies)}/{len(strategies)} strategies")
        return valid_strategies


class TelemetryAnalyzer:
    """Analyzes enriched lap-level telemetry data to extract trends and insights."""
    
    @staticmethod
    def calculate_tire_degradation_rate(telemetry: List[EnrichedTelemetryWebhook]) -> float:
        """
        Calculate tire degradation rate per lap (using lap-level data).
        
        Args:
            telemetry: List of enriched telemetry records
            
        Returns:
            Latest tire degradation rate (0.0 to 1.0)
        """
        if not telemetry:
            return 0.0
        
        # Use latest tire degradation rate from enrichment
        latest = max(telemetry, key=lambda x: x.lap)
        return latest.tire_degradation_rate
    
    @staticmethod
    def project_tire_cliff(
        telemetry: List[EnrichedTelemetryWebhook],
        current_lap: int
    ) -> int:
        """
        Project when tire cliff will be reached (using lap-level data).
        
        Args:
            telemetry: List of enriched telemetry records
            current_lap: Current lap number
            
        Returns:
            Estimated lap number when cliff will be reached
        """
        if not telemetry:
            return current_lap + 20  # Default assumption
        
        # Use tire cliff risk from enrichment
        latest = max(telemetry, key=lambda x: x.lap)
        cliff_risk = latest.tire_cliff_risk
        
        if cliff_risk >= 0.7:
            return current_lap + 2  # Imminent cliff
        elif cliff_risk >= 0.4:
            return current_lap + 5  # Approaching cliff
        else:
            # Estimate based on optimal pit window
            pit_window = latest.optimal_pit_window
            return pit_window[1] if pit_window else current_lap + 15
