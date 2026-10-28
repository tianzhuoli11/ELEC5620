"""Regression checks for incorrect model proposals and simulated energy control."""
import unittest
from unittest.mock import Mock
from dataclasses import replace
from domains.energy_comfort.control import run_energy_control
from domains.smart_home_control import default_device_states, run_smart_home_control
from simulation.devices import SimulatedDeviceTool
from simulation.energy_comfort_demo import example_contexts, make_energy_comfort_event
from simulation.events import make_user_goal_event
from models import HomeContext, HomeEnvironment, UserPreference, EnergyProfile, DeviceObservation


class ReleaseControlTests(unittest.TestCase):
    def test_ai_cannot_reverse_explicit_positive_target(self):
        tool = SimulatedDeviceTool(default_device_states())
        result = run_smart_home_control(make_user_goal_event("Turn on the bedroom light"), device_tool=tool,
                    proposal_provider=lambda _: {"domain": "smart_home_control", "intent": "direct_control", "parameters": {"light_power": "off"}}, record_path=None)
        self.assertEqual(result.outcome, "COMPLETE")
        self.assertEqual(tool.states["bedroom-light"]["power"], "on")

    def hot_event(self):
        return make_energy_comfort_event(example_contexts()["adjustment_needed"])

    def test_negation_blocks_even_wrong_ai_before_provider_call(self):
        for text in ("Do not turn off the bedroom light", "Don't unlock the front door", "不要关灯", "Do not go to sleep", "Never switch my bedroom lamp off", "不需要关闭卧室照明"):
            with self.subTest(text=text):
                provider = Mock(return_value={"domain": "smart_home_control", "intent": "night_mode", "parameters": {}})
                tool = SimulatedDeviceTool(default_device_states())
                result = run_smart_home_control(make_user_goal_event(text), device_tool=tool, proposal_provider=provider, record_path=None)
                self.assertEqual(result.outcome, "CLARIFICATION_REQUIRED")
                self.assertEqual(tool.dispatch_count, 0)
                provider.assert_not_called()

    def test_hot_room_controls_and_verifies_curtain_and_ac(self):
        tool = SimulatedDeviceTool(default_device_states())
        result = run_energy_control(self.hot_event(), approved=True, safety_clear=True, device_tool=tool)
        self.assertEqual(result.workflow.outcome, "COMPLETE")
        self.assertEqual(result.planned, 2)
        self.assertTrue(all(r.success for r in result.workflow.action_results))
        self.assertEqual(tool.states["living-room-ac"]["temperature_c"], 24)
        self.assertEqual(tool.states["bedroom-curtain"]["position"], "closed")

    def test_missing_approval_or_safety_never_dispatches(self):
        for approval, safety in ((False, True), (True, None), (True, False)):
            tool = SimulatedDeviceTool(default_device_states())
            result = run_energy_control(self.hot_event(), approved=approval, safety_clear=safety, device_tool=tool)
            self.assertEqual(tool.dispatch_count, 0)
            self.assertEqual(result.planned, 0)

    def test_offline_ac_reports_partial_without_false_success(self):
        tool = SimulatedDeviceTool(default_device_states())
        tool.offline.add("living-room-ac")
        result = run_energy_control(self.hot_event(), approved=True, safety_clear=True, device_tool=tool)
        self.assertEqual(result.workflow.outcome, "PARTIAL")
        self.assertTrue(result.workflow.action_results[0].success)
        self.assertFalse(result.workflow.action_results[1].success)
        self.assertEqual(result.workflow.action_results[1].attempts, 2)

    def test_readback_mismatch_cannot_report_complete(self):
        class WrongState(SimulatedDeviceTool):
            def read_state(self, device_id):
                return {"power": "off"}
        result = run_energy_control(self.hot_event(), approved=True, safety_clear=True,
                                    device_tool=WrongState(default_device_states()))
        self.assertFalse(any(r.success for r in result.workflow.action_results))
        self.assertNotEqual(result.workflow.outcome, "COMPLETE")

    def test_unknown_context_and_comfort_ok_do_not_control(self):
        for context in (example_contexts()["insufficient_data"], example_contexts()["no_adjustment"]):
            result = run_energy_control(make_energy_comfort_event(context), approved=True, safety_clear=True)
            self.assertEqual(result.planned, 0)

    def test_cold_room_and_out_of_policy_preference(self):
        for minimum, expected in ((20, 1), (10, 0)):
            context = HomeContext(HomeEnvironment(5, True), UserPreference(minimum, 24), simulated=True)
            result = run_energy_control(make_energy_comfort_event(context), approved=True, safety_clear=True)
            self.assertEqual(result.planned, expected)

    def test_unoccupied_only_explicit_observed_bedroom_light_can_switch_off(self):
        for device, expected in (("bedroom-light", 1), ("siren", 0), ("bathroom_light", 0)):
            context = HomeContext(HomeEnvironment(22, False), None, EnergyProfile(900, 400),
                                  devices=(DeviceObservation(device, True, {"power": "on"}),), simulated=True)
            result = run_energy_control(make_energy_comfort_event(context), approved=True, safety_clear=True)
            self.assertEqual(result.planned, expected)

    def test_real_event_is_rejected(self):
        event = self.hot_event()
        event.context["energy_comfort"]["simulated"] = False
        with self.assertRaises(ValueError):
            run_energy_control(replace(event, simulated=False), approved=True, safety_clear=True)
