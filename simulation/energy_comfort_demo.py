"""Offline, repeatable Energy & Comfort examples using the real shared workflow."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import uuid4

from domains.energy_comfort.integration import CONTEXT_KEY, EVENT_TYPE, monitor_energy_comfort_workflow
from models import (
    DeviceObservation, EnergyProfile, Event, HomeContext, HomeEnvironment, HomeMode,
    SensorReading, UserPreference,
)


def make_energy_comfort_event(context: HomeContext) -> Event:
    """Encode environmental observations once in readings and policy input in context."""

    timestamp = datetime.now(timezone.utc).isoformat()
    readings = []
    if context.environment.temperature_c is not None:
        readings.append(SensorReading(
            "simulated-indoor-temperature", "indoor_temperature",
            context.environment.temperature_c, "C", timestamp,
        ))
    if context.environment.occupied is not None:
        readings.append(SensorReading(
            "simulated-occupancy", "occupancy",
            context.environment.occupied, "boolean", timestamp,
        ))
    serialized = context.to_dict()
    serialized.pop("environment")
    return Event(
        event_id=str(uuid4()), event_type=EVENT_TYPE, source="energy-comfort-demo",
        timestamp=timestamp, context={CONTEXT_KEY: serialized},
        simulated=context.simulated, readings=tuple(readings),
    )


def example_contexts() -> dict[str, HomeContext]:
    """Three fictional contexts covering the Stage 1 decision outcomes."""

    return {
        "no_adjustment": HomeContext(
            HomeEnvironment(22.0, True), UserPreference(20.0, 24.0),
            home_mode=HomeMode.HOME, simulated=True,
        ),
        "adjustment_needed": HomeContext(
            HomeEnvironment(27.0, True), UserPreference(20.0, 24.0),
            home_mode=HomeMode.HOME, simulated=True,
        ),
        "insufficient_data": HomeContext(
            HomeEnvironment(27.0, None), UserPreference(20.0, 24.0),
            EnergyProfile(900.0, 400.0), HomeMode.HOME,
            (DeviceObservation("simulated-heater", True, {"power": "on"}),), True,
        ),
    }


def run_examples() -> dict[str, dict]:
    results = {}
    for name, context in example_contexts().items():
        outcome = monitor_energy_comfort_workflow(make_energy_comfort_event(context))
        results[name] = {
            "assessment": outcome.assessment.to_dict(),
            "workflow": outcome.workflow.to_dict(),
        }
    return results


if __name__ == "__main__":
    print(json.dumps(run_examples(), indent=2))
