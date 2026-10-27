"""Elderly Safety through the shared SmartHomeWorkflow (requires langgraph).

Success, failure and fallback paths: HIGH complete, MEDIUM blocked pending
confirmation, offline light, notification adapter failure, event-ID trace,
coexistence with Pet Care in one registry.
"""

from __future__ import annotations

import unittest

from agents.graph import SmartHomeWorkflow
from domains.elderly_safety import ElderlySafetyHandler, default_devices
from domains.pet_care.integration import PetCareHandler
from models import NotificationRequest, NotificationResult
from simulation.devices import SimulatedDeviceTool
from simulation.elderly_scenarios import make_fall_scenario
from simulation.events import make_sensor_event
from simulation.notifications import SimulatedNotificationService


class FailingNotifier:
    def send(self, request: NotificationRequest) -> NotificationResult:
        raise ConnectionError("simulated transport down")


def run(scenario: str, *, offline: bool = False, notifier=None):
    devices = SimulatedDeviceTool(default_devices())
    if offline:
        devices.offline.update(devices.states)
    handler = ElderlySafetyHandler()
    workflow = SmartHomeWorkflow([handler], devices, notifier=notifier or SimulatedNotificationService())
    return workflow.run(make_fall_scenario(scenario)), handler, devices


class ElderlyWorkflowTests(unittest.TestCase):
    def test_high_fall_lights_room_and_alerts_caregiver(self):
        result, _, devices = run("high_floor")
        self.assertEqual(result.outcome, "COMPLETE")
        self.assertEqual(result.assessment.risk_level, "HIGH")
        self.assertTrue(result.action_results[0].success)
        self.assertEqual(devices.states["bathroom_light"]["power"], "on")
        self.assertEqual(result.notification_result.status, "SIMULATED")
        self.assertFalse(result.notification_result.acknowledged)

    def test_medium_pauses_for_resident_confirmation(self):
        result, handler, devices = run("medium_wait")
        self.assertEqual(result.outcome, "AWAITING_CONFIRMATION")
        self.assertIsNotNone(result.pending_confirmation)
        self.assertTrue(result.assessment.requires_human_review)
        self.assertEqual(result.action_results, ())
        self.assertIsNone(result.notification_result)
        self.assertEqual(devices.dispatch_count, 0)
        self.assertTrue(handler.fall_assessment.requires_confirmation)

    def test_low_without_model_becomes_medium_fallback(self):
        result, handler, _ = run("low_dropped_object")
        self.assertEqual(result.assessment.risk_level, "MEDIUM")
        self.assertTrue(result.assessment.fallback_used)
        self.assertEqual(result.outcome, "AWAITING_CONFIRMATION")  # MEDIUM asks the resident

    def test_offline_light_is_reported_failed_not_hidden(self):
        result, _, _ = run("high_floor", offline=True)
        self.assertEqual(result.outcome, "FAILED")
        r = result.action_results[0]
        self.assertFalse(r.accepted)
        self.assertFalse(r.verified)
        self.assertIn("offline", r.error.lower())
        # The caregiver is still alerted even though the light failed.
        self.assertEqual(result.notification_result.status, "SIMULATED")

    def test_notification_failure_is_partial(self):
        result, _, devices = run("high_floor", notifier=FailingNotifier())
        self.assertEqual(result.notification_result.status, "FAILED")
        self.assertEqual(result.outcome, "PARTIAL")  # light verified, alert failed
        self.assertEqual(devices.states["bathroom_light"]["power"], "on")

    def test_trace_preserves_event_id_and_names_all_three_agents(self):
        result, _, _ = run("high_floor")
        self.assertTrue(all(e.event_id == result.event.event_id for e in result.trace))
        self.assertEqual({e.agent for e in result.trace}, {"HomeCoordinatorAgent", "MonitoringAgent", "DeviceAutomationAgent"})

    def test_coexists_with_pet_care_in_one_registry(self):
        workflow = SmartHomeWorkflow([ElderlySafetyHandler(), PetCareHandler()], SimulatedDeviceTool(default_devices()),
                                     notifier=SimulatedNotificationService())
        fall = workflow.run(make_fall_scenario("high_floor"))
        pet = workflow.run(make_sensor_event("pet_bowl_level", "food_level_percent", 0, "%"))
        self.assertEqual((fall.domain, pet.domain), ("elderly_safety", "pet_care"))


if __name__ == "__main__":
    unittest.main()
