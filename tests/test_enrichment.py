import unittest

from hpcsim.enrichment import Enricher


class TestEnrichment(unittest.TestCase):
    def test_basic_ranges(self):
        e = Enricher()
        sample = {
            "lap": 1,
            "speed": 250,
            "throttle": 0.8,
            "brake": 0.1,
            "tire_compound": "medium",
            "fuel_level": 0.6,
            "ers": 0.5,
            "track_temp": 35,
            "rain_probability": 0.1,
        }
        out = e.enrich(sample)
        self.assertIn("aero_efficiency", out)
        self.assertTrue(0.0 <= out["aero_efficiency"] <= 1.0)
        self.assertTrue(0.0 <= out["tire_degradation_index"] <= 1.0)
        self.assertTrue(0.0 <= out["ers_charge"] <= 1.0)
        self.assertTrue(0.0 <= out["fuel_optimization_score"] <= 1.0)
        self.assertTrue(0.0 <= out["driver_consistency"] <= 1.0)
        self.assertIn(out["weather_impact"], {"low", "medium", "high"})

    def test_stateful_wear_increases(self):
        e = Enricher()
        prev = 0.0
        for lap in range(1, 6):
            out = e.enrich({
                "lap": lap,
                "speed": 260,
                "throttle": 0.9,
                "brake": 0.05,
                "tire_compound": "soft",
                "fuel_level": 0.7,
            })
            self.assertGreaterEqual(out["tire_degradation_index"], prev)
            prev = out["tire_degradation_index"]
    
    def test_enrich_with_context(self):
        """Test the new enrich_with_context method that outputs race context."""
        e = Enricher()
        sample = {
            "lap": 10,
            "speed": 280,
            "throttle": 0.85,
            "brake": 0.05,
            "tire_compound": "medium",
            "fuel_level": 0.7,
            "track_temp": 42.5,
            "total_laps": 51,
            "track_name": "Monza",
            "driver_name": "Alonso",
            "current_position": 5,
            "tire_life_laps": 8,
            "rainfall": False,
        }
        
        result = e.enrich_with_context(sample)
        
        # Verify structure
        self.assertIn("enriched_telemetry", result)
        self.assertIn("race_context", result)
        
        # Verify enriched telemetry
        enriched = result["enriched_telemetry"]
        self.assertEqual(enriched["lap"], 10)
        self.assertTrue(0.0 <= enriched["aero_efficiency"] <= 1.0)
        self.assertTrue(0.0 <= enriched["tire_degradation_index"] <= 1.0)
        self.assertTrue(0.0 <= enriched["ers_charge"] <= 1.0)
        self.assertTrue(0.0 <= enriched["fuel_optimization_score"] <= 1.0)
        self.assertTrue(0.0 <= enriched["driver_consistency"] <= 1.0)
        self.assertIn(enriched["weather_impact"], {"low", "medium", "high"})
        
        # Verify race context
        context = result["race_context"]
        self.assertIn("race_info", context)
        self.assertIn("driver_state", context)
        self.assertIn("competitors", context)
        
        # Verify race_info
        race_info = context["race_info"]
        self.assertEqual(race_info["track_name"], "Monza")
        self.assertEqual(race_info["total_laps"], 51)
        self.assertEqual(race_info["current_lap"], 10)
        self.assertEqual(race_info["weather_condition"], "Dry")
        self.assertEqual(race_info["track_temp_celsius"], 42.5)
        
        # Verify driver_state
        driver_state = context["driver_state"]
        self.assertEqual(driver_state["driver_name"], "Alonso")
        self.assertEqual(driver_state["current_position"], 5)
        self.assertEqual(driver_state["current_tire_compound"], "medium")
        self.assertEqual(driver_state["tire_age_laps"], 8)
        self.assertEqual(driver_state["fuel_remaining_percent"], 70.0)
        
        # Verify competitors
        competitors = context["competitors"]
        self.assertIsInstance(competitors, list)
        self.assertGreater(len(competitors), 0)
        for comp in competitors:
            self.assertIn("position", comp)
            self.assertIn("driver", comp)
            self.assertIn("tire_compound", comp)
            self.assertIn("tire_age_laps", comp)
            self.assertIn("gap_seconds", comp)
            self.assertNotEqual(comp["position"], 5)  # Not same as driver position


if __name__ == "__main__":
    unittest.main()
