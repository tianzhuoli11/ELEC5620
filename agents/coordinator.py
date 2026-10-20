"""Route events and coordinate optional notifications."""

from __future__ import annotations

from domains.base import DomainRegistry
from models import Event, GoalInterpretation, NotificationRequest, NotificationResult
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
