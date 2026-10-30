"""SCRUM-32 acceptance criteria mapped to repository tests (main integration)."""

from __future__ import annotations

import unittest

from domains.energy_comfort.control import run_energy_control
from domains.energy_comfort.integration import evaluate_formal_control_attempt
from domains.energy_comfort.post_action import assess_post_action_environment
from domains.smart_home_control import default_device_states
from safety_fixtures import safety_fixture
from simulation.devices import SimulatedDeviceTool
from simulation.energy_comfort_demo import example_contexts, make_energy_comfort_event


class Scrum32AcceptanceTests(unittest.TestCase):
    """Jira SCRUM-32 AC1–AC3 evidence on explicit simulation + formal pending path."""

    def hot_event(self):
        return make_energy_comfort_event(example_contexts()["adjustment_needed"])

    def test_ac1_safe_plan_when_adjustment_needed_with_approval_and_clear_safety(self) -> None:
        tool = SimulatedDeviceTool(default_device_states())
        result = run_energy_control(
            self.hot_event(), approved=True, safety_state=safety_fixture(), device_tool=tool,
        )
        self.assertGreaterEqual(result.planned, 1)
        self.assertEqual(len(result.workflow.action_results), result.planned)
        self.assertTrue(any(r.success for r in result.workflow.action_results))

    def test_ac1_formal_integration_still_creates_no_action_request(self) -> None:
        outcome = evaluate_formal_control_attempt(self.hot_event())
        self.assertEqual(outcome.action_requests_created, 0)
        self.assertFalse(outcome.dispatched)
        self.assertEqual(outcome.workflow.action_results, ())

    def test_ac2_cross_domain_safety_blocks_before_dispatch(self) -> None:
        tool = SimulatedDeviceTool(default_device_states())
        result = run_energy_control(
            self.hot_event(), approved=True, safety_state=safety_fixture(blocked=True), device_tool=tool,
        )
        self.assertEqual(result.planned, 0)
        self.assertEqual(tool.dispatch_count, 0)
        self.assertEqual(result.workflow.action_results, ())

    def test_ac3_post_action_environment_unknown_not_measured_after_verified_devices(self) -> None:
        tool = SimulatedDeviceTool(default_device_states())
        result = run_energy_control(
            self.hot_event(), approved=True, safety_state=safety_fixture(), device_tool=tool,
        )
        obs = result.post_action_environment
        self.assertEqual(obs.status, "UNKNOWN_NOT_MEASURED")
        self.assertEqual(obs.source, "no_independent_environment_sensor_feed")
        self.assertNotIn("22", obs.detail)  # do not echo pre-action temperature as measurement
        replay = assess_post_action_environment(
            workflow=result.workflow, planned_actions=result.planned,
        )
        self.assertEqual(replay.status, "UNKNOWN_NOT_MEASURED")

    def test_ac3_partial_offline_device_reports_bounded_failure_without_false_complete(self) -> None:
        tool = SimulatedDeviceTool(default_device_states())
        tool.offline.add("living-room-ac")
        result = run_energy_control(
            self.hot_event(), approved=True, safety_state=safety_fixture(), device_tool=tool,
        )
        self.assertEqual(result.workflow.outcome, "PARTIAL")
        self.assertTrue(result.workflow.action_results[0].success)
        self.assertFalse(result.workflow.action_results[1].success)
        self.assertGreaterEqual(result.workflow.action_results[1].attempts, 2)


if __name__ == "__main__":
    unittest.main()
