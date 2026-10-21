"""Small integration boundary for independently developed domains."""

from __future__ import annotations

from typing import Protocol

from models import ConfirmationReply, Event, GoalInterpretation, GoalPlan, MonitoringDecision, PendingConfirmation, RiskAssessment


class DomainHandler(Protocol):
    domain: str

    def supports(self, event: Event) -> bool:
        """Return whether this handler owns the event type."""

    def assess(self, event: Event) -> MonitoringDecision:
        """Return a validated decision without directly calling devices or UI."""


class GoalHandler(DomainHandler, Protocol):
    def supports_goal(self, goal: GoalInterpretation) -> bool:
        """Claim a structured user goal belonging to this domain."""

    def plan_goal(self, event: Event, goal: GoalInterpretation) -> GoalPlan:
        """Validate the goal and return a policy-approved plan."""


class ConfirmationHandler(DomainHandler, Protocol):
    """Optional: a domain whose MEDIUM assessments pause for a resident reply.

    The coordinator calls these; the domain never contacts the resident or a
    device itself. Implemented by Elderly Safety (UC-01 steps 5-6).
    """

    def confirmation_question(self, event: Event, assessment: RiskAssessment, attempt: int) -> PendingConfirmation:
        """Question to ask on this attempt (1-based), with timeout and max attempts."""

    def interpret_reply(self, event: Event, attempt: int, reply: str | None) -> ConfirmationReply:
        """Classify a reply as safe / help / unclear; ``None`` is a timeout."""

    def escalate(self, event: Event, assessment: RiskAssessment, replies: tuple[ConfirmationReply, ...]) -> MonitoringDecision:
        """Actions and notification once help is needed or confirmation failed."""


def supports_confirmation(handler: object) -> bool:
    return all(callable(getattr(handler, name, None)) for name in ("confirmation_question", "interpret_reply", "escalate"))


class DomainRegistry:
    def __init__(self, handlers: list[DomainHandler]) -> None:
        names = [handler.domain for handler in handlers]
        if len(names) != len(set(names)):
            raise ValueError("domain names must be unique")
        self._handlers = tuple(handlers)

    def resolve(self, event: Event) -> DomainHandler:
        matches = [handler for handler in self._handlers if handler.supports(event)]
        if len(matches) != 1:
            raise ValueError(f"expected one handler for {event.event_type}; found {len(matches)}")
        return matches[0]

    def resolve_goal(self, goal: GoalInterpretation) -> GoalHandler:
        matches = [
            handler for handler in self._handlers
            if handler.domain == goal.domain
            and callable(getattr(handler, "supports_goal", None))
            and handler.supports_goal(goal)
        ]
        if len(matches) != 1:
            raise ValueError(f"expected one goal handler for {goal.domain}:{goal.intent}; found {len(matches)}")
        return matches[0]
