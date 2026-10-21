"""Run Home Security through the shared three-agent LangGraph workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter

from agents.graph import SmartHomeWorkflow
from models import Event, MonitoringDecision, RiskAssessment, WorkflowResult
from simulation.devices import SimulatedDeviceTool

from .monitoring import EVENT_TYPE, READING_TYPES, ProposalProvider, SecurityAssessment, assess_security_event


class HomeSecurityHandler:
    domain = "home_security"

    def __init__(self, proposal_provider: ProposalProvider | None = None) -> None:
        self.proposal_provider = proposal_provider
        self.security_assessment: SecurityAssessment | None = None

    def supports(self, event: Event) -> bool:
        return event.event_type == EVENT_TYPE

    def assess(self, event: Event) -> MonitoringDecision:
        security = assess_security_event(event, self.proposal_provider)
        self.security_assessment = security
        assessment = RiskAssessment(
            event_id=security.event_id,
            domain=self.domain,
            risk_level=security.risk_level,
            rationale=security.rationale,
            evidence=security.evidence,
            policy_override=security.policy_override,
            fallback_used=security.fallback_used,
            requires_human_review=security.requires_human_review,
        )
        # SCRUM-15 only assesses and records. Later tasks add notifications and actions.
        return MonitoringDecision(assessment=assessment)


@dataclass(frozen=True)
class SecurityWorkflowOutcome:
    assessment: SecurityAssessment
    workflow: WorkflowResult
    classification_ms: float


def _recorded_event(event: Event) -> dict:
    """Persist only the fictional fields used by the security assessment."""
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


def monitor_security_workflow(
    event: Event, *, record_path: str | Path,
    proposal_provider: ProposalProvider | None = None,
) -> SecurityWorkflowOutcome:
    """Assess a simulated event and persist its actual shared-workflow result."""
    received_at = datetime.now(timezone.utc).isoformat()
    started = perf_counter()
    handler = HomeSecurityHandler(proposal_provider)
    workflow = SmartHomeWorkflow([handler], SimulatedDeviceTool({})).run(event)
    classification_ms = round((perf_counter() - started) * 1000, 3)
    security = handler.security_assessment
    if security is None:
        raise RuntimeError("Home Security handler did not produce an assessment")

    recorded_event = _recorded_event(event)
    recorded_workflow = workflow.to_dict()
    recorded_workflow["event"] = recorded_event
    record = {
        "record_type": "security_monitoring",
        "received_at": received_at,
        "classification_ms": classification_ms,
        "event": recorded_event,
        "assessment": security.to_dict(),
        "workflow": recorded_workflow,
    }
    path = Path(record_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
    return SecurityWorkflowOutcome(security, workflow, classification_ms)
