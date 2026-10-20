"""In-memory simulated devices; no physical I/O is performed."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from models import ActionRequest
from tools.device import DispatchResult


class SimulatedDeviceTool:
    def __init__(self, initial_states: dict[str, dict[str, Any]]) -> None:
        self.states = deepcopy(initial_states)
        self.offline: set[str] = set()
        self.dispatch_count = 0

    def dispatch(self, request: ActionRequest) -> DispatchResult:
        self.dispatch_count += 1
        if not request.simulated:
            return DispatchResult(False, "Only simulated commands are supported")
        if request.device_id not in self.states:
            return DispatchResult(False, "Unknown simulated device")
        if request.device_id in self.offline:
            return DispatchResult(False, "Simulated device is offline")
        if request.action != "set_state":
            return DispatchResult(False, "Unsupported simulated action")
        if not request.parameters or not set(request.parameters).issubset(self.states[request.device_id]):
            return DispatchResult(False, "Invalid simulated state parameters")
        self.states[request.device_id].update(deepcopy(request.parameters))
        return DispatchResult(True)

    def read_state(self, device_id: str) -> dict[str, Any]:
        if device_id in self.offline:
            raise ConnectionError("Simulated device is offline")
        if device_id not in self.states:
            raise KeyError("Unknown simulated device")
        return deepcopy(self.states[device_id])
