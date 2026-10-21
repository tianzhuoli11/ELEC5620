"""Map Energy & Comfort observations into the existing shared workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agents.graph import SmartHomeWorkflow
from models import (
    DeviceObservation, EnergyProfile, Event, HomeContext, HomeEnvironment, HomeMode,
    MonitoringDecision, RiskAssessment, UserPreference, WorkflowResult,
)
from tools.device import DeviceTool

from .monitoring import EnergyComfortAssessment, assess_energy_comfort


EVENT_TYPE = "energy_comfort_observation"
CONTEXT_KEY = "energy_comfort"


class _NoDeviceDispatch:
    def dispatch(self, request: object) -> object:
        raise AssertionError("Energy & Comfort assessment must not dispatch a device")

    def read_state(self, device_id: str) -> dict[str, Any]:
        raise AssertionError("Energy & Comfort assessment must not read device state through DeviceTool")


def _single_reading(event: Event, reading_type: str, unit: str) -> Any | None:
    matches = [item for item in event.readings if item.reading_type == reading_type]
    if len(matches) > 1:
        raise ValueError(f"event must not contain duplicate {reading_type} readings")
    if not matches:
        return None
    if matches[0].unit != unit:
        raise ValueError(f"{reading_type} must use unit {unit}")
    return matches[0].value


def context_from_event(event: Event) -> HomeContext:
    """Normalize one event while rejecting duplicate observation sources."""

    if event.event_type != EVENT_TYPE:
        raise ValueError(f"unsupported energy event type: {event.event_type}")
    raw = event.context.get(CONTEXT_KEY, {})
    if not isinstance(raw, dict):
        raise ValueError(f"event context {CONTEXT_KEY} must be a dictionary")
    duplicate_keys = {"environment", "temperature_c", "occupied", "occupancy"}.intersection(raw)
    if duplicate_keys:
        raise ValueError("temperature and occupancy belong only in event readings")
    if raw.get("simulated") is not event.simulated:
        raise ValueError("context simulation marker must match event.simulated")

    temperature = _single_reading(event, "indoor_temperature", "C")
    occupied = _single_reading(event, "occupancy", "boolean")
    environment = HomeEnvironment(temperature_c=temperature, occupied=occupied)

    preference_raw = raw.get("preference")
    if preference_raw is not None and not isinstance(preference_raw, dict):
        raise ValueError("preference context must be a dictionary or None")
    preference = UserPreference(**preference_raw) if preference_raw is not None else None

    energy_raw = raw.get("energy")
    if energy_raw is not None and not isinstance(energy_raw, dict):
        raise ValueError("energy context must be a dictionary or None")
    energy = EnergyProfile(**energy_raw) if energy_raw is not None else None

    mode_raw = raw.get("home_mode")
    try:
        mode = HomeMode(mode_raw) if mode_raw is not None else None
    except ValueError as exc:
        raise ValueError("home_mode must be HOME, AWAY, SLEEP or None") from exc

    devices_raw = raw.get("devices", [])
    if not isinstance(devices_raw, list) or not all(isinstance(item, dict) for item in devices_raw):
        raise ValueError("devices context must be a list of dictionaries")
    devices = tuple(DeviceObservation(**item) for item in devices_raw)
    return HomeContext(environment, preference, energy, mode, devices, event.simulated)


class EnergyComfortHandler:
    domain = "energy_comfort"

    def __init__(self) -> None:
        self.energy_assessment: EnergyComfortAssessment | None = None

    def supports(self, event: Event) -> bool:
        return event.event_type == EVENT_TYPE

    def assess(self, event: Event) -> MonitoringDecision:
        domain_result = assess_energy_comfort(event.event_id, context_from_event(event))
        self.energy_assessment = domain_result
        risk = "LOW" if domain_result.decision == "NO_ADJUSTMENT" else "MEDIUM"
        evidence = "; ".join((
            f"decision={domain_result.decision}", f"policy={domain_result.policy}",
            *(f"evidence:{item}" for item in domain_result.evidence),
            *(f"missing:{item}" for item in domain_result.missing_fields),
        ))
        return MonitoringDecision(assessment=RiskAssessment(
            event_id=event.event_id,
            domain=self.domain,
            risk_level=risk,
            rationale=domain_result.rationale,
            evidence=evidence,
        ))


@dataclass(frozen=True)
class EnergyComfortWorkflowOutcome:
    assessment: EnergyComfortAssessment
    workflow: WorkflowResult


def monitor_energy_comfort_workflow(
    event: Event, *, device_tool: DeviceTool | None = None,
) -> EnergyComfortWorkflowOutcome:
    """Run the real coordinator/monitoring path without actions or notifications."""

    handler = EnergyComfortHandler()
    safe_tool = device_tool if device_tool is not None else _NoDeviceDispatch()
    workflow = SmartHomeWorkflow([handler], safe_tool).run(event)
    if handler.energy_assessment is None:
        raise RuntimeError("Energy & Comfort handler did not produce an assessment")
    return EnergyComfortWorkflowOutcome(handler.energy_assessment, workflow)
