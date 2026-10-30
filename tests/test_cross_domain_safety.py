import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from safety_fixtures import safety_fixture
from services.safety_state import SafetyState
from domains.energy_comfort.control import run_energy_control
from domains.home_security.integration import monitor_security_workflow
from domains.smart_home_control import default_device_states
from domains.elderly_safety.context import collect_context
from simulation.devices import SimulatedDeviceTool
from simulation.security_scenarios import make_security_scenario
from simulation.external_warning_scenarios import make_warning_scenario
from simulation.elderly_scenarios import make_fall_scenario
from simulation.energy_comfort_demo import example_contexts, make_energy_comfort_event


class CrossDomainSafetyTests(unittest.TestCase):
    def event(self):
        return make_energy_comfort_event(example_contexts()["adjustment_needed"])

    def security(self, scenario, *, warning=False):
        with TemporaryDirectory() as folder:
            event = make_warning_scenario(scenario) if warning else make_security_scenario(scenario)
            return monitor_security_workflow(event, record_path=Path(folder) / "security.jsonl").workflow

    def test_clear_real_domain_results_allow_energy_but_missing_or_stale_block(self):
        safety = safety_fixture()
        self.assertTrue(safety.snapshot()["clear"])
        self.assertFalse(SafetyState().snapshot()["clear"])
        self.assertFalse(safety.snapshot(now=datetime.now(timezone.utc) + timedelta(seconds=301))["clear"])
        safety.invalidate("home_security")
        result = run_energy_control(self.event(), approved=True, safety_state=safety)
        self.assertEqual(result.planned, 0)

    def test_medium_confirmation_and_high_hazard_block(self):
        for case in ("unusual_door", "smoke", "gas", "suspected_intrusion"):
            with self.subTest(case=case):
                safety = safety_fixture()
                safety.observe(self.security(case))
                result = run_energy_control(self.event(), approved=True, safety_state=safety)
                self.assertEqual(result.workflow.action_results, ())

    def test_normal_domain_reassessment_can_restore_clearance(self):
        safety = safety_fixture(blocked=True)
        self.assertFalse(safety.snapshot()["clear"])
        safety.observe(self.security("normal"))
        self.assertTrue(safety.snapshot()["clear"])

    def test_active_warning_cannot_be_cleared_by_unrelated_or_invalid_warning(self):
        safety = safety_fixture()
        warning = self.security("relevant_earthquake", warning=True)
        safety.observe(warning)
        safety.observe(self.security("irrelevant_flood", warning=True))
        safety.observe(self.security("invalid_source", warning=True))
        safety.observe(self.security("normal"))
        self.assertFalse(safety.snapshot()["clear"])
        self.assertEqual(run_energy_control(self.event(), approved=True, safety_state=safety).planned, 0)

    def test_safety_change_between_commands_stops_remaining_device_dispatch(self):
        safety = safety_fixture()
        class ChangingTool(SimulatedDeviceTool):
            def dispatch(self, request):
                result = super().dispatch(request)
                safety.invalidate("elderly_safety")
                return result
        tool = ChangingTool(default_device_states())
        result = run_energy_control(self.event(), approved=True, safety_state=safety, device_tool=tool)
        self.assertEqual(tool.dispatch_count, 1)
        self.assertEqual(result.workflow.outcome, "PARTIAL")
        self.assertEqual(tool.states["living-room-ac"], default_device_states()["living-room-ac"])

    def test_fresh_scenario_keeps_explicit_simulated_night_context(self):
        event = make_fall_scenario("medium_night_uplift")
        age = datetime.now(timezone.utc) - datetime.fromisoformat(event.timestamp)
        self.assertLess(age.total_seconds(), 5)
        self.assertEqual(collect_context(event).time_of_day, "night")
