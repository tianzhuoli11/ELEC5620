"""Repeatable OR-06 inputs; these are fictional, never government API data."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from domains.home_security.external_warnings import (
    HOUSEHOLD_AREA, TRUSTED_SOURCE, WARNING_EVENT_TYPE,
)
from models import Event


WARNING_SCENARIOS = {
    "relevant_earthquake": ("Earthquake near home · SIMULATED", "EARTHQUAKE", "EMERGENCY", [HOUSEHOLD_AREA], TRUSTED_SOURCE),
    "relevant_flood": ("Flood near home · SIMULATED", "FLOOD", "WARNING", [HOUSEHOLD_AREA], TRUSTED_SOURCE),
    "relevant_storm": ("Severe storm near home · SIMULATED", "SEVERE_STORM", "EMERGENCY", [HOUSEHOLD_AREA], TRUSTED_SOURCE),
    "relevant_bushfire": ("Bushfire near home · SIMULATED", "BUSHFIRE", "EMERGENCY", [HOUSEHOLD_AREA], TRUSTED_SOURCE),
    "irrelevant_flood": ("Flood in another area · SIMULATED", "FLOOD", "EMERGENCY", ["BLUE_MOUNTAINS"], TRUSTED_SOURCE),
    "invalid_source": ("Untrusted storm alert · SIMULATED", "SEVERE_STORM", "EMERGENCY", [HOUSEHOLD_AREA], "simulated-untrusted-feed"),
}


def make_warning_scenario(name: str) -> Event:
    """Build a new active warning from preset input fields, never a preset result."""
    try:
        _, hazard, severity, areas, source_id = WARNING_SCENARIOS[name]
    except KeyError as exc:
        raise ValueError(f"unknown external warning scenario: {name}") from exc
    now = datetime.now(timezone.utc)
    warning = {
        "warning_id": "SIM-" + uuid4().hex[:12],
        "source_id": source_id,
        "hazard_type": hazard,
        "severity": severity,
        "areas": list(areas),
        "issued_at": (now - timedelta(minutes=5)).isoformat(),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
        "simulated": True,
    }
    return Event(
        event_id=str(uuid4()), event_type=WARNING_EVENT_TYPE,
        source=source_id, timestamp=now.isoformat(),
        context={"warning": warning}, simulated=True,
    )
