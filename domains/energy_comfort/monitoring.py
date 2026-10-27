"""Deterministic Energy & Comfort assessment with no device side effects."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from models import HomeContext


AdjustmentDecision = Literal["ADJUSTMENT_NEEDED", "NO_ADJUSTMENT", "INSUFFICIENT_DATA"]


@dataclass(frozen=True)
class EnergyComfortAssessment:
    event_id: str
    decision: AdjustmentDecision
    rationale: str
    evidence: tuple[str, ...]
    missing_fields: tuple[str, ...]
    policy: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_energy_comfort(event_id: str, context: HomeContext) -> EnergyComfortAssessment:
    """Apply explicit comfort or unoccupied-energy rules to normalized context."""

    environment = context.environment
    if environment.occupied is None:
        return EnergyComfortAssessment(
            event_id, "INSUFFICIENT_DATA",
            "Occupancy is unknown, so neither occupied comfort nor unoccupied energy policy can be selected.",
            (), ("environment.occupied",), "occupancy_route_required",
        )

    if environment.occupied:
        missing = []
        if environment.temperature_c is None:
            missing.append("environment.temperature_c")
        if context.preference is None or context.preference.temperature_min_c is None:
            missing.append("preference.temperature_min_c")
        if context.preference is None or context.preference.temperature_max_c is None:
            missing.append("preference.temperature_max_c")
        if missing:
            return EnergyComfortAssessment(
                event_id, "INSUFFICIENT_DATA",
                "Occupied comfort cannot be assessed without temperature and both preference bounds.",
                ("occupied=True",), tuple(missing), "occupied_comfort_inclusive_range",
            )

        temperature = environment.temperature_c
        minimum = context.preference.temperature_min_c
        maximum = context.preference.temperature_max_c
        evidence = (
            "occupied=True", f"temperature_c={temperature:g}",
            f"preferred_range_c=[{minimum:g}, {maximum:g}]",
        )
        if minimum <= temperature <= maximum:
            return EnergyComfortAssessment(
                event_id, "NO_ADJUSTMENT",
                "For the observed temperature-comfort target, the temperature is inside the inclusive preferred range for an occupied home.",
                evidence, (), "occupied_comfort_inclusive_range",
            )
        direction = "above" if temperature > maximum else "below"
        return EnergyComfortAssessment(
            event_id, "ADJUSTMENT_NEEDED",
            f"The observed temperature is {direction} the preferred range for an occupied home.",
            evidence, (), "occupied_comfort_inclusive_range",
        )

    energy = context.energy
    missing = []
    if energy is None or energy.current_power_w is None:
        missing.append("energy.current_power_w")
    if energy is None or energy.unoccupied_power_limit_w is None:
        missing.append("energy.unoccupied_power_limit_w")
    if missing:
        return EnergyComfortAssessment(
            event_id, "INSUFFICIENT_DATA",
            "The home is known to be unoccupied, but explicit power evidence or its policy limit is missing.",
            ("occupied=False",), tuple(missing), "unoccupied_power_signal_with_device_observation",
        )

    evidence = (
        "occupied=False", f"current_power_w={energy.current_power_w:g}",
        f"unoccupied_power_limit_w={energy.unoccupied_power_limit_w:g}",
    )
    if energy.current_power_w <= energy.unoccupied_power_limit_w:
        return EnergyComfortAssessment(
            event_id, "NO_ADJUSTMENT",
            "Observed whole-home power did not trigger the configured simulated unoccupied-limit rule; other energy waste was not assessed.",
            evidence, (), "unoccupied_power_signal_with_device_observation",
        )

    candidate_devices = tuple(
        item.device_id for item in context.devices
        if item.available is True and item.observed_state.get("power") == "on"
    )
    if not candidate_devices:
        return EnergyComfortAssessment(
            event_id, "INSUFFICIENT_DATA",
            "Power exceeds the unoccupied limit, but there is no available powered-device observation to investigate further.",
            evidence, ("devices.available_powered_device",),
            "unoccupied_power_signal_with_device_observation",
        )
    return EnergyComfortAssessment(
        event_id, "ADJUSTMENT_NEEDED",
        "Further energy assessment is needed: power exceeds the simulated unoccupied limit and an available device is observed on; this correlation does not identify the cause or authorize control.",
        evidence + ("available_powered_device_candidates=" + ",".join(candidate_devices),), (),
        "unoccupied_power_signal_with_device_observation",
    )
