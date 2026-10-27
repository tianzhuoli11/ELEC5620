"""Connect Pet Care assessment and simulated owner alerts to the shared graph."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from agents.graph import SmartHomeWorkflow
from models import ActionRequest, Event, MonitoringDecision, NotificationRequest, RiskAssessment, WorkflowResult
from services.notifications import NotificationService
from simulation.devices import SimulatedDeviceTool
from simulation.notifications import SimulatedNotificationService

from .monitoring import PetAssessment, assess_pet_event
from .feeder import FEEDER_ID, FeedingDecision, SimulatedPetFeederTool, evaluate_feeding_goal


class PetCareHandler:
    domain = "pet_care"

    def __init__(
        self,
        proposal_provider: Callable[[Event], Mapping[str, Any]] | None = None,
        feeding_decision: FeedingDecision | None = None,
        feeding_requested: bool = False,
    ) -> None:
        self.proposal_provider = proposal_provider
        self.feeding_decision = feeding_decision or FeedingDecision("NOT_REQUESTED", "No optional feeding goal was requested")
        self.feeding_requested = feeding_requested
        self.pet_assessment: PetAssessment | None = None

    def supports(self, event: Event) -> bool:
        return event.event_type in {"pet_bowl_level", "pet_inactivity"}

    def assess(self, event: Event) -> MonitoringDecision:
        pet = replace(assess_pet_event(event, self.proposal_provider), feeding_requested=self.feeding_requested)
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
        action = None
        if self.feeding_decision.status == "READY":
            portion = self.feeding_decision.portion_grams
            action = ActionRequest(
                event_id=event.event_id,
                device_id=FEEDER_ID,
                action="dispense",
                parameters={"portion_grams": portion},
                expected_state={"last_event_id": event.event_id, "last_dispensed_g": portion},
                authorization="POLICY",
                simulated=True,
            )
        return MonitoringDecision(assessment=assessment, action_request=action, notification_request=notification)


@dataclass(frozen=True)
class PetWorkflowOutcome:
    assessment: PetAssessment
    workflow: WorkflowResult
    feeding: FeedingDecision


def monitor_pet_workflow(
    event: Event,
    *,
    record_path: str | Path,
    proposal_provider: Callable[[Event], Mapping[str, Any]] | None = None,
    notifier: NotificationService | None = None,
    feeding_goal: Mapping[str, Any] | None = None,
    feeding_enabled: bool = False,
    feeder: SimulatedPetFeederTool | None = None,
) -> PetWorkflowOutcome:
    """Run the shared graph, then persist the actual assessment and alert outcome."""
    feeding = evaluate_feeding_goal(event, feeding_goal, enabled=feeding_enabled, feeder=feeder)
    handler = PetCareHandler(proposal_provider, feeding, feeding_goal is not None)
    workflow = SmartHomeWorkflow(
        [handler], feeder if feeding.status == "READY" and feeder is not None else SimulatedDeviceTool({}),
        notifier=notifier if notifier is not None else SimulatedNotificationService(),
    ).run(event)
    pet = handler.pet_assessment
    if pet is None:
        raise RuntimeError("Pet Care handler did not produce an assessment")
    if feeding.status == "READY":
        if len(workflow.action_results) != 1:
            raise RuntimeError("Approved feeding goal did not produce exactly one action result")
        action = workflow.action_results[0]
        feeding = replace(
            feeding,
            status="VERIFIED" if action.success else "UNVERIFIED" if action.accepted else "FAILED",
            detail=("Simulated portion independently verified" if action.success
                    else action.error or "Simulated feeding was not verified"),
        )
    record = {
        "record_type": "pet_monitoring",
        "event": event.to_dict(),
        "assessment": pet.to_dict(),
        "workflow": workflow.to_dict(),
        "feeding": asdict(feeding),
    }
    path = Path(record_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
    return PetWorkflowOutcome(pet, workflow, feeding)
