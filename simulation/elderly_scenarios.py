"""SIMULATED elderly-safety fall scenarios (UC-01 trigger: sudden motion then inactivity).

Each scenario is a fresh Event with a unique ID. Static copies with the
expected results live in data/samples/elderly_fall_*.json.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from models.events import Event, SensorReading

SCENARIOS = {
    # name: (impact, seconds_without_motion, posture, room, hour, expected_rule_level)
    "high_floor": (True, 90, "floor", "bathroom", 14, "HIGH"),
    "medium_wait": (True, 30, "unknown", "living room", 14, "MEDIUM"),
    "low_dropped_object": (True, 5, "upright", "kitchen", 14, "LOW"),
    "medium_missing_duration": (True, None, "unknown", "bedroom", 14, "MEDIUM"),
    "medium_night_uplift": (True, 5, "unknown", "bedroom", 3, "MEDIUM"),
}


def make_fall_scenario(name: str, observed_at: str | None = None) -> Event:
    impact, seconds, posture, room, hour, _expected = SCENARIOS[name]
    timestamp = observed_at or datetime(2026, 10, 20, hour, 0, tzinfo=timezone.utc).isoformat()
    readings = [SensorReading("simulated-fall-sensor-1", "fall_impact", impact, "bool", timestamp)]
    if seconds is not None:
        readings.append(SensorReading("simulated-motion-sensor-1", "seconds_without_motion", seconds, "s", timestamp))
    if posture != "unknown":
        readings.append(SensorReading("simulated-posture-sensor-1", "posture", posture, "category", timestamp))
    return Event(
        event_id=str(uuid4()),
        event_type="fall_detected",
        source="simulated-fall-sensor-1",
        timestamp=timestamp,
        context={"room": room, "home_mode": "home", "recent_activity": "walking", "scenario": name},
        simulated=True,
        readings=tuple(readings),
    )
