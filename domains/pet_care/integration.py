"""Connect Pet Care assessment and simulated owner alerts to the shared graph."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from agents.graph import SmartHomeWorkflow
from models import Event, MonitoringDecision, NotificationRequest, RiskAssessment, WorkflowResult
from services.notifications import NotificationService
from simulation.devices import SimulatedDeviceTool
from simulation.notifications import SimulatedNotificationService

from .monitoring import PetAssessment, assess_pet_event


class PetCareHandler:
    domain = "pet_care"

    def __init__(self, proposal_provider: Callable[[Event], Mapping[str, Any]] | None = None) -> None:
        self.proposal_provider = proposal_provider
        self.pet_assessment: PetAssessment | None = None

    def supports(self, event: Event) -> bool:
        return event.event_type in {"pet_bowl_level", "pet_inactivity"}

    def assess(self, event: Event) -> MonitoringDecision:
        pet = assess_pet_event(event, self.proposal_provider)
        self.pet_assessment = pet
        assessment = RiskAssessment(
            event_id=pet.event_id, domain=self.domain, risk_level=pet.risk_level,
            rationale=pet.rationale, evidence=pet.evidence,
            policy_override=pet.policy_override, fallback_used=pet.fallback_used,
        )
        notification = None
        if pet.risk_level in {"MEDIUM", "HIGH"}:
            notification = NotificationRequest(
                event_id=event.event_id, recipient_ref="fictional-pet-owner",
                message=f"Pet check needs attention: {pet.rationale}",
                simulated=event.simulated,
            )
        return MonitoringDecision(assessment=assessment, notification_request=notification)


@dataclass(frozen=True)
class PetWorkflowOutcome:
    assessment: PetAssessment
    workflow: WorkflowResult


def monitor_pet_workflow(
    event: Event,
    *,
    record_path: str | Path,
    proposal_provider: Callable[[Event], Mapping[str, Any]] | None = None,
    notifier: NotificationService | None = None,
) -> PetWorkflowOutcome:
    """Run the shared graph, then persist the actual assessment and alert outcome."""
    handler = PetCareHandler(proposal_provider)
    workflow = SmartHomeWorkflow(
        [handler], SimulatedDeviceTool({}),
        notifier=notifier if notifier is not None else SimulatedNotificationService(),
    ).run(event)
    pet = handler.pet_assessment
    if pet is None:
        raise RuntimeError("Pet Care handler did not produce an assessment")
    record = {
        "record_type": "pet_monitoring",
        "event": event.to_dict(),
        "assessment": pet.to_dict(),
        "workflow": workflow.to_dict(),
    }
    path = Path(record_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
    return PetWorkflowOutcome(pet, workflow)
