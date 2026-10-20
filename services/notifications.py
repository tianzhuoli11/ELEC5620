"""Notification adapter contract; no real sender is included in the baseline."""

from __future__ import annotations

from typing import Protocol

from models import NotificationRequest, NotificationResult


class NotificationService(Protocol):
    def send(self, request: NotificationRequest) -> NotificationResult:
        """Report the actual send outcome, never presumed acknowledgement."""
