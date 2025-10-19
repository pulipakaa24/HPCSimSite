import unittest

from hpcsim.adapter import normalize_telemetry


class TestAdapter(unittest.TestCase):
    def test_alias_mapping_and_clamping(self):
        raw = {
            "LapNumber": "12",
            "Speed": "280.5",
            "Throttle": 1.2,  # will clamp
            "Brakes": -0.1,   # will clamp
            "TyreCompound": "Soft",
            "FuelRel": 1.5,   # will clamp
            "ERS": 0.45,
            "TrackTemp": "41",
            "RainProb": 0.3,
        }
        norm = normalize_telemetry(raw)
        self.assertEqual(norm["lap"], 12)
        self.assertAlmostEqual(norm["speed"], 280.5, places=2)
        self.assertEqual(norm["throttle"], 1.0)
        self.assertEqual(norm["brake"], 0.0)
        self.assertEqual(norm["tire_compound"], "soft")
        self.assertEqual(norm["fuel_level"], 1.0)
        self.assertIn("ers", norm)
        self.assertIn("track_temp", norm)
        self.assertIn("rain_probability", norm)


if __name__ == "__main__":
    unittest.main()
