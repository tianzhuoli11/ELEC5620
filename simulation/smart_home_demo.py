"""Command-line acceptance demo for AR-02 / UC-02."""

from __future__ import annotations

import argparse
import json

from domains.smart_home_control import (
    default_device_states,
    resume_smart_home_confirmation,
    run_smart_home_control,
)
from simulation.devices import SimulatedDeviceTool
from simulation.events import make_user_goal_event


SCENARIOS = {
    "good-night": "I'm going to sleep",
    "away": "I'm leaving home",
    "relax": "Relax mode",
    "direct": "Turn off the bedroom light, close the curtain, lock the front door, and set the air conditioner to 22 degrees",
    "sensitive": "Unlock the front door",
    "sensitive-approved": "Unlock the front door",
    "sensitive-declined": "Unlock the front door",
    "ambiguous": "Make the house better",
}


def run_demo(scenario: str = "good-night", offline_device: str | None = None) -> dict:
    tool = SimulatedDeviceTool(default_device_states())
    if offline_device:
        tool.offline.add(offline_device)
    result = run_smart_home_control(
        make_user_goal_event(SCENARIOS[scenario]),
        device_tool=tool,
        record_path=None,
    )
    initial_outcome = result.outcome
    if scenario == "sensitive-approved":
        result = resume_smart_home_confirmation(result, approved=True, device_tool=tool, record_path=None)
    elif scenario == "sensitive-declined":
        result = resume_smart_home_confirmation(result, approved=False, device_tool=tool, record_path=None)
    return {
        "initial_outcome": initial_outcome,
        "workflow": result.to_dict(),
        "final_device_states": tool.states,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a simulated Smart Home Control scenario")
    parser.add_argument("--scenario", choices=SCENARIOS, default="good-night")
    parser.add_argument("--offline", help="Optional simulated device ID to make unavailable")
    args = parser.parse_args()
    print(json.dumps(run_demo(args.scenario, args.offline), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
