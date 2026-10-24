"""Typed fictional device inventory used by the Smart Home Control prototype."""

from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from typing import Any


BEDROOM_LIGHT = "bedroom-light"
BEDROOM_CURTAIN = "bedroom-curtain"
FRONT_DOOR_LOCK = "front-door-lock"
LIVING_ROOM_AC = "living-room-ac"


@dataclass(frozen=True)
class DeviceContext:
    """Latest observable state kept separately from the device definition."""

    device_id: str
    available: bool
    state: dict[str, Any]
    energy_watts: float | None = None


@dataclass(frozen=True)
class SmartDevice(ABC):
    """Common Stage 1 device model used behind the DeviceControlTool boundary."""

    device_id: str
    name: str
    location: str

    @abstractmethod
    def initial_state(self) -> dict[str, Any]:
        """Return a fresh simulated state for this device type."""

    def initial_context(self) -> DeviceContext:
        return DeviceContext(self.device_id, True, self.initial_state())


@dataclass(frozen=True)
class SmartLight(SmartDevice):
    def initial_state(self) -> dict[str, Any]:
        return {"power": "on", "brightness": 70}


@dataclass(frozen=True)
class SmartCurtain(SmartDevice):
    def initial_state(self) -> dict[str, Any]:
        return {"position": "open"}


@dataclass(frozen=True)
class SmartLock(SmartDevice):
    def initial_state(self) -> dict[str, Any]:
        return {"locked": True}


@dataclass(frozen=True)
class AirConditioner(SmartDevice):
    def initial_state(self) -> dict[str, Any]:
        return {"power": "on", "mode": "comfort", "temperature_c": 24}


DEVICE_INVENTORY: tuple[SmartDevice, ...] = (
    SmartLight(BEDROOM_LIGHT, "Bedroom light", "bedroom"),
    SmartCurtain(BEDROOM_CURTAIN, "Bedroom curtain", "bedroom"),
    SmartLock(FRONT_DOOR_LOCK, "Front-door lock", "entrance"),
    AirConditioner(LIVING_ROOM_AC, "Living-room air conditioner", "living room"),
)


def default_device_contexts() -> dict[str, DeviceContext]:
    """Return Stage 1 DeviceContext objects for the fictional inventory."""

    return {device.device_id: device.initial_context() for device in DEVICE_INVENTORY}


def default_device_states() -> dict[str, dict[str, Any]]:
    """Return a fresh, explicitly simulated home state for UC-02 demos."""

    return {
        device_id: deepcopy(context.state)
        for device_id, context in default_device_contexts().items()
    }
