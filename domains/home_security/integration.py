"""Run and resume Home Security through the shared three-agent LangGraph."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter

from agents.graph import SmartHomeWorkflow
from models import AuditEntry, Event, MonitoringDecision, NotificationRequest, RiskAssessment, WorkflowResult
from services.notifications import NotificationService
from simulation.devices import SimulatedDeviceTool
from simulation.notifications import SimulatedNotificationService
from tools.device import DeviceTool

from . import response
from .external_warnings import (
    WARNING_EVENT_TYPE, ExternalWarningAssessment, assess_external_warning,
    external_warning_decision,
)
from .monitoring import EVENT_TYPE, READING_TYPES, ProposalProvider, SecurityAssessment, assess_security_event


class HomeSecurityHandler:
    domain = "home_security"

    def __init__(self, proposal_provider: ProposalProvider | None = None) -> None:
        self.proposal_provider = proposal_provider
        self.security_assessment: SecurityAssessment | None = None
        self.last_notification_request: NotificationRequest | None = None
        self.classification_ms: float | None = None

    def supports(self, event: Event) -> bool:
        return event.event_type in (EVENT_TYPE, WARNING_EVENT_TYPE)

    def assess(self, event: Event) -> MonitoringDecision:
        started = perf_counter()
        try:
            return self._assess(event)
        finally:
            self.classification_ms = round((perf_counter() - started) * 1000, 3)

    def _assess(self, event: Event) -> MonitoringDecision:
        if event.event_type == WARNING_EVENT_TYPE:
            warning = assess_external_warning(event, self.proposal_provider)
            self.security_assessment = warning
            decision = external_warning_decision(event, warning)
            self.last_notification_request = decision.notification_request
            return decision
        security = assess_security_event(event, self.proposal_provider)
        self.security_assessment = security
        assessment = RiskAssessment(
            event_id=security.event_id, domain=self.domain,
            risk_level=security.risk_level, rationale=security.rationale,
            evidence=security.evidence, policy_override=security.policy_override,
            fallback_used=security.fallback_used,
            requires_human_review=security.requires_human_review,
        )
        if assessment.risk_level == "HIGH":
            decision = response.high_risk_decision(event, assessment)
            self.last_notification_request = decision.notification_request
            return decision
        return MonitoringDecision(assessment=assessment)

    def confirmation_question(self, event: Event, assessment: RiskAssessment, attempt: int):
        return response.confirmation_question(event, attempt)

    def interpret_reply(self, event: Event, attempt: int, reply: str | None):
        return response.interpret_reply(event, attempt, reply or "")

    def escalate(self, event: Event, assessment: RiskAssessment, replies):
        decision = response.confirmation_decision(event, assessment, replies)
        self.last_notification_request = decision.notification_request
        return decision


@dataclass(frozen=True)
class SecurityWorkflowOutcome:
    assessment: SecurityAssessment
    workflow: WorkflowResult
    classification_ms: float
    workflow_ms: float
    workflow_engine: SmartHomeWorkflow
    handler: HomeSecurityHandler
    device_tool: DeviceTool
    notification_history: tuple[dict[str, str], ...]


def _recorded_event(event: Event) -> dict:
    """Persist only the fictional fields used by the security assessment."""
    if event.event_type == WARNING_EVENT_TYPE:
        return {
            "event_id": event.event_id, "event_type": event.event_type,
            "source": event.source, "timestamp": event.timestamp,
            "simulated": event.simulated,
            "raw_warning": event.context.get("warning"),
        }
    context = event.context
    devices = context.get("device_status")
    devices = devices if isinstance(devices, dict) else {}
    return {
        "event_id": event.event_id, "event_type": event.event_type,
        "timestamp": event.timestamp, "simulated": event.simulated,
        "readings": [
            {"reading_type": reading.reading_type,
             "value": int(reading.value) if isinstance(reading.value, (bool, int, float)) and reading.value in (0, 1) else None,
             "unit": reading.unit, "observed_at": reading.observed_at}
            for reading in event.readings if reading.reading_type in READING_TYPES
        ],
        "context": {
            "home_mode": context.get("home_mode") if context.get("home_mode") in ("HOME", "AWAY") else "UNKNOWN",
            "recent_activity": context.get("recent_activity") if context.get("recent_activity") in ("EXPECTED", "NONE") else "UNKNOWN",
            "authorized_entry": context.get("authorized_entry") if isinstance(context.get("authorized_entry"), bool) else None,
            "device_status": {
                "front_door_lock": devices.get("front_door_lock") if devices.get("front_door_lock") in ("locked", "unlocked") else "unknown",
                "water_valve": devices.get("water_valve") if devices.get("water_valve") in ("open", "closed") else "unknown",
            },
        },
    }


def _append_record(
    event: Event, security: SecurityAssessment, workflow: WorkflowResult,
    classification_ms: float, workflow_ms: float, record_path: str | Path,
    notification_history: tuple[dict[str, str], ...],
) -> None:
    recorded_event = _recorded_event(event)
    recorded_workflow = workflow.to_dict()
    recorded_workflow["event"] = recorded_event
    record = {
        "record_type": "external_warning_workflow" if event.event_type == WARNING_EVENT_TYPE else "security_workflow",
        "received_at": datetime.now(timezone.utc).isoformat(),
        "classification_ms": classification_ms,
        "workflow_ms": workflow_ms,
        "event": recorded_event,
        "assessment": security.to_dict(),
        "workflow": recorded_workflow,
        "notifications": list(notification_history),
    }
    path = Path(record_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")


def _notify_confirmation(engine: SmartHomeWorkflow, result: WorkflowResult) -> WorkflowResult:
    pending = result.pending_confirmation
    if pending is None:
        return result
    notice = engine.notify(response.notification(result.event, pending.question))
    trace = result.trace + (AuditEntry(
        result.event.event_id, "HomeCoordinatorAgent", f"confirmation_notification:{notice.status}",
        datetime.now(timezone.utc).isoformat(),
    ),)
    return replace(result, notification_result=notice, trace=trace)


def _notice_entry(result: WorkflowResult, purpose: str, message: str) -> tuple[dict[str, str], ...]:
    notice = result.notification_result
    if notice is None:
        return ()
    return ({"purpose": purpose, "recipient_ref": response.OWNER_REF,
             "message": message, "status": notice.status, "detail": notice.detail},)


def _alert_failed_actions(
    engine: SmartHomeWorkflow, result: WorkflowResult,
) -> tuple[WorkflowResult, tuple[dict[str, str], ...]]:
    if not any(not action.success for action in result.action_results):
        return result, ()
    message = "A simulated protective device action failed or could not be verified; manual safety check needed."
    notice = engine.notify(response.notification(result.event, message))
    updated = replace(
        result, notification_result=notice,
        trace=result.trace + (AuditEntry(
            result.event.event_id, "HomeCoordinatorAgent", f"failed_action_notification:{notice.status}",
            datetime.now(timezone.utc).isoformat(),
        ),),
    )
    return updated, _notice_entry(updated, "failed_action", message)


def monitor_security_workflow(
    event: Event, *, record_path: str | Path,
    proposal_provider: ProposalProvider | None = None,
    device_tool: DeviceTool | None = None,
    notifier: NotificationService | None = None,
    offline_devices: tuple[str, ...] = (),
) -> SecurityWorkflowOutcome:
    """Assess and respond through the shared graph, then audit actual outcomes."""
    started = perf_counter()
    handler = HomeSecurityHandler(proposal_provider)
    states = {name: state.copy() for name, state in response.INITIAL_DEVICE_STATES.items()}
    status = event.context.get("device_status", {})
    if isinstance(status, dict) and status.get("water_valve") in ("open", "closed"):
        states["water_valve"]["open"] = status["water_valve"] == "open"
    tool = device_tool if device_tool is not None else SimulatedDeviceTool(states)
    if offline_devices:
        if not isinstance(tool, SimulatedDeviceTool):
            raise ValueError("offline_devices requires the simulated device tool")
        tool.offline.update(offline_devices)
    engine = SmartHomeWorkflow(
        [handler], tool,
        notifier=notifier if notifier is not None else SimulatedNotificationService(),
    )
    workflow = _notify_confirmation(engine, engine.run(event))
    initial_message = (
        workflow.pending_confirmation.question if workflow.pending_confirmation
        else handler.last_notification_request.message if handler.last_notification_request else ""
    )
    history = _notice_entry(workflow, "confirmation" if workflow.pending_confirmation else "response", initial_message)
    workflow, failure_notice = _alert_failed_actions(engine, workflow)
    history += failure_notice
    workflow_ms = round((perf_counter() - started) * 1000, 3)
    classification_ms = handler.classification_ms
    security = handler.security_assessment
    if security is None or classification_ms is None:
        raise RuntimeError("Home Security handler did not produce an assessment")
    _append_record(event, security, workflow, classification_ms, workflow_ms, record_path, history)
    return SecurityWorkflowOutcome(security, workflow, classification_ms, workflow_ms, engine, handler, tool, history)


def resume_security_workflow(
    previous: SecurityWorkflowOutcome, reply: str | None, *, record_path: str | Path,
) -> SecurityWorkflowOutcome:
    """Continue the same event; None represents an expired confirmation timer."""
    if previous.workflow.pending_confirmation is None:
        raise ValueError("no Home Security confirmation is pending")
    started = perf_counter()
    resumed = previous.workflow_engine.resume(previous.workflow, reply)
    resumed = _notify_confirmation(previous.workflow_engine, resumed)
    message = (
        resumed.pending_confirmation.question if resumed.pending_confirmation
        else previous.handler.last_notification_request.message if previous.handler.last_notification_request else ""
    )
    history = previous.notification_history + _notice_entry(
        resumed, "confirmation" if resumed.pending_confirmation else "response", message,
    )
    resumed, failure_notice = _alert_failed_actions(previous.workflow_engine, resumed)
    history += failure_notice
    if resumed.notification_result is None:
        resumed = replace(resumed, notification_result=previous.workflow.notification_result)
    workflow_ms = round((perf_counter() - started) * 1000, 3)
    _append_record(resumed.event, previous.assessment, resumed, previous.classification_ms, workflow_ms, record_path, history)
    return replace(previous, workflow=resumed, workflow_ms=workflow_ms, notification_history=history)
