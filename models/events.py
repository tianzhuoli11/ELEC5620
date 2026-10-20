"""Small, dependency-free contracts for sensor observations and events."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


def _aware_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be an ISO 8601 date and time") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a time zone")


@dataclass(frozen=True)
class SensorReading:
    """One observed value; simulated inputs are identified by their parent event."""

    sensor_id: str
    reading_type: str
    value: int | float | str | bool
    unit: str
    observed_at: str

    def __post_init__(self) -> None:
        if not self.sensor_id or not self.reading_type:
            raise ValueError("sensor_id and reading_type are required")
        if isinstance(self.value, float) and not -float("inf") < self.value < float("inf"):
            raise ValueError("sensor value must be finite")
        _aware_timestamp(self.observed_at)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Event:
    """A traceable input for the shared MonitoringAgent to route by domain."""

    event_id: str
    event_type: str
    source: str
    timestamp: str
    context: dict[str, Any] = field(default_factory=dict)
    simulated: bool = False
    readings: tuple[SensorReading, ...] = ()

    def __post_init__(self) -> None:
        if not self.event_id or not self.event_type or not self.source:
            raise ValueError("event_id, event_type and source are required")
        _aware_timestamp(self.timestamp)
        if not isinstance(self.simulated, bool):
            raise ValueError("simulated must be a boolean")
        if not isinstance(self.context, dict):
            raise ValueError("context must be a dictionary")
        if not all(isinstance(item, SensorReading) for item in self.readings):
            raise ValueError("readings must contain SensorReading values")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
