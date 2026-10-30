"""Post-action environmental observation for SCRUM-32 AC3.

DeviceAutomationAgent verifies device readback independently; this module
covers room-level temperature, occupancy, and whole-home power only when a
separate observation source exists. It never reuses pre-action event readings.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Literal

from models import WorkflowResult

PostActionStatus = Literal["UNKNOWN_NOT_MEASURED", "MEASURED"]

EnvironmentProbe = Callable[[WorkflowResult], tuple[dict[str, Any], ...] | None]


@dataclass(frozen=True)
class PostActionEnvironmentObservation:
    status: PostActionStatus
    observed_at: str
    source: str
    detail: str
    readings: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["readings"] = list(self.readings)
        return payload


def environment_effect_text(observation: PostActionEnvironmentObservation) -> str:
    prefix = observation.status
    return (
        f"{prefix}: {observation.detail} "
        f"(source={observation.source}; observed_at={observation.observed_at})"
    )


def assess_post_action_environment(
    *,
    workflow: WorkflowResult,
    planned_actions: int,
    environment_probe: EnvironmentProbe | None = None,
    now: datetime | None = None,
) -> PostActionEnvironmentObservation:
    """Record post-action environment evidence or an explicit not-measured boundary."""

    observed_at = (now or datetime.now(timezone.utc)).isoformat()
    if planned_actions <= 0 or not workflow.action_results:
        return PostActionEnvironmentObservation(
            status="UNKNOWN_NOT_MEASURED",
            observed_at=observed_at,
            source="not_applicable_no_device_execution",
            detail="No device plan ran; post-action environment was not measured.",
        )

    if environment_probe is not None:
        probe_readings = environment_probe(workflow)
        if probe_readings:
            return PostActionEnvironmentObservation(
                status="MEASURED",
                observed_at=observed_at,
                source="independent_environment_probe",
                detail="Independent post-action environmental readings were supplied.",
                readings=tuple(probe_readings),
            )

    return PostActionEnvironmentObservation(
        status="UNKNOWN_NOT_MEASURED",
        observed_at=observed_at,
        source="no_independent_environment_sensor_feed",
        detail=(
            "Device action results were verified independently, but this repository "
            "does not expose a separate post-action temperature, occupancy, or "
            "whole-home power observation. Pre-action event readings were not reused."
        ),
    )
