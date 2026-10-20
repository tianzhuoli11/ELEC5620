"""Small integration boundary for independently developed domains."""

from __future__ import annotations

from typing import Protocol

from models import Event, GoalInterpretation, GoalPlan, MonitoringDecision


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
