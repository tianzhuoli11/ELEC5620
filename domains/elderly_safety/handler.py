"""Elderly Safety handler for the shared `SmartHomeWorkflow` (domains/base.DomainHandler).

Decision mapping (UC-01):
    HIGH    notify the caregiver and switch on the light at the fall location,
            in parallel, without asking the resident (extension 3).
    MEDIUM  ask the resident first. The baseline graph has no pause point, so
            the decision carries `requires_human_review=True` (blocks any
            dispatch) and no notification; the confirmation / timeout /
            escalation extension (SCRUM-24/25) consumes this flag.
    LOW     record only (extension 2, false alarm).

Follows the Pet Care pattern: keep the domain's full `FallAssessment` on the
handler and map it onto the shared `RiskAssessment`.
"""

from __future__ import annotations

from typing import Any

from models import ActionRequest, Event, MonitoringDecision, NotificationRequest, RiskAssessment

from domains.elderly_safety.assessment import DOMAIN, FallAssessment, FallProposalProvider, assess_fall

FALL_EVENT_TYPES = frozenset({"fall_detected", "fall_suspected", "elderly_inactivity"})

# Prototype room -> light mapping. The simulated device tool only accepts
# `set_state` with parameters that already exist on the device.
ROOM_LIGHTS = {"bathroom": "bathroom_light", "bedroom": "bedroom_light", "kitchen": "kitchen_light", "hall": "hall_light", "living": "living_light"}
DEFAULT_LIGHT = "hall_light"
CAREGIVER_REF = "fictional-primary-caregiver"


def light_for(event: Event) -> str:
    room = str(event.context.get("room") or event.context.get("location") or "").lower()
    return next((device for key, device in ROOM_LIGHTS.items() if key in room), DEFAULT_LIGHT)


class ElderlySafetyHandler:
    domain = DOMAIN

    def __init__(self, proposal_provider: FallProposalProvider | None = None) -> None:
        self.proposal_provider = proposal_provider
        self.fall_assessment: FallAssessment | None = None

    def supports(self, event: Event) -> bool:
        return event.event_type in FALL_EVENT_TYPES

    def assess(self, event: Event) -> MonitoringDecision:
        fall = assess_fall(event, self.proposal_provider)
        self.fall_assessment = fall
        assessment = RiskAssessment(
            event_id=fall.event_id,
            domain=self.domain,
            risk_level=fall.risk_level,
            rationale=fall.rationale,
            evidence=f"{fall.evidence} [{fall.evidence_source}]",
            policy_override=fall.policy_override,
            fallback_used=fall.fallback_used,
            requires_human_review=fall.requires_confirmation,
        )
        if fall.risk_level != "HIGH":
            return MonitoringDecision(assessment=assessment)

        light = light_for(event)
        action = ActionRequest(
            event_id=event.event_id,
            device_id=light,
            action="set_state",
            parameters={"power": "on"},
            expected_state={"power": "on"},
            authorization="POLICY",
            simulated=event.simulated,
        )
        notification = NotificationRequest(
            event_id=event.event_id,
            recipient_ref=CAREGIVER_REF,
            # Describes the detected condition only; no claim about the light (INTEGRATION_GUIDE).
            message=f"Possible fall needing help: {fall.rationale}",
            simulated=event.simulated,
        )
        return MonitoringDecision(assessment=assessment, action_requests=(action,), notification_request=notification)


def default_devices() -> dict[str, dict[str, Any]]:
    """Simulated lights for demos and tests."""
    return {device: {"power": "off"} for device in ROOM_LIGHTS.values()}
