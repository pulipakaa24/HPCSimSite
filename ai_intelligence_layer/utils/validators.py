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
    """Analyzes enriched telemetry data to extract trends and insights."""
    
    @staticmethod
    def calculate_tire_degradation_rate(telemetry: List[EnrichedTelemetryWebhook]) -> float:
        """
        Calculate tire degradation rate per lap.
        
        Args:
            telemetry: List of enriched telemetry records
            
        Returns:
            Rate of tire degradation per lap (0.0 to 1.0)
        """
        if len(telemetry) < 2:
            return 0.0
        
        # Sort by lap (ascending)
        sorted_telemetry = sorted(telemetry, key=lambda x: x.lap)
        
        # Calculate rate of change
        first = sorted_telemetry[0]
        last = sorted_telemetry[-1]
        
        lap_diff = last.lap - first.lap
        if lap_diff == 0:
            return 0.0
        
        deg_diff = last.tire_degradation_index - first.tire_degradation_index
        rate = deg_diff / lap_diff
        
        return max(0.0, rate)  # Ensure non-negative
    
    @staticmethod
    def calculate_aero_efficiency_avg(telemetry: List[EnrichedTelemetryWebhook]) -> float:
        """
        Calculate average aero efficiency.
        
        Args:
            telemetry: List of enriched telemetry records
            
        Returns:
            Average aero efficiency (0.0 to 1.0)
        """
        if not telemetry:
            return 0.0
        
        total = sum(t.aero_efficiency for t in telemetry)
        return total / len(telemetry)
    
    @staticmethod
    def analyze_ers_pattern(telemetry: List[EnrichedTelemetryWebhook]) -> str:
        """
        Analyze ERS charge pattern.
        
        Args:
            telemetry: List of enriched telemetry records
            
        Returns:
            Pattern description: "charging", "stable", "depleting"
        """
        if len(telemetry) < 2:
            return "stable"
        
        # Sort by lap
        sorted_telemetry = sorted(telemetry, key=lambda x: x.lap)
        
        # Look at recent trend
        recent = sorted_telemetry[-3:] if len(sorted_telemetry) >= 3 else sorted_telemetry
        
        if len(recent) < 2:
            return "stable"
        
        # Calculate average change
        total_change = 0.0
        for i in range(1, len(recent)):
            total_change += recent[i].ers_charge - recent[i-1].ers_charge
        
        avg_change = total_change / (len(recent) - 1)
        
        if avg_change > 0.05:
            return "charging"
        elif avg_change < -0.05:
            return "depleting"
        else:
            return "stable"
    
    @staticmethod
    def is_fuel_critical(telemetry: List[EnrichedTelemetryWebhook]) -> bool:
        """
        Check if fuel situation is critical.
        
        Args:
            telemetry: List of enriched telemetry records
            
        Returns:
            True if fuel optimization score is below 0.7
        """
        if not telemetry:
            return False
        
        # Check most recent telemetry
        latest = max(telemetry, key=lambda x: x.lap)
        return latest.fuel_optimization_score < 0.7
    
    @staticmethod
    def assess_driver_form(telemetry: List[EnrichedTelemetryWebhook]) -> str:
        """
        Assess driver consistency form.
        
        Args:
            telemetry: List of enriched telemetry records
            
        Returns:
            Form description: "excellent", "good", "inconsistent"
        """
        if not telemetry:
            return "good"
        
        # Get average consistency
        avg_consistency = sum(t.driver_consistency for t in telemetry) / len(telemetry)
        
        if avg_consistency >= 0.85:
            return "excellent"
        elif avg_consistency >= 0.75:
            return "good"
        else:
            return "inconsistent"
    
    @staticmethod
    def project_tire_cliff(
        telemetry: List[EnrichedTelemetryWebhook],
        current_lap: int
    ) -> int:
        """
        Project when tire degradation will hit 0.85 (performance cliff).
        
        Args:
            telemetry: List of enriched telemetry records
            current_lap: Current lap number
            
        Returns:
            Projected lap number when cliff will be reached
        """
        if not telemetry:
            return current_lap + 20  # Default assumption
        
        # Get current degradation and rate
        latest = max(telemetry, key=lambda x: x.lap)
        current_deg = latest.tire_degradation_index
        
        if current_deg >= 0.85:
            return current_lap  # Already at cliff
        
        # Calculate rate
        rate = TelemetryAnalyzer.calculate_tire_degradation_rate(telemetry)
        
        if rate <= 0:
            return current_lap + 50  # Not degrading, far future
        
        # Project laps until 0.85
        laps_until_cliff = (0.85 - current_deg) / rate
        projected_lap = current_lap + int(laps_until_cliff)
        
        return projected_lap
    
    @staticmethod
    def generate_telemetry_summary(telemetry: List[EnrichedTelemetryWebhook]) -> str:
        """
        Generate human-readable summary of telemetry trends.
        
        Args:
            telemetry: List of enriched telemetry records
            
        Returns:
            Summary string
        """
        if not telemetry:
            return "No telemetry data available."
        
        tire_rate = TelemetryAnalyzer.calculate_tire_degradation_rate(telemetry)
        aero_avg = TelemetryAnalyzer.calculate_aero_efficiency_avg(telemetry)
        ers_pattern = TelemetryAnalyzer.analyze_ers_pattern(telemetry)
        fuel_critical = TelemetryAnalyzer.is_fuel_critical(telemetry)
        driver_form = TelemetryAnalyzer.assess_driver_form(telemetry)
        
        latest = max(telemetry, key=lambda x: x.lap)
        
        summary = f"""Telemetry Analysis (Last {len(telemetry)} laps):
- Tire degradation: {latest.tire_degradation_index:.2f} index, increasing at {tire_rate:.3f}/lap
- Aero efficiency: {aero_avg:.2f} average
- ERS: {latest.ers_charge:.2f} charge, {ers_pattern}
- Fuel: {latest.fuel_optimization_score:.2f} score, {'CRITICAL' if fuel_critical else 'OK'}
- Driver form: {driver_form} ({latest.driver_consistency:.2f} consistency)
- Weather impact: {latest.weather_impact}"""
        
        return summary
