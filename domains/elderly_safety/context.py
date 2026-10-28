"""Collect fall context from an Event and produce a de-identified view for the LLM.

UC-01 step 2: location, time of day, current home mode and recent activity.
NFR-03: nothing sent to the external model may identify the resident, the
address or contacts. `FallContext.for_llm()` is the only thing that may be
placed in a prompt.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from models.events import Event

# Reading types the fall sensor / motion sensor may report. Jinjing's
# SensorReading uses `reading_type` + `unit`.
READING_IMPACT = "fall_impact"            # bool
READING_INACTIVITY = "seconds_without_motion"  # s
READING_POSTURE = "posture"               # "floor" | "upright" | "unknown"

TIME_OF_DAY = ("night", "morning", "day", "evening")


@dataclass(frozen=True)
class FallContext:
    impact_detected: bool | None
    seconds_without_motion: float | None
    posture: str
    location: str
    time_of_day: str
    home_mode: str
    recent_activity: str
    simulated: bool
    missing: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def for_llm(self) -> dict[str, Any]:
        """De-identified subset for the proposal prompt (NFR-03).

        Location is reduced to a room category and never a street address;
        no resident name, age, contacts or event IDs are included.
        """
        return {
            "impact_detected": self.impact_detected,
            "seconds_without_motion": self.seconds_without_motion,
            "posture": self.posture,
            "room_category": _room_category(self.location),
            "time_of_day": self.time_of_day,
            "home_mode": self.home_mode,
            "recent_activity": self.recent_activity,
        }


def _reading(event: Event, reading_type: str):
    matches = [r for r in event.readings if r.reading_type == reading_type]
    return matches[0].value if len(matches) == 1 else None


def _room_category(location: str) -> str:
    text = location.lower()
    for key in ("bathroom", "bedroom", "kitchen", "stairs", "hall", "living", "garden", "garage"):
        if key in text:
            return key
    return "other" if text and text != "unknown" else "unknown"


def time_of_day_for(timestamp: str) -> str:
    hour = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).hour
    if hour < 6:
        return "night"
    if hour < 12:
        return "morning"
    if hour < 18:
        return "day"
    return "evening"


def collect_context(event: Event) -> FallContext:
    """Never invents a value: unknown facts stay None/'unknown' and are listed in `missing`."""
    ctx = event.context if isinstance(event.context, dict) else {}
    missing: list[str] = []

    impact = _reading(event, READING_IMPACT)
    if impact is None:
        impact = ctx.get("impact_detected")
    if not isinstance(impact, bool):
        impact = None
        missing.append("impact_detected")

    seconds = _reading(event, READING_INACTIVITY)
    if seconds is None:
        seconds = ctx.get("seconds_without_motion")
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or seconds < 0:
        seconds = None
        missing.append("seconds_without_motion")
    else:
        seconds = float(seconds)

    posture = _reading(event, READING_POSTURE) or ctx.get("posture") or "unknown"
    if posture not in ("floor", "upright", "unknown"):
        posture = "unknown"
    if posture == "unknown":
        missing.append("posture")

    location = str(ctx.get("room") or ctx.get("location") or "unknown")
    home_mode = str(ctx.get("home_mode") or "unknown")
    recent = str(ctx.get("recent_activity") or "unknown")

    return FallContext(
        impact_detected=impact,
        seconds_without_motion=seconds,
        posture=posture,
        location=location,
        time_of_day=(ctx["simulated_time_of_day"] if event.simulated and ctx.get("simulated_time_of_day") in TIME_OF_DAY
                     else time_of_day_for(event.timestamp)),
        home_mode=home_mode,
        recent_activity=recent,
        simulated=event.simulated,
        missing=tuple(missing),
    )
