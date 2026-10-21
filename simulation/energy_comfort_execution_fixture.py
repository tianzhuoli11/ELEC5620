"""Test-only device execution evidence; not an Energy & Comfort control contract."""

from __future__ import annotations

from typing import Any

from agents.automation import DeviceAutomationAgent
from models import ActionRequest, RiskAssessment
from simulation.devices import SimulatedDeviceTool
from simulation.events import make_sensor_event


FIXTURE_DEVICE_ID = "fictional-test-light"


class _DispatchTimeoutTool(SimulatedDeviceTool):
    def __init__(self) -> None:
        super().__init__({FIXTURE_DEVICE_ID: {"power": "on"}})
        self.read_count = 0

    def dispatch(self, request: ActionRequest):
        self.dispatch_count += 1
        raise TimeoutError("fictional dispatch timeout")

    def read_state(self, device_id: str) -> dict[str, Any]:
        self.read_count += 1
        return super().read_state(device_id)


def run_test_only_execution_cases() -> list[dict[str, Any]]:
    """Exercise gaps not already covered by the shared framework tests."""

    event = make_sensor_event("fixture_event", "fixture", "run", "state")
    assessment = RiskAssessment(
        event.event_id, "energy_comfort_test_fixture", "MEDIUM",
        "Fictional test-only execution", "No production authorization",
    )

    timeout_tool = _DispatchTimeoutTool()
    timeout_request = ActionRequest(
        event.event_id, FIXTURE_DEVICE_ID, "set_state",
        {"power": "off"}, {"power": "off"}, "POLICY", True,
    )
    timeout_result = DeviceAutomationAgent(timeout_tool).execute(
        event, assessment, timeout_request,
    )
    timeout_actual = {
        "accepted": timeout_result.accepted,
        "verified": timeout_result.verified,
        "error": timeout_result.error,
        "dispatch_calls": timeout_tool.dispatch_count,
        "read_calls": timeout_tool.read_count,
        "state_unchanged": timeout_tool.states[FIXTURE_DEVICE_ID] == {"power": "on"},
    }
    timeout_expected = {
        "accepted": False,
        "verified": False,
        "error": "Device dispatch failed: TimeoutError",
        "dispatch_calls": 1,
        "read_calls": 0,
        "state_unchanged": True,
    }

    invalid_tool = SimulatedDeviceTool({FIXTURE_DEVICE_ID: {"power": "on"}})
    invalid_request = ActionRequest(
        event.event_id, FIXTURE_DEVICE_ID, "toggle",
        {"power": "off"}, {"power": "off"}, "POLICY", True,
    )
    invalid_result = DeviceAutomationAgent(invalid_tool).execute(
        event, assessment, invalid_request,
    )
    invalid_actual = {
        "accepted": invalid_result.accepted,
        "verified": invalid_result.verified,
        "error": invalid_result.error,
        "dispatch_calls": invalid_tool.dispatch_count,
        "state_unchanged": invalid_tool.states[FIXTURE_DEVICE_ID] == {"power": "on"},
    }
    invalid_expected = {
        "accepted": False,
        "verified": False,
        "error": "Unsupported simulated action",
        "dispatch_calls": 1,
        "state_unchanged": True,
    }

    return [
        {
            "case_id": "test_only_dispatch_timeout",
            "scope": "TEST_ONLY_SIMULATION",
            "expected": timeout_expected,
            "actual": timeout_actual,
            "test_result": "PASS" if timeout_actual == timeout_expected else "FAIL",
        },
        {
            "case_id": "test_only_invalid_action_schema",
            "scope": "TEST_ONLY_SIMULATION",
            "expected": invalid_expected,
            "actual": invalid_actual,
            "test_result": "PASS" if invalid_actual == invalid_expected else "FAIL",
        },
    ]
