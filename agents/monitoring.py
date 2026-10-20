"""Call the owning domain and validate the messages it returns."""

from __future__ import annotations

from domains.base import DomainRegistry
from models import Event, MonitoringDecision


class MonitoringAgent:
    def __init__(self, registry: DomainRegistry) -> None:
        self.registry = registry

    def assess(self, event: Event, domain: str) -> MonitoringDecision:
        handler = self.registry.resolve(event)
        if handler.domain != domain:
            raise ValueError("routed domain does not match the owning handler")
        decision = handler.assess(event)
        assessment = decision.assessment
        if assessment.event_id != event.event_id or assessment.domain != domain:
            raise ValueError("assessment must preserve the event ID and domain")
        if any(request.event_id != event.event_id for request in decision.actions):
            raise ValueError("action request must preserve the event ID")
        if decision.notification_request and decision.notification_request.event_id != event.event_id:
            raise ValueError("notification request must preserve the event ID")
        return decision
