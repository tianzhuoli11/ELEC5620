"""Route events and coordinate optional notifications."""

from __future__ import annotations

from domains.base import ConfirmationHandler, DomainRegistry
from models import (
    ConfirmationReply, Event, GoalInterpretation, MonitoringDecision, NotificationRequest,
    NotificationResult, PendingConfirmation, RiskAssessment,
)
from services.goals import GoalInterpreter
from services.notifications import NotificationService


class HomeCoordinatorAgent:
    def __init__(
        self,
        registry: DomainRegistry,
        notifier: NotificationService | None = None,
        goal_interpreter: GoalInterpreter | None = None,
    ) -> None:
        self.registry = registry
        self.notifier = notifier
        self.goal_interpreter = goal_interpreter

    def route(self, event: Event) -> str:
        return self.registry.resolve(event).domain

    def route_goal(self, event: Event) -> GoalInterpretation:
        if self.goal_interpreter is None:
            raise ValueError("goal interpreter is not configured")
        text = event.context.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("user goal text is required")
        goal = self.goal_interpreter.interpret(event)
        if goal.event_id != event.event_id:
            raise ValueError("goal interpretation must preserve the event ID")
        if goal.clarification_question:
            return goal
        self.registry.resolve_goal(goal)
        return goal

    def notify(self, request: NotificationRequest) -> NotificationResult:
        if self.notifier is None:
            return NotificationResult(request.event_id, "UNAVAILABLE", "No notification adapter is configured")
        try:
            result = self.notifier.send(request)
        except Exception as exc:
            return NotificationResult(request.event_id, "FAILED", f"Notification adapter failed: {type(exc).__name__}")
        if result.event_id != request.event_id:
            return NotificationResult(request.event_id, "FAILED", "Notification result event ID mismatch")
        return result

    # --- resident confirmation (UC-01 steps 5-6, SCRUM-24) -----------------

    def ask_resident(self, event: Event, assessment: RiskAssessment, handler: ConfirmationHandler, attempt: int) -> PendingConfirmation:
        pending = handler.confirmation_question(event, assessment, attempt)
        if pending.event_id != event.event_id or pending.attempt != attempt:
            raise ValueError("confirmation question must preserve the event ID and attempt")
        return pending

    def interpret_reply(self, event: Event, handler: ConfirmationHandler, attempt: int, reply: str | None) -> ConfirmationReply:
        """A missing reply is a timeout; the domain never turns silence into 'safe'."""
        if reply is None:
            return ConfirmationReply(event.event_id, attempt, None, "timeout", "coordinator")
        result = handler.interpret_reply(event, attempt, reply)
        if result.event_id != event.event_id or result.verdict not in ("safe", "help", "unclear"):
            raise ValueError("reply interpretation must preserve the event ID and use a known verdict")
        return result

    def escalate(self, event: Event, assessment: RiskAssessment, handler: ConfirmationHandler, replies: tuple[ConfirmationReply, ...]) -> MonitoringDecision:
        decision = handler.escalate(event, assessment, replies)
        if decision.assessment.event_id != event.event_id or decision.assessment.requires_human_review:
            raise ValueError("escalation must preserve the event ID and must not request human review again")
        if any(request.event_id != event.event_id for request in decision.actions):
            raise ValueError("escalation action request must preserve the event ID")
        return decision
