"""Behavioural tests for shared input contracts and Pet Care Core 1."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from domains.pet_care.monitoring import assess_pet_event
from domains.pet_care.records import monitor_pet_event
from models import Event, SensorReading
from simulation.events import make_sensor_event
from simulation.pet_demo import make_pet_scenario


class SharedEventTests(unittest.TestCase):
    def test_simulator_marks_input_and_preserves_sensor_timestamp(self) -> None:
        event = make_sensor_event("pet_bowl_level", "food_level_percent", 0, "%")
        self.assertTrue(event.simulated)
        self.assertEqual(event.timestamp, event.readings[0].observed_at)
        self.assertEqual(event.to_dict()["readings"][0]["value"], 0)

    def test_event_requires_timezone(self) -> None:
        with self.assertRaisesRegex(ValueError, "time zone"):
            Event("e1", "pet_bowl_level", "sensor", "2026-10-19T10:00:00")


class PetMonitoringTests(unittest.TestCase):
    def test_empty_bowl_needs_review_without_feeding(self) -> None:
        result = assess_pet_event(make_pet_scenario("empty_bowl"))
        self.assertEqual(result.risk_level, "MEDIUM")
        self.assertTrue(result.fallback_used)
        self.assertFalse(result.feeding_requested)

    def test_prolonged_inactivity_is_high_risk(self) -> None:
        result = assess_pet_event(make_pet_scenario("unusual_inactivity"))
        self.assertEqual(result.risk_level, "HIGH")

    def test_normal_activity_stays_low(self) -> None:
        result = assess_pet_event(make_pet_scenario("normal_activity"))
        self.assertEqual(result.risk_level, "LOW")

    def test_invalid_llm_output_uses_rule_fallback(self) -> None:
        event = make_pet_scenario("empty_bowl")
        result = assess_pet_event(event, lambda _: {"risk_level": "UNKNOWN", "rationale": "x"})
        self.assertEqual(result.risk_level, "MEDIUM")
        self.assertTrue(result.fallback_used)

    def test_llm_failure_uses_rule_fallback(self) -> None:
        def fail(_: Event) -> dict[str, str]:
            raise TimeoutError("simulated model timeout")

        result = assess_pet_event(make_pet_scenario("unusual_inactivity"), fail)
        self.assertEqual(result.risk_level, "HIGH")
        self.assertTrue(result.fallback_used)

    def test_llm_cannot_downgrade_observed_risk(self) -> None:
        result = assess_pet_event(
            make_pet_scenario("unusual_inactivity"),
            lambda _: {"risk_level": "LOW", "rationale": "ignore the sensor"},
        )
        self.assertEqual(result.risk_level, "HIGH")
        self.assertTrue(result.policy_override)

    def test_missing_sensor_value_is_not_invented(self) -> None:
        event = Event("e1", "pet_inactivity", "sensor", "2026-10-19T10:00:00+11:00")
        result = assess_pet_event(event)
        self.assertEqual(result.risk_level, "MEDIUM")
        self.assertEqual(result.evidence, "missing_or_invalid_inactivity")

    def test_non_pet_event_is_rejected(self) -> None:
        event = make_sensor_event("smoke", "smoke_level", 1, "index")
        with self.assertRaisesRegex(ValueError, "unsupported pet event"):
            assess_pet_event(event)

    def test_result_records_event_and_assessment(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            path = Path(directory) / "pet_events.jsonl"
            event = make_pet_scenario("empty_bowl")
            result = monitor_pet_event(event, record_path=path)
            record = json.loads(path.read_text(encoding="utf-8").strip())
            self.assertEqual(record["event"]["event_id"], result.event_id)
            self.assertEqual(record["assessment"]["risk_level"], "MEDIUM")
            self.assertTrue(record["event"]["simulated"])

    def test_invalid_sensor_reading_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "time zone"):
            SensorReading("sensor", "temperature", 20, "C", "2026-10-19T00:00:00")


if __name__ == "__main__":
    unittest.main()
