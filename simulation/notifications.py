"""Local notification outcome for fictional, offline demonstrations."""

from __future__ import annotations

from models import NotificationRequest, NotificationResult


class SimulatedNotificationService:
    def send(self, request: NotificationRequest) -> NotificationResult:
        if not request.simulated:
            return NotificationResult(
                request.event_id, "UNAVAILABLE", "Real notification delivery is not configured",
            )
        return NotificationResult(
            request.event_id, "SIMULATED", "Fictional owner alert recorded locally; no external message sent",
        )
