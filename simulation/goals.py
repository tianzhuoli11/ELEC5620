"""Explicit, deterministic goal interpreter for offline framework tests only."""

from __future__ import annotations

from models import Event, GoalInterpretation


class DemoGoalInterpreter:
    def interpret(self, event: Event) -> GoalInterpretation:
        text = event.context["text"].strip().casefold()
        if text not in {"good night", "我要睡觉了"}:
            return GoalInterpretation(
                event_id=event.event_id, domain="unresolved", intent="clarify",
                evidence="No exact fictional demo phrase matched; no LLM call",
                clarification_question="This offline demo only understands 'Good night'. What would you like to do?",
            )
        return GoalInterpretation(
            event_id=event.event_id, domain="smart_home_control", intent="night_mode",
            evidence="Exact fictional demo phrase; no LLM call",
        )
