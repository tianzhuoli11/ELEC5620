"""Policy-validated multi-device plans for AR-02 / UC-02."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from models import ActionRequest, Event, GoalInterpretation, GoalPlan, MonitoringDecision, RiskAssessment

from .devices import BEDROOM_CURTAIN, BEDROOM_LIGHT, FRONT_DOOR_LOCK, LIVING_ROOM_AC


SUPPORTED_INTENTS = frozenset({"night_mode", "away_mode", "relax_mode", "unlock_door"})
ALLOWED_PARAMETER_KEYS = frozenset({"temperature_c"})


class SmartHomeControlHandler:
    """Convert an untrusted structured goal into an allow-listed device plan."""

    domain = "smart_home_control"

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
        unknown = set(goal.parameters) - ALLOWED_PARAMETER_KEYS
        if unknown:
            raise ValueError(f"unsupported goal parameters: {sorted(unknown)}")

        if goal.intent == "unlock_door":
            assessment = RiskAssessment(
                event_id=event.event_id,
                domain=self.domain,
                risk_level="MEDIUM",
                rationale="Unlocking an exterior door is sensitive and requires explicit human approval.",
                evidence=goal.evidence or "User requested a sensitive action",
                requires_human_review=True,
            )
            return GoalPlan(
                assessment=assessment,
                action_requests=(self._request(event, FRONT_DOOR_LOCK, {"locked": False}, authorization="HUMAN"),),
            )

        temperature = self._temperature(goal)
        target_states = self._targets(goal.intent, temperature)
        assessment = RiskAssessment(
            event_id=event.event_id,
            domain=self.domain,
            risk_level="LOW",
            rationale=f"The {goal.intent.replace('_', ' ')} plan uses only allow-listed simulated devices and states.",
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
    def _temperature(goal: GoalInterpretation) -> int | None:
        value = goal.parameters.get("temperature_c")
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("temperature_c must be a number")
        if not 18 <= float(value) <= 28:
            raise ValueError("temperature_c must be between 18 and 28")
        return round(float(value))

    @staticmethod
    def _targets(intent: str, temperature: int | None) -> Iterable[tuple[str, dict[str, Any]]]:
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
        )
