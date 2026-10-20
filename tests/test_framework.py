"""Behavior tests for the shared graph and integration boundaries."""

from __future__ import annotations

import unittest

from agents.graph import SmartHomeWorkflow
from models import ActionRequest, Event, GoalInterpretation, GoalPlan, MonitoringDecision, NotificationRequest, RiskAssessment
from simulation.devices import SimulatedDeviceTool
from simulation.events import make_sensor_event, make_user_goal_event
from simulation.framework_demo import DemoLightHandler, DemoNightModeHandler
from simulation.goals import DemoGoalInterpreter


class NoActionHandler:
    domain = "status"

    def supports(self, event: Event) -> bool:
        return event.event_type == "status_check"

    def assess(self, event: Event) -> MonitoringDecision:
        return MonitoringDecision(RiskAssessment(event.event_id, self.domain, "LOW", "No action needed", "Simulated status"))


class ReviewHandler(DemoLightHandler):
    domain = "review_demo"

    def assess(self, event: Event) -> MonitoringDecision:
        decision = super().assess(event)
        return MonitoringDecision(
            RiskAssessment(event.event_id, self.domain, "HIGH", "Manual review required", "Simulated rule", requires_human_review=True),
            decision.action_request,
        )


class WrongIdHandler(DemoLightHandler):
    domain = "wrong_id"

    def assess(self, event: Event) -> MonitoringDecision:
        return MonitoringDecision(RiskAssessment("wrong", self.domain, "LOW", "Bad response", "Test"))


class HumanAuthorizationHandler(DemoLightHandler):
    domain = "human_demo"

    def assess(self, event: Event) -> MonitoringDecision:
        return MonitoringDecision(
            RiskAssessment(event.event_id, self.domain, "LOW", "Request awaits review", "Test"),
            ActionRequest(event.event_id, "demo-light", "set_state", {"power": "on"}, {"power": "on"}, "HUMAN", True),
        )


class WrongReadbackDevice(SimulatedDeviceTool):
    def read_state(self, device_id: str) -> dict:
        return {"power": "off"}


class FailedReadbackDevice(SimulatedDeviceTool):
    def read_state(self, device_id: str) -> dict:
        raise ConnectionError("test outage")


class NoticeHandler(NoActionHandler):
    domain = "notice"

    def assess(self, event: Event) -> MonitoringDecision:
        decision = super().assess(event)
        return MonitoringDecision(
            RiskAssessment(event.event_id, self.domain, "LOW", "Notice", "Test"),
            notification_request=NotificationRequest(event.event_id, "demo-contact", "Simulated status", True),
        )


class FrameworkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.event = make_sensor_event("demo_light_request", "power_request", "on", "state")
        self.device = SimulatedDeviceTool({"demo-light": {"power": "off"}})

    def test_three_agent_path_verifies_simulated_state(self) -> None:
        result = SmartHomeWorkflow([DemoLightHandler()], self.device).run(self.event)
        self.assertEqual(result.domain, "framework_demo")
        self.assertTrue(result.action_result.success)
        self.assertEqual(result.action_result.returned_state["power"], "on")
        self.assertEqual([entry.agent for entry in result.trace], [
            "HomeCoordinatorAgent", "MonitoringAgent", "DeviceAutomationAgent", "HomeCoordinatorAgent",
        ])
        self.assertTrue(result.event.simulated)

    def test_no_action_path_skips_device_tool(self) -> None:
        event = make_sensor_event("status_check", "status", "ok", "state")
        result = SmartHomeWorkflow([NoActionHandler()], self.device).run(event)
        self.assertIsNone(result.action_result)
        self.assertEqual(self.device.dispatch_count, 0)

    def test_unsupported_event_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected one handler"):
            SmartHomeWorkflow([DemoLightHandler()], self.device).run(
                make_sensor_event("unknown", "status", "ok", "state"))

    def test_ambiguous_handler_fails_closed(self) -> None:
        class Duplicate(DemoLightHandler):
            domain = "duplicate"

        with self.assertRaisesRegex(ValueError, "found 2"):
            SmartHomeWorkflow([DemoLightHandler(), Duplicate()], self.device).run(self.event)

    def test_bad_event_id_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "preserve the event ID"):
            SmartHomeWorkflow([WrongIdHandler()], self.device).run(self.event)

    def test_offline_device_does_not_report_success(self) -> None:
        self.device.offline.add("demo-light")
        result = SmartHomeWorkflow([DemoLightHandler()], self.device).run(self.event)
        self.assertFalse(result.action_result.accepted)
        self.assertFalse(result.action_result.success)
        self.assertIn("offline", result.action_result.error)

    def test_readback_mismatch_is_unverified(self) -> None:
        result = SmartHomeWorkflow([DemoLightHandler()], WrongReadbackDevice({"demo-light": {"power": "off"}})).run(self.event)
        self.assertTrue(result.action_result.accepted)
        self.assertFalse(result.action_result.verified)

    def test_readback_failure_retains_dispatch_acceptance(self) -> None:
        result = SmartHomeWorkflow([DemoLightHandler()], FailedReadbackDevice({"demo-light": {"power": "off"}})).run(self.event)
        self.assertTrue(result.action_result.accepted)
        self.assertFalse(result.action_result.success)
        self.assertIn("verification failed", result.action_result.error)

    def test_review_gate_prevents_dispatch(self) -> None:
        result = SmartHomeWorkflow([ReviewHandler()], self.device).run(self.event)
        self.assertFalse(result.action_result.success)
        self.assertIn("Human review required", result.action_result.error)
        self.assertEqual(self.device.dispatch_count, 0)

    def test_human_authorization_is_not_self_approval(self) -> None:
        result = SmartHomeWorkflow([HumanAuthorizationHandler()], self.device).run(self.event)
        self.assertFalse(result.action_result.accepted)
        self.assertEqual(self.device.dispatch_count, 0)

    def test_missing_notification_adapter_is_explicit(self) -> None:
        event = make_sensor_event("status_check", "status", "ok", "state")
        result = SmartHomeWorkflow([NoticeHandler()], self.device).run(event)
        self.assertEqual(result.notification_result.status, "UNAVAILABLE")
        self.assertFalse(result.notification_result.acknowledged)

    def test_direct_goal_skips_monitoring_and_verifies_two_devices(self) -> None:
        device = SimulatedDeviceTool({
            "demo-light": {"power": "on"}, "demo-thermostat": {"mode": "comfort"},
        })
        result = SmartHomeWorkflow(
            [DemoNightModeHandler()], device, goal_interpreter=DemoGoalInterpreter(),
        ).run(make_user_goal_event("Good night"))
        self.assertEqual(result.goal.intent, "night_mode")
        self.assertEqual(result.outcome, "COMPLETE")
        self.assertEqual(len(result.action_results), 2)
        self.assertTrue(all(action.success for action in result.action_results))
        self.assertNotIn("MonitoringAgent", [entry.agent for entry in result.trace])
        self.assertEqual(device.states["demo-thermostat"]["mode"], "sleep")

    def test_second_device_failure_reports_partial_result(self) -> None:
        device = SimulatedDeviceTool({
            "demo-light": {"power": "on"}, "demo-thermostat": {"mode": "comfort"},
        })
        device.offline.add("demo-thermostat")
        result = SmartHomeWorkflow(
            [DemoNightModeHandler()], device, goal_interpreter=DemoGoalInterpreter(),
        ).run(make_user_goal_event("Good night"))
        self.assertEqual(result.outcome, "PARTIAL")
        self.assertTrue(result.action_results[0].success)
        self.assertFalse(result.action_results[1].success)
        self.assertEqual(device.states["demo-light"]["power"], "off")
        self.assertEqual(device.states["demo-thermostat"]["mode"], "comfort")

    def test_first_device_failure_skips_later_device(self) -> None:
        device = SimulatedDeviceTool({
            "demo-light": {"power": "on"}, "demo-thermostat": {"mode": "comfort"},
        })
        device.offline.add("demo-light")
        result = SmartHomeWorkflow(
            [DemoNightModeHandler()], device, goal_interpreter=DemoGoalInterpreter(),
        ).run(make_user_goal_event("Good night"))
        self.assertEqual(result.outcome, "FAILED")
        self.assertIn("Skipped", result.action_results[1].error)
        self.assertEqual(device.dispatch_count, 1)

    def test_goal_without_interpreter_or_supported_phrase_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "interpreter is not configured"):
            SmartHomeWorkflow([DemoNightModeHandler()], self.device).run(make_user_goal_event("Good night"))
        result = SmartHomeWorkflow(
            [DemoNightModeHandler()], self.device, goal_interpreter=DemoGoalInterpreter(),
        ).run(make_user_goal_event("Unlock the door"))
        self.assertEqual(result.outcome, "CLARIFICATION_REQUIRED")
        self.assertIn("What would you like", result.goal.clarification_question)
        self.assertEqual(self.device.dispatch_count, 0)

    def test_goal_interpretation_must_keep_original_event_id(self) -> None:
        class WrongGoalId:
            def interpret(self, event: Event) -> GoalInterpretation:
                return GoalInterpretation("wrong-id", "smart_home_control", "night_mode")

        with self.assertRaisesRegex(ValueError, "preserve the event ID"):
            SmartHomeWorkflow(
                [DemoNightModeHandler()], self.device, goal_interpreter=WrongGoalId(),
            ).run(make_user_goal_event("Good night"))
        self.assertEqual(self.device.dispatch_count, 0)

    def test_unsafe_later_step_blocks_entire_plan_before_dispatch(self) -> None:
        class ReviewSecondStep(DemoNightModeHandler):
            def plan_goal(self, event: Event, goal) -> GoalPlan:
                plan = super().plan_goal(event, goal)
                second = plan.action_requests[1]
                return GoalPlan(plan.assessment, (
                    plan.action_requests[0],
                    ActionRequest(second.event_id, second.device_id, second.action,
                                  second.parameters, second.expected_state, "HUMAN", second.simulated),
                ))

        device = SimulatedDeviceTool({
            "demo-light": {"power": "on"}, "demo-thermostat": {"mode": "comfort"},
        })
        result = SmartHomeWorkflow(
            [ReviewSecondStep()], device, goal_interpreter=DemoGoalInterpreter(),
        ).run(make_user_goal_event("Good night"))
        self.assertEqual(result.outcome, "FAILED")
        self.assertEqual(device.dispatch_count, 0)
        self.assertTrue(all("Human review" in action.error for action in result.action_results))

    def test_invalid_later_step_blocks_entire_plan_before_dispatch(self) -> None:
        class WrongSecondId(DemoNightModeHandler):
            def plan_goal(self, event: Event, goal) -> GoalPlan:
                plan = super().plan_goal(event, goal)
                second = plan.action_requests[1]
                return GoalPlan(plan.assessment, (
                    plan.action_requests[0],
                    ActionRequest("wrong-id", second.device_id, second.action,
                                  second.parameters, second.expected_state, second.authorization, second.simulated),
                ))

        device = SimulatedDeviceTool({
            "demo-light": {"power": "on"}, "demo-thermostat": {"mode": "comfort"},
        })
        result = SmartHomeWorkflow(
            [WrongSecondId()], device, goal_interpreter=DemoGoalInterpreter(),
        ).run(make_user_goal_event("Good night"))
        self.assertEqual(result.outcome, "FAILED")
        self.assertEqual(device.dispatch_count, 0)


if __name__ == "__main__":
    unittest.main()
