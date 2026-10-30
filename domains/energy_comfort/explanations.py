"""Deterministic Energy & Comfort explanations derived only from supplied evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from models import WorkflowResult

from .control_policy import LightShutdownEligibility
from .monitoring import EnergyComfortAssessment
from .post_action import PostActionEnvironmentObservation, environment_effect_text


EvidenceStatus = Literal["CONSISTENT", "MISSING", "CONFLICTING"]
ExecutionStatus = Literal["UNKNOWN", "NOT_EXECUTED", "VERIFIED", "PARTIAL", "UNVERIFIED"]
SafetyStatus = Literal[
    "UNKNOWN", "BLOCKED_BY_SAFETY", "NOT_ELIGIBLE", "ELIGIBLE_FOR_LATER_PLANNING",
]


@dataclass(frozen=True)
class EnergyComfortExplanation:
    decision: str
    summary: str
    evidence: tuple[str, ...]
    missing_fields: tuple[str, ...]
    evidence_status: EvidenceStatus
    execution_status: ExecutionStatus
    execution_detail: str
    safety_status: SafetyStatus
    safety_detail: str
    environment_effect: str
    trace: tuple[str, ...]
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _decision_summary(assessment: EnergyComfortAssessment) -> str:
    if assessment.decision == "NO_ADJUSTMENT":
        return "No adjustment was indicated for the assessed policy scope only."
    if assessment.decision == "ADJUSTMENT_NEEDED":
        return "Adjustment was indicated; this does not show that device control was authorized or executed."
    missing = ", ".join(assessment.missing_fields) or "unspecified evidence"
    return f"The assessment was inconclusive because required evidence is missing: {missing}."


def explain_energy_comfort(
    assessment: EnergyComfortAssessment,
    *,
    workflow: WorkflowResult | None = None,
    eligibility: LightShutdownEligibility | None = None,
    post_action_environment: PostActionEnvironmentObservation | None = None,
) -> EnergyComfortExplanation:
    """Explain an assessment without inferring actions or environmental effects."""

    trace: tuple[str, ...] = ()
    evidence_status: EvidenceStatus = "MISSING"
    execution_status: ExecutionStatus = "UNKNOWN"
    execution_detail = "Execution evidence was not supplied; device execution is unknown."

    if workflow is not None:
        trace = tuple(f"{item.agent}:{item.outcome}" for item in workflow.trace)
        consistent = (
            workflow.event.event_id == assessment.event_id
            and workflow.assessment.event_id == assessment.event_id
            and workflow.domain == "energy_comfort"
            and f"decision={assessment.decision}" in workflow.assessment.evidence
        )
        if not consistent:
            evidence_status = "CONFLICTING"
            execution_detail = "Workflow evidence conflicts with the supplied domain assessment; execution is unknown."
        else:
            evidence_status = "CONSISTENT"
            results = workflow.action_results
            if not results:
                execution_status = "NOT_EXECUTED"
                execution_detail = "No device action result is recorded; this was assessment-only."
            else:
                verified = sum(result.success for result in results)
                if verified == len(results):
                    execution_status = "VERIFIED"
                    execution_detail = "Every supplied device action result was accepted and independently verified."
                elif verified:
                    execution_status = "PARTIAL"
                    execution_detail = "Only some supplied device action results were independently verified."
                else:
                    execution_status = "UNVERIFIED"
                    execution_detail = "No supplied device action result was independently verified."

    safety_status: SafetyStatus = "UNKNOWN"
    safety_detail = "No control-eligibility safety evidence was supplied."
    if eligibility is not None:
        safety_reasons = {
            "safety_policy_unknown", "safety_policy_rejected",
            "unknown_safety_conditions", "conflicting_safety_conditions",
        }.intersection(eligibility.reasons)
        if safety_reasons:
            safety_status = "BLOCKED_BY_SAFETY"
            safety_detail = "Control eligibility was denied because safety evidence was unknown, rejected, or conflicting."
        elif eligibility.eligible:
            safety_status = "ELIGIBLE_FOR_LATER_PLANNING"
            safety_detail = "Domain eligibility checks passed, but no executable device authorization is implied."
        else:
            safety_status = "NOT_ELIGIBLE"
            safety_detail = "Control eligibility was denied by the recorded domain conditions."

    if post_action_environment is not None:
        environment_effect = environment_effect_text(post_action_environment)
    else:
        environment_effect = (
            "UNKNOWN_NOT_MEASURED: no post-action temperature, power, or energy-savings "
            "evidence is represented by this explanation."
        )

    return EnergyComfortExplanation(
        decision=assessment.decision,
        summary=_decision_summary(assessment),
        evidence=assessment.evidence,
        missing_fields=assessment.missing_fields,
        evidence_status=evidence_status,
        execution_status=execution_status,
        execution_detail=execution_detail,
        safety_status=safety_status,
        safety_detail=safety_detail,
        environment_effect=environment_effect,
        trace=trace,
        limitations=(
            "Workflow trace is in-memory and is not persistent audit history.",
            "No energy saving, comfort improvement, or whole-home safety conclusion is inferred.",
        ),
    )
