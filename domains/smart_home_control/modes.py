"""Verified HomeMode state shared with later monitoring events (OR-02 / UC-07)."""

from __future__ import annotations

from dataclasses import dataclass, replace

from models import Event, WorkflowResult


MODE_BY_INTENT = {
    "night_mode": "NIGHT",
    "away_mode": "AWAY",
    "relax_mode": "RELAX",
}


@dataclass
class HomeModeState:
    """Persist the last fully verified mode and expose it as event context."""

    current_mode: str = "HOME"
    previous_mode: str | None = None
    last_event_id: str | None = None

    def enrich_event(self, event: Event) -> Event:
        context = dict(event.context)
        context["home_mode"] = self.current_mode
        return replace(event, context=context)

    def update_from_result(self, result: WorkflowResult) -> bool:
        if result.goal is None or result.outcome != "COMPLETE":
            return False
        requested_mode = MODE_BY_INTENT.get(result.goal.intent)
        if requested_mode is None:
            return False
        self.previous_mode = self.current_mode
        self.current_mode = requested_mode
        self.last_event_id = result.event.event_id
        return True

    def monitoring_context(self) -> dict[str, str]:
        """Context that the shared MonitoringAgent can receive on its next event."""

        return {"home_mode": self.current_mode}
