"""AR-03 / UC-03 acceptance and failure scenarios for final integration."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from domains.pet_care.feeder import SimulatedPetFeederTool
from domains.pet_care.integration import monitor_pet_workflow
from models import NotificationResult
from simulation.events import make_sensor_event


class FailedNotifier:
    def send(self, request):
        return NotificationResult(request.event_id, "FAILED", "Simulated delivery failure")


class PetSprint2AcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "pet.jsonl"

    def bowl(self, level=0):
        return make_sensor_event("pet_bowl_level", "food_level_percent", level, "%")

    def run_pet(self, event=None, **kwargs):
        return monitor_pet_workflow(event or self.bowl(), record_path=self.path, **kwargs)

    def last_record(self):
        return json.loads(self.path.read_text(encoding="utf-8").splitlines()[-1])

    def test_core_monitoring_and_alert_complete_without_feeder(self) -> None:
        result = self.run_pet()
        self.assertEqual(result.assessment.risk_level, "MEDIUM")
        self.assertEqual(result.workflow.notification_result.status, "SIMULATED")
        self.assertEqual(result.workflow.action_results, ())
        self.assertEqual(result.feeding.status, "NOT_REQUESTED")
        self.assertEqual(self.last_record()["workflow"]["outcome"], "COMPLETE")

    def test_disabled_feeding_does_not_block_core_notification(self) -> None:
        feeder = SimulatedPetFeederTool()
        result = self.run_pet(feeding_goal={"portion_grams": 20}, feeder=feeder)
        self.assertEqual(result.feeding.status, "DISABLED")
        self.assertEqual(feeder.dispatch_count, 0)
        self.assertEqual(result.workflow.notification_result.status, "SIMULATED")
        self.assertEqual(result.workflow.outcome, "COMPLETE")

    def test_approved_simulated_feed_is_dispatched_once_and_verified(self) -> None:
        feeder = SimulatedPetFeederTool()
        result = self.run_pet(feeding_goal={"portion_grams": 20}, feeding_enabled=True, feeder=feeder)
        self.assertEqual(result.feeding.status, "VERIFIED")
        self.assertEqual(feeder.dispatch_count, 1)
        self.assertEqual(feeder.read_state("pet-feeder")["dispense_count"], 1)
        self.assertTrue(result.workflow.action_results[0].success)
        self.assertEqual(result.workflow.notification_result.status, "SIMULATED")
        self.assertEqual(self.last_record()["feeding"]["status"], "VERIFIED")

    def test_invalid_or_unsafe_goal_is_rejected_before_dispatch(self) -> None:
        for goal in ({"portion_grams": True}, {"portion_grams": 51}, {"portion_grams": 20, "extra": True}):
            with self.subTest(goal=goal):
                feeder = SimulatedPetFeederTool()
                result = self.run_pet(feeding_goal=goal, feeding_enabled=True, feeder=feeder)
                self.assertEqual(result.feeding.status, "REJECTED")
                self.assertEqual(feeder.dispatch_count, 0)
                self.assertEqual(result.workflow.notification_result.status, "SIMULATED")
        feeder = SimulatedPetFeederTool()
        result = self.run_pet(self.bowl(45), feeding_goal={"portion_grams": 20}, feeding_enabled=True, feeder=feeder)
        self.assertEqual(result.feeding.status, "REJECTED")
        self.assertEqual(feeder.dispatch_count, 0)

    def test_offline_feeder_is_reported_without_dispatch_or_false_success(self) -> None:
        feeder = SimulatedPetFeederTool(available=False)
        result = self.run_pet(feeding_goal={"portion_grams": 20}, feeding_enabled=True, feeder=feeder)
        self.assertEqual(result.feeding.status, "UNAVAILABLE")
        self.assertEqual(feeder.dispatch_count, 0)
        self.assertEqual(result.workflow.notification_result.status, "SIMULATED")
        self.assertEqual(self.last_record()["feeding"]["status"], "UNAVAILABLE")

    def test_unverified_feed_is_not_retried_or_reported_successful(self) -> None:
        feeder = SimulatedPetFeederTool(stale_readback=True)
        result = self.run_pet(feeding_goal={"portion_grams": 20}, feeding_enabled=True, feeder=feeder)
        self.assertEqual(result.feeding.status, "UNVERIFIED")
        self.assertEqual(feeder.dispatch_count, 1)
        self.assertEqual(result.workflow.notification_result.status, "SIMULATED")
        self.assertFalse(result.workflow.action_results[0].success)
        self.assertEqual(self.last_record()["feeding"]["status"], "UNVERIFIED")

    def test_same_event_cannot_dispense_twice(self) -> None:
        feeder = SimulatedPetFeederTool()
        event = self.bowl()
        first = self.run_pet(event, feeding_goal={"portion_grams": 20}, feeding_enabled=True, feeder=feeder)
        second = self.run_pet(event, feeding_goal={"portion_grams": 20}, feeding_enabled=True, feeder=feeder)
        self.assertEqual(first.feeding.status, "VERIFIED")
        self.assertEqual(second.feeding.status, "FAILED")
        self.assertEqual(feeder.read_state("pet-feeder")["dispense_count"], 1)

    def test_llm_timeout_keeps_rule_result_and_never_requests_feeding(self) -> None:
        def timeout(_):
            raise TimeoutError("model unavailable")

        result = self.run_pet(proposal_provider=timeout)
        self.assertTrue(result.assessment.fallback_used)
        self.assertEqual(result.assessment.risk_level, "MEDIUM")
        self.assertEqual(result.feeding.status, "NOT_REQUESTED")
        self.assertEqual(result.workflow.action_results, ())

    def test_notification_failure_and_verified_feed_are_reported_separately(self) -> None:
        feeder = SimulatedPetFeederTool()
        result = self.run_pet(feeding_goal={"portion_grams": 20}, feeding_enabled=True,
                              feeder=feeder, notifier=FailedNotifier())
        self.assertEqual(result.feeding.status, "VERIFIED")
        self.assertEqual(result.workflow.notification_result.status, "FAILED")
        self.assertEqual(result.workflow.outcome, "PARTIAL")
        self.assertEqual(self.last_record()["workflow"]["notification_result"]["status"], "FAILED")


if __name__ == "__main__":
    unittest.main()
