"""Boundary for a goal interpreter; implementations must not execute actions."""

from __future__ import annotations

from typing import Protocol

from models import Event, GoalInterpretation


class GoalInterpreter(Protocol):
    def interpret(self, event: Event) -> GoalInterpretation:
        """Turn a user-goal event into a proposal for domain policy validation."""
