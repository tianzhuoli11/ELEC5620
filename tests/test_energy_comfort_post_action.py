"""Post-action environment observation boundary tests."""

from __future__ import annotations

import unittest
from dataclasses import replace

from domains.energy_comfort.post_action import assess_post_action_environment
from models import ActionResult
from simulation.energy_comfort_demo import example_contexts, make_energy_comfort_event
from domains.energy_comfort.integration import monitor_energy_comfort_workflow


class PostActionEnvironmentTests(unittest.TestCase):
    def test_no_execution_yields_not_applicable_unknown(self) -> None:
        outcome = monitor_energy_comfort_workflow(
            make_energy_comfort_event(example_contexts()["no_adjustment"]),
        )
        obs = assess_post_action_environment(workflow=outcome.workflow, planned_actions=0)
        self.assertEqual(obs.status, "UNKNOWN_NOT_MEASURED")
        self.assertEqual(obs.source, "not_applicable_no_device_execution")

    def test_verified_devices_without_probe_still_unknown_environment(self) -> None:
        outcome = monitor_energy_comfort_workflow(
            make_energy_comfort_event(example_contexts()["adjustment_needed"]),
        )
        event_id = outcome.workflow.event.event_id
        result = ActionResult(
            event_id, "bedroom-light", "set_state",
            accepted=True, verified=True, returned_state={"power": "off"},
        )
        workflow = replace(outcome.workflow, action_result=result, action_results=(result,))
        obs = assess_post_action_environment(workflow=workflow, planned_actions=1)
        self.assertEqual(obs.status, "UNKNOWN_NOT_MEASURED")
        self.assertEqual(obs.source, "no_independent_environment_sensor_feed")

    def test_optional_probe_can_supply_measured_readings(self) -> None:
        outcome = monitor_energy_comfort_workflow(
            make_energy_comfort_event(example_contexts()["adjustment_needed"]),
        )
        event_id = outcome.workflow.event.event_id
        result = ActionResult(
            event_id, "bedroom-light", "set_state",
            accepted=True, verified=True, returned_state={"power": "off"},
        )
        workflow = replace(outcome.workflow, action_result=result, action_results=(result,))

        def probe(_workflow):
            return ({"reading_type": "indoor_temperature", "value": 23.0, "unit": "C"},)

        obs = assess_post_action_environment(
            workflow=workflow, planned_actions=1, environment_probe=probe,
        )
        self.assertEqual(obs.status, "MEASURED")
        self.assertEqual(obs.source, "independent_environment_probe")
        self.assertEqual(len(obs.readings), 1)


if __name__ == "__main__":
    unittest.main()
