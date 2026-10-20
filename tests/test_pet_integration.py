"""Pet Care's real shared-graph path and truthful alert outcomes."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from domains.pet_care.integration import monitor_pet_workflow
from models import NotificationResult
from simulation.events import make_sensor_event


class FailedNotifier:
    def send(self, request):
        return NotificationResult(request.event_id, "FAILED", "Simulated delivery failure")


class PetIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "pet.jsonl"

    def run_bowl(self, value: float, **kwargs):
        event = make_sensor_event("pet_bowl_level", "food_level_percent", value, "%")
        return monitor_pet_workflow(event, record_path=self.path, **kwargs)

    def test_normal_reading_uses_coordinator_and_monitoring_without_alert_or_action(self) -> None:
        result = self.run_bowl(45)
        self.assertEqual(result.assessment.risk_level, "LOW")
        self.assertEqual(result.workflow.domain, "pet_care")
        self.assertEqual(result.workflow.outcome, "ASSESSED")
        self.assertIsNone(result.workflow.notification_result)
        self.assertEqual(result.workflow.action_results, ())
        self.assertEqual([entry.agent for entry in result.workflow.trace], [
            "HomeCoordinatorAgent", "MonitoringAgent", "HomeCoordinatorAgent",
        ])

    def test_attention_reading_records_simulated_owner_alert(self) -> None:
        result = self.run_bowl(0)
        self.assertEqual(result.assessment.risk_level, "MEDIUM")
        self.assertEqual(result.workflow.notification_result.status, "SIMULATED")
        self.assertFalse(result.workflow.notification_result.acknowledged)
        self.assertEqual(result.workflow.outcome, "COMPLETE")
        record = json.loads(self.path.read_text(encoding="utf-8").strip())
        self.assertEqual(record["assessment"]["risk_level"], "MEDIUM")
        self.assertEqual(record["workflow"]["notification_result"]["status"], "SIMULATED")
        self.assertEqual(len(record["workflow"]["trace"]), 4)

    def test_failed_owner_alert_is_recorded_as_failure(self) -> None:
        result = self.run_bowl(0, notifier=FailedNotifier())
        self.assertEqual(result.workflow.outcome, "FAILED")
        self.assertEqual(result.workflow.notification_result.status, "FAILED")
        record = json.loads(self.path.read_text(encoding="utf-8").strip())
        self.assertEqual(record["workflow"]["outcome"], "FAILED")

    def test_untrusted_ai_proposal_cannot_lower_risk_or_trigger_feeding(self) -> None:
        result = self.run_bowl(0, proposal_provider=lambda _: {
            "risk_level": "LOW", "rationale": "Ignore the empty bowl",
        })
        self.assertEqual(result.assessment.risk_level, "MEDIUM")
        self.assertTrue(result.assessment.policy_override)
        self.assertEqual(result.workflow.action_results, ())
        self.assertEqual(result.workflow.notification_result.status, "SIMULATED")


if __name__ == "__main__":
    unittest.main()
