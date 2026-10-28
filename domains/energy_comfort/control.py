"""Explicitly approved simulated control using the shared device inventory.

Safety is a supplied simulation snapshot, never inferred from missing data.
The legacy contract-readiness assessment remains available for team review.
"""
from dataclasses import dataclass, replace

from agents.graph import SmartHomeWorkflow
from models import ActionRequest, Event, WorkflowResult
from simulation.devices import SimulatedDeviceTool
from domains.smart_home_control.devices import BEDROOM_LIGHT, BEDROOM_CURTAIN, LIVING_ROOM_AC
from domains.smart_home_control import default_device_states
from .integration import EnergyComfortHandler, context_from_event


@dataclass(frozen=True)
class ControlOutcome:
    workflow: WorkflowResult
    reason: str
    planned: int


def run_energy_control(event: Event, *, approved: bool = False,
                       safety_clear: bool | None = None,
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

    class Handler(EnergyComfortHandler):
        reason = "No adjustment required"
        planned = 0

        def assess(self, observation):
            decision = super().assess(observation)
            if approved is not True or safety_clear is not True:
                self.reason = "Control blocked: explicit approval and a clear simulated safety snapshot are required"
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
    result = SmartHomeWorkflow([handler], tool).run(event)
    return ControlOutcome(result, handler.reason, handler.planned)
