"""Small executable integration example for the shared three-agent graph."""

from __future__ import annotations

import json

from agents.graph import SmartHomeWorkflow
from models import ActionRequest, Event, GoalInterpretation, GoalPlan, MonitoringDecision, RiskAssessment
from simulation.devices import SimulatedDeviceTool
from simulation.events import make_sensor_event, make_user_goal_event
from simulation.goals import DemoGoalInterpreter


class DemoLightHandler:
    domain = "framework_demo"

    def supports(self, event: Event) -> bool:
        return event.event_type == "demo_light_request"

    def assess(self, event: Event) -> MonitoringDecision:
        return MonitoringDecision(
            assessment=RiskAssessment(
                event_id=event.event_id, domain=self.domain, risk_level="LOW",
                rationale="A simulated light request is permitted by the demo policy.",
                evidence="User request in a simulated event; no LLM inference",
            ),
            action_request=ActionRequest(
                event_id=event.event_id, device_id="demo-light", action="set_state",
                parameters={"power": "on"}, expected_state={"power": "on"},
                authorization="POLICY", simulated=event.simulated,
            ),
        )


class DemoNightModeHandler:
    """Small policy example; Yang Yang's real domain rules belong in his branch."""

    domain = "smart_home_control"

    def supports(self, event: Event) -> bool:
        return False

    def assess(self, event: Event) -> MonitoringDecision:
        raise ValueError("night mode is a direct goal, not a sensor assessment")

    def supports_goal(self, goal: GoalInterpretation) -> bool:
        return goal.domain == self.domain and goal.intent == "night_mode"

    def plan_goal(self, event: Event, goal: GoalInterpretation) -> GoalPlan:
        return GoalPlan(
            assessment=RiskAssessment(
                event_id=event.event_id, domain=self.domain, risk_level="LOW",
                rationale="Fictional night-mode commands are permitted by the demo policy.",
                evidence=goal.evidence,
            ),
            action_requests=(
                ActionRequest(event.event_id, "demo-light", "set_state", {"power": "off"},
                              {"power": "off"}, "POLICY", event.simulated),
                ActionRequest(event.event_id, "demo-thermostat", "set_state", {"mode": "sleep"},
                              {"mode": "sleep"}, "POLICY", event.simulated),
            ),
        )


def run_demo() -> dict:
    device = SimulatedDeviceTool({"demo-light": {"power": "off"}})
    workflow = SmartHomeWorkflow([DemoLightHandler()], device)
    event = make_sensor_event("demo_light_request", "power_request", "on", "state")
    return workflow.run(event).to_dict()


def run_goal_demo(*, offline_device: str | None = None) -> dict:
    device = SimulatedDeviceTool({
        "demo-light": {"power": "on"},
        "demo-thermostat": {"mode": "comfort"},
    })
    if offline_device:
        device.offline.add(offline_device)
    workflow = SmartHomeWorkflow(
        [DemoNightModeHandler()], device, goal_interpreter=DemoGoalInterpreter(),
    )
    return workflow.run(make_user_goal_event("Good night")).to_dict()


if __name__ == "__main__":
    print(json.dumps({"sensor_event": run_demo(), "direct_goal": run_goal_demo()}, indent=2))
