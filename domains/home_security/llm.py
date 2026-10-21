"""Security-specific prompt using the existing shared campus proxy transport."""

from __future__ import annotations

import json
from typing import Any

from models import Event
from services.campus_proxy import CampusProxyConfig, request_json_chat

from .monitoring import EVENT_TYPE, READING_TYPES


def propose_security_risk(event: Event, config: CampusProxyConfig) -> dict[str, Any]:
    """Send only allowlisted, fictional observations; never send whole context."""
    if event.event_type != EVENT_TYPE or not event.simulated:
        raise ValueError("campus advice accepts simulated security observations only")
    observations = []
    for reading in event.readings:
        if reading.reading_type not in READING_TYPES:
            continue
        value = reading.value
        safe_value = int(value) if isinstance(value, (bool, int, float)) and value in (0, 1) else None
        observations.append({"type": reading.reading_type, "value": safe_value})

    context = event.context
    devices = context.get("device_status")
    devices = devices if isinstance(devices, dict) else {}
    safe_context = {
        "home_mode": context.get("home_mode") if context.get("home_mode") in ("HOME", "AWAY") else "UNKNOWN",
        "recent_activity": context.get("recent_activity") if context.get("recent_activity") in ("EXPECTED", "NONE") else "UNKNOWN",
        "authorized_entry": context.get("authorized_entry") if isinstance(context.get("authorized_entry"), bool) else None,
        "front_door_lock": devices.get("front_door_lock") if devices.get("front_door_lock") in ("locked", "unlocked") else "unknown",
        "water_valve": devices.get("water_valve") if devices.get("water_valve") in ("open", "closed") else "unknown",
    }
    return request_json_chat([
        {
            "role": "system",
            "content": (
                "Assess fictional smart-home security observations. Return one JSON object "
                "with risk_level (LOW, MEDIUM, HIGH) and a short rationale. "
                "This is advice only: do not claim an alarm, notification, or device action occurred."
            ),
        },
        {"role": "user", "content": json.dumps({"readings": observations, "context": safe_context})},
    ], config)
