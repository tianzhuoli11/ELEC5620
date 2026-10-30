"""Explicitly approved simulated control using the shared device inventory.

Safety is derived from fresh cross-domain workflows, never from a UI override.
The legacy contract-readiness assessment remains available for team review.
"""
from dataclasses import dataclass, replace

from agents.graph import SmartHomeWorkflow
from models import ActionRequest, Event, WorkflowResult
from simulation.devices import SimulatedDeviceTool
from domains.smart_home_control.devices import BEDROOM_LIGHT, BEDROOM_CURTAIN, LIVING_ROOM_AC
from domains.smart_home_control import default_device_states
from .integration import EnergyComfortHandler, context_from_event
from .monitoring import EnergyComfortAssessment
from .post_action import PostActionEnvironmentObservation, assess_post_action_environment
from services.safety_state import SafetyState
from tools.device import DispatchResult


@dataclass(frozen=True)
class ControlOutcome:
    workflow: WorkflowResult
    reason: str
    planned: int
    safety_before: dict
    safety_after: dict
    post_action_environment: PostActionEnvironmentObservation
    energy_assessment: EnergyComfortAssessment


def run_energy_control(event: Event, *, approved: bool = False,
                       safety_state: SafetyState | None = None,
                       device_tool: SimulatedDeviceTool | None = None) -> ControlOutcome:
    """Execute a bounded simulated plan only after explicit approval and safety clearance.

    Occupied comfort adjusts the AC to the nearest allowed preference boundary
    and closes the curtain for cooling. Unoccupied energy control switches off
    only an explicitly observed bedroom light; whole-home watts never establish
    which device caused excess usage. No savings or temperature change is claimed.
    """
    context = context_from_event(event)
    if not event.simulated or not context.simulated:
        raise ValueError("Energy control supports simulated events only")
    tool = device_tool or SimulatedDeviceTool(default_device_states())
    if not isinstance(tool, SimulatedDeviceTool):
        raise ValueError("Energy control requires a simulated device adapter")
    safety = safety_state if isinstance(safety_state, SafetyState) else SafetyState()

    class GuardedTool:
        def dispatch(self, request):
            if not safety.snapshot()["clear"]:
                return DispatchResult(False, "Cross-domain safety changed; energy action blocked")
            return tool.dispatch(request)

        def read_state(self, device_id):
            return tool.read_state(device_id)

    class Handler(EnergyComfortHandler):
        reason = "No adjustment required"
        planned = 0
        safety_before = None

        def assess(self, observation):
            decision = super().assess(observation)
            snapshot = safety.snapshot()
            self.safety_before = snapshot
            if approved is not True or not snapshot["clear"]:
                self.reason = "Control blocked: approval and fresh clear domain assessments are required. " + "; ".join(snapshot["reasons"])
                return replace(decision, assessment=replace(decision.assessment, rationale=self.reason))
            if self.energy_assessment.decision != "ADJUSTMENT_NEEDED":
                self.reason = self.energy_assessment.rationale
                return decision
            targets = []
            if context.environment.occupied is True:
                low, high = context.preference.temperature_min_c, context.preference.temperature_max_c
                target = high if context.environment.temperature_c > high else low
                if not 18 <= target <= 28:
                    self.reason = "Control blocked: requested comfort boundary is outside the 18–28 C device policy"
                    return replace(decision, assessment=replace(decision.assessment, rationale=self.reason))
                if context.environment.temperature_c > high:
                    targets.append((BEDROOM_CURTAIN, {"position": "closed"}))
                targets.append((LIVING_ROOM_AC, {"power": "on", "mode": "comfort", "temperature_c": target}))
            elif any(d.device_id == BEDROOM_LIGHT and d.available is True and d.observed_state.get("power") == "on" for d in context.devices):
                targets.append((BEDROOM_LIGHT, {"power": "off"}))
            if not targets:
                self.reason = "Control blocked: no permitted device target supported by the observations"
                return replace(decision, assessment=replace(decision.assessment, rationale=self.reason))
            self.planned = len(targets)
            self.reason = "Explicitly approved simulated control; environmental effect and savings remain unmeasured"
            actions = tuple(ActionRequest(observation.event_id, device, "set_state", state, state.copy(),
                                          "POLICY", True, continue_on_failure=True, max_attempts=2)
                            for device, state in targets)
            return replace(decision, action_requests=actions)

    handler = Handler()
    result = SmartHomeWorkflow([handler], GuardedTool()).run(event)
    if handler.energy_assessment is None:
        raise RuntimeError("Energy control handler did not produce an assessment")
    final_safety = safety.snapshot()
    reason = handler.reason
    if handler.planned and not final_safety["clear"]:
        reason = "Safety evidence changed during execution; further energy actions are blocked."
    post_action = assess_post_action_environment(
        workflow=result,
        planned_actions=handler.planned,
    )
    return ControlOutcome(
        result,
        reason,
        handler.planned,
        handler.safety_before,
        final_safety,
        post_action,
        handler.energy_assessment,
    )
