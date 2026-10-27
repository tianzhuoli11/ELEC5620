"""Fictional, repeatable Home Security inputs for SCRUM-15."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from models import Event, SensorReading
from domains.home_security.monitoring import EVENT_TYPE, READING_TYPES


SCENARIOS = {
    "normal": ("Normal safe state", {}, "HOME", "EXPECTED", True, "locked", "closed"),
    "smoke": ("Smoke or fire alarm", {"smoke_alarm": 1}, "HOME", "NONE", False, "locked", "closed"),
    "device_failure": ("Smoke alarm with offline devices", {"smoke_alarm": 1}, "HOME", "NONE", False, "locked", "closed"),
    "gas": ("Gas leak alarm", {"gas_alarm": 1}, "HOME", "NONE", False, "locked", "closed"),
    "water_leak": ("Water leak with valve open", {"water_leak": 1}, "HOME", "NONE", False, "locked", "open"),
    "appliance_overheat": ("Appliance overheat alarm", {"appliance_overheat_alarm": 1}, "HOME", "NONE", False, "locked", "closed"),
    "appliance_unexpected_run": ("Appliance running unexpectedly", {"appliance_unexpected_run": 1}, "AWAY", "NONE", False, "locked", "closed"),
    "unusual_door": ("Unusual door opening", {"door_open": 1}, "AWAY", "NONE", False, "unlocked", "closed"),
    "unusual_window": ("Unusual window opening", {"window_open": 1}, "AWAY", "NONE", False, "locked", "closed"),
    "abnormal_lock_access": ("Abnormal smart-lock access", {"smart_lock_access_anomaly": 1}, "AWAY", "NONE", False, "locked", "closed"),
    "suspicious_motion": ("Suspicious motion", {"motion_detected": 1}, "AWAY", "NONE", False, "locked", "closed"),
    "suspected_intrusion": ("Door and motion while away", {"door_open": 1, "motion_detected": 1}, "AWAY", "NONE", False, "unlocked", "closed"),
    "window_intrusion": ("Window and motion while away", {"window_open": 1, "motion_detected": 1}, "AWAY", "NONE", False, "locked", "closed"),
}


def make_security_observation(
    readings: dict[str, int | bool], *, home_mode: str = "HOME",
    recent_activity: str = "NONE", authorized_entry: bool = False,
    front_door_lock: str = "locked", water_valve: str = "closed",
) -> Event:
    """Create all supported binary sensor readings from editable fictional inputs."""
    unknown = set(readings) - set(READING_TYPES)
    if unknown:
        raise ValueError(f"unknown security reading types: {sorted(unknown)}")
    timestamp = datetime.now(timezone.utc).isoformat()
    observations = tuple(
        SensorReading(f"simulated-{kind}", kind, readings.get(kind, 0), "state", timestamp)
        for kind in READING_TYPES
    )
    return Event(
        event_id=str(uuid4()), event_type=EVENT_TYPE,
        source="simulated-security-panel", timestamp=timestamp, simulated=True,
        readings=observations,
        context={
            "home_mode": home_mode, "recent_activity": recent_activity,
            "authorized_entry": authorized_entry,
            "device_status": {"front_door_lock": front_door_lock, "water_valve": water_valve},
        },
    )


def make_security_scenario(name: str) -> Event:
    """Return a new event for a named scenario; the preset contains no result."""
    try:
        _, readings, mode, activity, authorised, lock, valve = SCENARIOS[name]
    except KeyError as exc:
        raise ValueError(f"unknown security scenario: {name}") from exc
    return make_security_observation(
        readings, home_mode=mode, recent_activity=activity,
        authorized_entry=authorised, front_door_lock=lock, water_valve=valve,
    )
