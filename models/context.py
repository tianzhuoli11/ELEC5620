"""Provisional shared home context for cross-domain observations and policy input."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any


def _optional_number(value: int | float | None, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{field_name} must be a finite number or None")
    return float(value)


class HomeMode(str, Enum):
    """Small candidate vocabulary; absence is represented by ``None``."""

    HOME = "HOME"
    AWAY = "AWAY"
    SLEEP = "SLEEP"


@dataclass(frozen=True)
class HomeEnvironment:
    """Latest known indoor conditions; ``None`` means not observed."""

    temperature_c: float | None = None
    occupied: bool | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "temperature_c", _optional_number(self.temperature_c, "temperature_c"))
        if self.occupied is not None and not isinstance(self.occupied, bool):
            raise ValueError("occupied must be True, False or None")

    def to_dict(self) -> dict[str, Any]:
        return {"temperature_c": self.temperature_c, "occupied": self.occupied}


@dataclass(frozen=True)
class UserPreference:
    """An inclusive preferred indoor-temperature range in degrees Celsius."""

    temperature_min_c: float | None = None
    temperature_max_c: float | None = None

    def __post_init__(self) -> None:
        minimum = _optional_number(self.temperature_min_c, "temperature_min_c")
        maximum = _optional_number(self.temperature_max_c, "temperature_max_c")
        object.__setattr__(self, "temperature_min_c", minimum)
        object.__setattr__(self, "temperature_max_c", maximum)
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError("temperature_min_c must not exceed temperature_max_c")

    def to_dict(self) -> dict[str, Any]:
        return {
            "temperature_min_c": self.temperature_min_c,
            "temperature_max_c": self.temperature_max_c,
        }


@dataclass(frozen=True)
class EnergyProfile:
    """Optional whole-home power observation and explicit unoccupied policy limit."""

    current_power_w: float | None = None
    unoccupied_power_limit_w: float | None = None

    def __post_init__(self) -> None:
        current = _optional_number(self.current_power_w, "current_power_w")
        limit = _optional_number(self.unoccupied_power_limit_w, "unoccupied_power_limit_w")
        if current is not None and current < 0:
            raise ValueError("current_power_w must not be negative")
        if limit is not None and limit < 0:
            raise ValueError("unoccupied_power_limit_w must not be negative")
        object.__setattr__(self, "current_power_w", current)
        object.__setattr__(self, "unoccupied_power_limit_w", limit)

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_power_w": self.current_power_w,
            "unoccupied_power_limit_w": self.unoccupied_power_limit_w,
        }


@dataclass(frozen=True)
class DeviceObservation:
    """Observed device availability and state, without command capability."""

    device_id: str
    available: bool | None = None
    observed_state: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.device_id, str) or not self.device_id.strip():
            raise ValueError("device_id is required")
        if self.available is not None and not isinstance(self.available, bool):
            raise ValueError("available must be True, False or None")
        if not isinstance(self.observed_state, dict):
            raise ValueError("observed_state must be a dictionary")
        object.__setattr__(self, "observed_state", dict(self.observed_state))

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "available": self.available,
            "observed_state": dict(self.observed_state),
        }


@dataclass(frozen=True)
class HomeContext:
    """Normalized context shared by domain policy code."""

    environment: HomeEnvironment
    preference: UserPreference | None = None
    energy: EnergyProfile | None = None
    home_mode: HomeMode | None = None
    devices: tuple[DeviceObservation, ...] = ()
    simulated: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.environment, HomeEnvironment):
            raise ValueError("environment must be a HomeEnvironment")
        if self.preference is not None and not isinstance(self.preference, UserPreference):
            raise ValueError("preference must be a UserPreference or None")
        if self.energy is not None and not isinstance(self.energy, EnergyProfile):
            raise ValueError("energy must be an EnergyProfile or None")
        if self.home_mode is not None and not isinstance(self.home_mode, HomeMode):
            raise ValueError("home_mode must be a HomeMode or None")
        if not isinstance(self.simulated, bool):
            raise ValueError("simulated must be a boolean")
        if not all(isinstance(item, DeviceObservation) for item in self.devices):
            raise ValueError("devices must contain DeviceObservation values")
        object.__setattr__(self, "devices", tuple(self.devices))
        identifiers = [item.device_id for item in self.devices]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("device observations must have unique device IDs")

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment": self.environment.to_dict(),
            "preference": self.preference.to_dict() if self.preference else None,
            "energy": self.energy.to_dict() if self.energy else None,
            "home_mode": self.home_mode.value if self.home_mode else None,
            "devices": [item.to_dict() for item in self.devices],
            "simulated": self.simulated,
        }
