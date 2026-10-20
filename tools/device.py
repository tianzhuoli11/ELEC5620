"""Shared device port: dispatch is separate from returned-state verification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from models import ActionRequest


@dataclass(frozen=True)
class DispatchResult:
    accepted: bool
    error: str | None = None


class DeviceTool(Protocol):
    def dispatch(self, request: ActionRequest) -> DispatchResult:
        """Send a command; acceptance alone is not successful execution."""

    def read_state(self, device_id: str) -> dict[str, Any]:
        """Fetch independent returned state for verification."""
