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


if __name__ == "__main__":
    unittest.main()
