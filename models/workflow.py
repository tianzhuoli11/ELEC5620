"""Shared, UI-independent messages passed through the three-agent workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .events import Event

RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]
NotificationStatus = Literal["SIMULATED", "SENT", "FAILED", "UNAVAILABLE"]


@dataclass(frozen=True)
class RiskAssessment:
    event_id: str
    domain: str
    risk_level: RiskLevel
    rationale: str
    evidence: str
    policy_override: bool = False
    fallback_used: bool = False
    requires_human_review: bool = False

    def __post_init__(self) -> None:
        if self.risk_level not in ("LOW", "MEDIUM", "HIGH"):
            raise ValueError("risk_level must be LOW, MEDIUM or HIGH")
        if not self.event_id or not self.domain or not self.rationale:
            raise ValueError("assessment event_id, domain and rationale are required")


@dataclass(frozen=True)
class ActionRequest:
    event_id: str
    device_id: str
    action: str
    parameters: dict[str, Any]
    expected_state: dict[str, Any]
    authorization: Literal["POLICY", "HUMAN"]
    simulated: bool

    def __post_init__(self) -> None:
        if not self.event_id or not self.device_id or not self.action:
            raise ValueError("action event_id, device_id and action are required")
        if self.authorization not in ("POLICY", "HUMAN"):
            raise ValueError("action authorization must be POLICY or HUMAN")
        if not self.expected_state:
            raise ValueError("expected_state is required for result verification")


@dataclass(frozen=True)
class ActionResult:
    event_id: str
    device_id: str
    action: str
    accepted: bool
    verified: bool
    returned_state: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    simulated: bool = True

    @property
    def success(self) -> bool:
        return self.accepted and self.verified

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "success": self.success}


@dataclass(frozen=True)
class NotificationRequest:
    event_id: str
    recipient_ref: str
    message: str
    simulated: bool


@dataclass(frozen=True)
class NotificationResult:
    event_id: str
    status: NotificationStatus
    detail: str
    acknowledged: bool = False


@dataclass(frozen=True)
class MonitoringDecision:
    assessment: RiskAssessment
    action_request: ActionRequest | None = None
    notification_request: NotificationRequest | None = None
    action_requests: tuple[ActionRequest, ...] = ()

    @property
    def actions(self) -> tuple[ActionRequest, ...]:
        """All planned actions; the singular field keeps existing domains compatible."""
        first = (self.action_request,) if self.action_request else ()
        return first + self.action_requests


@dataclass(frozen=True)
class GoalInterpretation:
    """Structured proposal from an interpreter, still subject to domain policy."""

    event_id: str
    domain: str
    intent: str
    parameters: dict[str, Any] = field(default_factory=dict)
    evidence: str = ""
    clarification_question: str | None = None

    def __post_init__(self) -> None:
        if not self.event_id or not self.domain or not self.intent:
            raise ValueError("goal event_id, domain and intent are required")


@dataclass(frozen=True)
class GoalPlan:
    """Domain-validated plan for a direct user goal; monitoring may be skipped."""

    assessment: RiskAssessment
    action_requests: tuple[ActionRequest, ...] = ()
    notification_request: NotificationRequest | None = None


@dataclass(frozen=True)
class AuditEntry:
    event_id: str
    agent: str
    outcome: str
    timestamp: str


@dataclass(frozen=True)
class WorkflowResult:
    event: Event
    domain: str
    assessment: RiskAssessment
    action_result: ActionResult | None
    notification_result: NotificationResult | None
    trace: tuple[AuditEntry, ...]
    action_results: tuple[ActionResult, ...] = ()
    goal: GoalInterpretation | None = None

    @property
    def outcome(self) -> str:
        """Describe complete, partial, failed and assessment-only outcomes honestly."""
        if self.goal and self.goal.clarification_question:
            return "CLARIFICATION_REQUIRED"
        completed = sum(result.success for result in self.action_results)
        failed = len(self.action_results) - completed
        notice_failed = self.notification_result is not None and self.notification_result.status in ("FAILED", "UNAVAILABLE")
        if failed:
            return "PARTIAL" if completed else "FAILED"
        if notice_failed:
            return "PARTIAL" if completed else "FAILED"
        if completed or self.notification_result is not None:
            return "COMPLETE"
        return "ASSESSED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event.to_dict(),
            "domain": self.domain,
            "assessment": asdict(self.assessment),
            "action_result": self.action_result.to_dict() if self.action_result else None,
            "action_results": [result.to_dict() for result in self.action_results],
            "notification_result": asdict(self.notification_result) if self.notification_result else None,
            "goal": asdict(self.goal) if self.goal else None,
            "outcome": self.outcome,
            "trace": [asdict(item) for item in self.trace],
        }
