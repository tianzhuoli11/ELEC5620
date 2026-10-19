"""Reusable simulated sensor-event factory for all five domains."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from models import Event, SensorReading


def make_sensor_event(
    event_type: str,
    reading_type: str,
    value: int | float | str | bool,
    unit: str,
    *,
    sensor_id: str = "simulated-sensor-1",
    context: dict[str, Any] | None = None,
    observed_at: str | None = None,
) -> Event:
    """Create a fresh simulated event with one sensor reading and a shared ID."""

    timestamp = observed_at or datetime.now(timezone.utc).isoformat()
    reading = SensorReading(sensor_id, reading_type, value, unit, timestamp)
    return Event(
        event_id=str(uuid4()),
        event_type=event_type,
        source=sensor_id,
        timestamp=timestamp,
        context=dict(context or {}),
        simulated=True,
        readings=(reading,),
    )
