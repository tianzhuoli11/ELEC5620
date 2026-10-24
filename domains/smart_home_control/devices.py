"""Fictional device inventory used by the Smart Home Control prototype."""

from __future__ import annotations

from typing import Any


BEDROOM_LIGHT = "bedroom-light"
BEDROOM_CURTAIN = "bedroom-curtain"
FRONT_DOOR_LOCK = "front-door-lock"
LIVING_ROOM_AC = "living-room-ac"


def default_device_states() -> dict[str, dict[str, Any]]:
    """Return a fresh, explicitly simulated home state for UC-02 demos."""

    return {
        BEDROOM_LIGHT: {"power": "on", "brightness": 70},
        BEDROOM_CURTAIN: {"position": "open"},
        FRONT_DOOR_LOCK: {"locked": True},
        LIVING_ROOM_AC: {
            "power": "on",
            "mode": "comfort",
            "temperature_c": 24,
        },
    }
