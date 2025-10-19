"""
Integration test for enrichment + AI intelligence layer workflow.
Tests the complete flow from raw telemetry to automatic strategy generation.
"""
import unittest
from unittest.mock import patch, MagicMock
import json

from hpcsim.enrichment import Enricher
from hpcsim.adapter import normalize_telemetry


class TestIntegration(unittest.TestCase):
    def test_pi_to_enrichment_flow(self):
        """Test the flow from Pi telemetry to enriched output with race context."""
        # Simulate raw telemetry from Pi (like simulate_pi_stream.py sends)
        raw_telemetry = {
            'lap_number': 15,
            'total_laps': 51,
            'speed': 285.5,
            'throttle': 88.0,  # Note: Pi might send as percentage
            'brake': False,
            'tire_compound': 'MEDIUM',
            'tire_life_laps': 12,
            'track_temperature': 42.5,
            'rainfall': False,
            'track_name': 'Monza',
            'driver_name': 'Alonso',
            'current_position': 5,
            'fuel_level': 0.65,
        }
        
        # Step 1: Normalize (adapter)
        normalized = normalize_telemetry(raw_telemetry)
        
        # Verify normalization
        self.assertEqual(normalized['lap'], 15)
        self.assertEqual(normalized['total_laps'], 51)
        self.assertEqual(normalized['tire_compound'], 'medium')
        self.assertEqual(normalized['track_name'], 'Monza')
        self.assertEqual(normalized['driver_name'], 'Alonso')
        
        # Step 2: Enrich with context
        enricher = Enricher()
        result = enricher.enrich_with_context(normalized)
        
        # Verify output structure
        self.assertIn('enriched_telemetry', result)
        self.assertIn('race_context', result)
        
        # Verify enriched telemetry
        enriched = result['enriched_telemetry']
        self.assertEqual(enriched['lap'], 15)
        self.assertIn('aero_efficiency', enriched)
        self.assertIn('tire_degradation_index', enriched)
        self.assertIn('ers_charge', enriched)
        self.assertIn('fuel_optimization_score', enriched)
        self.assertIn('driver_consistency', enriched)
        self.assertIn('weather_impact', enriched)
        
        # Verify race context structure matches AI layer expectations
        race_context = result['race_context']
        
        # race_info
        self.assertIn('race_info', race_context)
        race_info = race_context['race_info']
        self.assertEqual(race_info['track_name'], 'Monza')
        self.assertEqual(race_info['total_laps'], 51)
        self.assertEqual(race_info['current_lap'], 15)
        self.assertIn('weather_condition', race_info)
        self.assertIn('track_temp_celsius', race_info)
        
        # driver_state
        self.assertIn('driver_state', race_context)
        driver_state = race_context['driver_state']
        self.assertEqual(driver_state['driver_name'], 'Alonso')
        self.assertEqual(driver_state['current_position'], 5)
        self.assertIn('current_tire_compound', driver_state)
        self.assertIn('tire_age_laps', driver_state)
        self.assertIn('fuel_remaining_percent', driver_state)
        # Verify tire compound is normalized
        self.assertIn(driver_state['current_tire_compound'], 
                      ['soft', 'medium', 'hard', 'intermediate', 'wet'])
        
        # competitors
        self.assertIn('competitors', race_context)
        competitors = race_context['competitors']
        self.assertIsInstance(competitors, list)
        if competitors:
            comp = competitors[0]
            self.assertIn('position', comp)
            self.assertIn('driver', comp)
            self.assertIn('tire_compound', comp)
            self.assertIn('tire_age_laps', comp)
            self.assertIn('gap_seconds', comp)
    
    def test_webhook_payload_structure(self):
        """Verify the webhook payload structure sent to AI layer."""
        enricher = Enricher()
        
        telemetry = {
            'lap': 20,
            'speed': 290.0,
            'throttle': 0.92,
            'brake': 0.03,
            'tire_compound': 'soft',
            'fuel_level': 0.55,
            'track_temp': 38.0,
            'total_laps': 51,
            'track_name': 'Monza',
            'driver_name': 'Alonso',
            'current_position': 4,
            'tire_life_laps': 15,
            'rainfall': False,
        }
        
        result = enricher.enrich_with_context(telemetry)
        
        # This is the payload that will be sent via webhook to AI layer
        # AI layer expects: EnrichedTelemetryWithContext
        # which has enriched_telemetry and race_context
        
        # Verify it matches the expected schema
        self.assertIn('enriched_telemetry', result)
        self.assertIn('race_context', result)
        
        enriched_telem = result['enriched_telemetry']
        race_ctx = result['race_context']
        
        # Verify enriched_telemetry matches EnrichedTelemetryWebhook schema
        required_fields = ['lap', 'aero_efficiency', 'tire_degradation_index', 
                          'ers_charge', 'fuel_optimization_score', 
                          'driver_consistency', 'weather_impact']
        for field in required_fields:
            self.assertIn(field, enriched_telem, f"Missing field: {field}")
        
        # Verify race_context matches RaceContext schema
        self.assertIn('race_info', race_ctx)
        self.assertIn('driver_state', race_ctx)
        self.assertIn('competitors', race_ctx)
        
        # Verify nested structures
        race_info_fields = ['track_name', 'total_laps', 'current_lap', 
                           'weather_condition', 'track_temp_celsius']
        for field in race_info_fields:
            self.assertIn(field, race_ctx['race_info'], 
                         f"Missing race_info field: {field}")
        
        driver_state_fields = ['driver_name', 'current_position', 
                              'current_tire_compound', 'tire_age_laps', 
                              'fuel_remaining_percent']
        for field in driver_state_fields:
            self.assertIn(field, race_ctx['driver_state'], 
                         f"Missing driver_state field: {field}")
    
    def test_fuel_level_conversion(self):
        """Verify fuel level is correctly converted from 0-1 to 0-100."""
        enricher = Enricher()
        
        telemetry = {
            'lap': 5,
            'speed': 280.0,
            'throttle': 0.85,
            'brake': 0.0,
            'tire_compound': 'medium',
            'fuel_level': 0.75,  # 75% as decimal
            'total_laps': 50,
            'track_name': 'Test Track',
            'driver_name': 'Test Driver',
            'current_position': 10,
            'tire_life_laps': 5,
        }
        
        result = enricher.enrich_with_context(telemetry)
        
        # Verify fuel is converted to percentage
        fuel_percent = result['race_context']['driver_state']['fuel_remaining_percent']
        self.assertEqual(fuel_percent, 75.0)
        self.assertGreaterEqual(fuel_percent, 0.0)
        self.assertLessEqual(fuel_percent, 100.0)


if __name__ == '__main__':
    unittest.main()
