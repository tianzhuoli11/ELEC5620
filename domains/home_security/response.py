"""Fixed UC-04 response policy for fictional Home Security devices.

The LLM only advises the monitoring risk. This module decides which simulated
commands are permitted after that risk has been validated by fixed rules.
"""

from __future__ import annotations

from models import (
    ActionRequest, ConfirmationReply, Event, MonitoringDecision,
    NotificationRequest, PendingConfirmation, RiskAssessment,
)
from .monitoring import validated_readings


CONFIRMATION_TIMEOUT_SECONDS = 30
MAX_CONFIRMATION_ATTEMPTS = 2
OWNER_REF = "simulated_homeowner"

# The DeviceControlTool changes these in-memory fields and reads them back.
INITIAL_DEVICE_STATES = {
    "emergency_mode": {"active": False},
    "siren": {"power": "off"},
    "security_lights": {"power": "off"},
    "appliance": {"power": "on"},
    "gas_valve": {"open": True},
    "water_valve": {"open": True},
}


def notification(event: Event, message: str) -> NotificationRequest:
    return NotificationRequest(event.event_id, OWNER_REF, message, simulated=True)


def _action(event: Event, device_id: str, state: dict, *, continue_on_failure: bool = False) -> ActionRequest:
    return ActionRequest(
        event_id=event.event_id, device_id=device_id, action="set_state",
        parameters=state, expected_state=state, authorization="POLICY",
        simulated=True, continue_on_failure=continue_on_failure,
        max_attempts=2,
    )


def protective_actions(event: Event, *, confirmed_or_urgent: bool) -> tuple[ActionRequest, ...]:
    """Choose scenario-specific commands; never lock an exit during a hazard.

The siren follows a valve/appliance command even if that command fails. It is
an independent safe warning, and both actual outcomes remain visible.
"""
    if not confirmed_or_urgent:
        return ()
    readings, _ = validated_readings(event)
    active = {kind for kind, value in readings.items() if value == 1}
    actions: list[ActionRequest] = []
    if "gas_alarm" in active:
        actions.append(_action(event, "gas_valve", {"open": False}, continue_on_failure=True))
    if "smoke_alarm" in active or "appliance_overheat_alarm" in active or "appliance_unexpected_run" in active:
        actions.append(_action(event, "appliance", {"power": "off"}, continue_on_failure=True))
    if "water_leak" in active:
        actions.append(_action(event, "water_valve", {"open": False}, continue_on_failure=True))
    if active & {"door_open", "window_open", "motion_detected", "smart_lock_access_anomaly"}:
        actions.append(_action(event, "security_lights", {"power": "on"}, continue_on_failure=True))
    if actions or active & {"smoke_alarm", "gas_alarm"}:
        actions.append(_action(event, "siren", {"power": "on"}))
    return tuple(actions)


def high_risk_decision(event: Event, assessment: RiskAssessment) -> MonitoringDecision:
    if assessment.risk_level != "HIGH" or assessment.requires_human_review:
        raise ValueError("emergency response needs a validated HIGH assessment")
    return MonitoringDecision(
        assessment=assessment,
        action_requests=protective_actions(event, confirmed_or_urgent=True),
        notification_request=notification(event, "HIGH Home Security hazard: simulated emergency response initiated."),
    )


def confirmation_question(event: Event, attempt: int) -> PendingConfirmation:
    if attempt not in (1, 2):
        raise ValueError("Home Security allows at most two confirmation attempts")
    question = (
        "Unusual Home Security activity detected. Approve a simulated protective response? "
        "Reply APPROVE or REJECT."
    )
    if attempt == 2:
        question = "Please confirm: APPROVE simulated protection or REJECT it."
    return PendingConfirmation(event.event_id, question, attempt, CONFIRMATION_TIMEOUT_SECONDS, MAX_CONFIRMATION_ATTEMPTS)


def interpret_reply(event: Event, attempt: int, reply: str) -> ConfirmationReply:
    """Only exact, explicit answers authorize MEDIUM protective actions."""
    answer = reply.strip().lower()
    if answer in ("approve", "yes", "confirm"):
        verdict = "help"
    elif answer in ("reject", "no", "deny", "false alarm"):
        verdict = "safe"
    else:
        verdict = "unclear"
    return ConfirmationReply(event.event_id, attempt, reply, verdict, "fixed_security_rules")


def confirmation_decision(
    event: Event, assessment: RiskAssessment, replies: tuple[ConfirmationReply, ...],
) -> MonitoringDecision:
    """Silence never grants permission; only an explicit approval acts.

    On timeout or exhausted unclear replies, notify the fictional owner and
    leave MEDIUM devices untouched. A later manual intervention is possible.
    """
    if assessment.risk_level != "MEDIUM" or not replies:
        raise ValueError("confirmation response needs a MEDIUM assessment and a reply")
    verdict = replies[-1].verdict
    approved = verdict == "help"
    final = RiskAssessment(
        event_id=assessment.event_id, domain=assessment.domain,
        risk_level=assessment.risk_level,
        rationale=f"{assessment.rationale} Homeowner confirmation: {verdict}.",
        evidence=f"{assessment.evidence}; confirmation_verdict={verdict}",
        policy_override=assessment.policy_override,
        fallback_used=assessment.fallback_used,
        requires_human_review=False,
    )
    actions = protective_actions(event, confirmed_or_urgent=approved)
    if approved and actions:
        message = "Home Security response approved; simulated protection started."
    elif approved:
        message = "Home Security approval recorded; no safe automatic action matched the validated evidence."
    elif verdict == "safe":
        message = "Home Security response rejected; no device action taken."
    else:
        message = "Home Security confirmation timed out or remained unclear; no device action taken."
    return MonitoringDecision(
        assessment=final,
        action_requests=actions,
        notification_request=notification(event, message),
    )
