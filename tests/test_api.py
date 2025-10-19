import unittest

from fastapi.testclient import TestClient

from hpcsim.api import app


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_ingest_and_list(self):
        payload = {
            "lap": 1,
            "speed": 250,
            "throttle": 0.8,
            "brake": 0.1,
            "tire_compound": "medium",
            "fuel_level": 0.6,
        }
        r = self.client.post("/ingest/telemetry", json=payload)
        self.assertEqual(r.status_code, 200)
        enriched = r.json()
        self.assertIn("aero_efficiency", enriched)

        list_r = self.client.get("/enriched", params={"limit": 5})
        self.assertEqual(list_r.status_code, 200)
        data = list_r.json()
        self.assertTrue(isinstance(data, list) and len(data) >= 1)

    def test_post_enriched(self):
        enriched = {
            "lap": 99,
            "aero_efficiency": 0.8,
            "tire_degradation_index": 0.5,
            "ers_charge": 0.6,
            "fuel_optimization_score": 0.9,
            "driver_consistency": 0.95,
            "weather_impact": "low",
        }
        r = self.client.post("/enriched", json=enriched)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["lap"], 99)


if __name__ == "__main__":
    unittest.main()
