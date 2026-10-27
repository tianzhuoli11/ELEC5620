"""Policy-validated multi-device plans for AR-02 / UC-02."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from models import ActionRequest, Event, GoalInterpretation, GoalPlan, MonitoringDecision, PendingConfirmation, RiskAssessment
from services.smart_home_goals import SUPPORTED_INTENTS, validate_smart_home_parameters

from .devices import BEDROOM_CURTAIN, BEDROOM_LIGHT, FRONT_DOOR_LOCK, LIVING_ROOM_AC


class SmartHomeControlHandler:
    """Convert an untrusted structured goal into an allow-listed device plan."""

    domain = "smart_home_control"

    def __init__(
        self,
        *,
        confirmation_decision: Literal["approved", "declined"] | None = None,
        confirmed_event_id: str | None = None,
    ) -> None:
        if (confirmation_decision is None) != (confirmed_event_id is None):
            raise ValueError("a confirmation decision and event ID must be supplied together")
        self.confirmation_decision = confirmation_decision
        self.confirmed_event_id = confirmed_event_id

    def supports(self, event: Event) -> bool:
        return False

    def assess(self, event: Event) -> MonitoringDecision:
        raise ValueError("Smart Home Control handles direct user goals, not sensor events")

    def supports_goal(self, goal: GoalInterpretation) -> bool:
        return goal.domain == self.domain and goal.intent in SUPPORTED_INTENTS

    def plan_goal(self, event: Event, goal: GoalInterpretation) -> GoalPlan:
        if event.event_type != "user_goal":
            raise ValueError("Smart Home Control requires a user_goal event")
        if not self.supports_goal(goal):
            raise ValueError(f"unsupported Smart Home Control goal: {goal.intent}")
        parameters = validate_smart_home_parameters(goal.intent, goal.parameters)
        temperature = parameters.get("temperature_c")
        target_states = tuple(self._targets(goal.intent, temperature, parameters))
        contains_unlock = any(device_id == FRONT_DOOR_LOCK and state.get("locked") is False for device_id, state in target_states)
        decision = (
            self.confirmation_decision
            if self.confirmed_event_id == event.event_id
            else None
        )

        if contains_unlock and decision not in ("approved", "declined"):
            assessment = RiskAssessment(
                event_id=event.event_id,
                domain=self.domain,
                risk_level="MEDIUM",
                rationale="Unlocking an exterior door is sensitive and requires explicit user confirmation.",
                evidence=goal.evidence or "User requested a sensitive action",
                requires_human_review=True,
            )
            return GoalPlan(
                assessment=assessment,
                pending_confirmation=PendingConfirmation(
                    event_id=event.event_id,
                    question="Unlock the front door? Confirm only if you are authorised and it is safe to do so.",
                    attempt=1,
                    timeout_seconds=60,
                    max_attempts=1,
                ),
            )

        if contains_unlock and decision == "declined":
            target_states = tuple(
                (device_id, state)
                for device_id, state in target_states
                if not (device_id == FRONT_DOOR_LOCK and state.get("locked") is False)
            )

        approval_note = " Explicit in-app approval was recorded." if decision == "approved" else ""
        decline_note = " The sensitive unlock action was declined and removed from the plan." if decision == "declined" else ""
        assessment = RiskAssessment(
            event_id=event.event_id,
            domain=self.domain,
            risk_level="MEDIUM" if contains_unlock else "LOW",
            rationale=(
                f"The {goal.intent.replace('_', ' ')} plan uses only allow-listed simulated devices and states."
                f"{approval_note}{decline_note}"
            ),
            evidence=goal.evidence or "Validated Smart Home Control goal",
        )
        return GoalPlan(
            assessment=assessment,
            action_requests=tuple(
                self._request(event, device_id, state)
                for device_id, state in target_states
            ),
        )

    @staticmethod
    def _targets(
        intent: str,
        temperature: int | None,
        parameters: dict[str, Any],
    ) -> Iterable[tuple[str, dict[str, Any]]]:
        if intent == "night_mode":
            return (
                (BEDROOM_LIGHT, {"power": "off"}),
                (BEDROOM_CURTAIN, {"position": "closed"}),
                (FRONT_DOOR_LOCK, {"locked": True}),
                (LIVING_ROOM_AC, {"power": "on", "mode": "sleep", "temperature_c": temperature or 22}),
            )
        if intent == "away_mode":
            return (
                (BEDROOM_LIGHT, {"power": "off"}),
                (BEDROOM_CURTAIN, {"position": "closed"}),
                (FRONT_DOOR_LOCK, {"locked": True}),
                (LIVING_ROOM_AC, {"power": "on", "mode": "eco", "temperature_c": temperature or 26}),
            )
        if intent == "relax_mode":
            return (
                (BEDROOM_LIGHT, {"power": "on", "brightness": 40}),
                (BEDROOM_CURTAIN, {"position": "closed"}),
                (LIVING_ROOM_AC, {"power": "on", "mode": "comfort", "temperature_c": temperature or 23}),
            )
        if intent == "unlock_door":
            return ((FRONT_DOOR_LOCK, {"locked": False}),)
        if intent == "direct_control":
            targets: list[tuple[str, dict[str, Any]]] = []
            light = {
                state_key: parameters[parameter_key]
                for parameter_key, state_key in (("light_power", "power"), ("light_brightness", "brightness"))
                if parameter_key in parameters
            }
            curtain = {"position": parameters["curtain_position"]} if "curtain_position" in parameters else {}
            lock = {"locked": parameters["door_locked"]} if "door_locked" in parameters else {}
            ac = {
                state_key: parameters[parameter_key]
                for parameter_key, state_key in (("ac_power", "power"), ("ac_mode", "mode"), ("temperature_c", "temperature_c"))
                if parameter_key in parameters
            }
            for device_id, state in (
                (BEDROOM_LIGHT, light),
                (BEDROOM_CURTAIN, curtain),
                (FRONT_DOOR_LOCK, lock),
                (LIVING_ROOM_AC, ac),
            ):
                if state:
                    targets.append((device_id, state))
            return tuple(targets)
        raise ValueError(f"no policy plan exists for intent: {intent}")

    @staticmethod
    def _request(
        event: Event,
        device_id: str,
        state: dict[str, Any],
        *,
        authorization: str = "POLICY",
    ) -> ActionRequest:
        return ActionRequest(
            event_id=event.event_id,
            device_id=device_id,
            action="set_state",
            parameters=dict(state),
            expected_state=dict(state),
            authorization=authorization,
            simulated=event.simulated,
            continue_on_failure=True,
            max_attempts=2,
        )
