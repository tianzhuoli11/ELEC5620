"""Run a repeatable Sprint 0 pet monitoring demonstration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from domains.pet_care.integration import monitor_pet_workflow
from models import Event
from simulation.events import make_sensor_event

DEFAULT_RECORD_PATH = Path("data/runtime/pet_events.jsonl")


def make_pet_scenario(name: str) -> Event:
    if name == "empty_bowl":
        return make_sensor_event(
            "pet_bowl_level", "food_level_percent", 0, "%",
            sensor_id="simulated-pet-bowl", context={"pet_id": "fictional-pet-1"},
        )
    if name == "unusual_inactivity":
        return make_sensor_event(
            "pet_inactivity", "inactive_minutes", 150, "min",
            sensor_id="simulated-pet-motion", context={"pet_id": "fictional-pet-1"},
        )
    if name == "normal_activity":
        return make_sensor_event(
            "pet_inactivity", "inactive_minutes", 5, "min",
            sensor_id="simulated-pet-motion", context={"pet_id": "fictional-pet-1"},
        )
    raise ValueError(f"unknown scenario: {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a simulated pet-monitoring event")
    parser.add_argument("--scenario", choices=("empty_bowl", "unusual_inactivity", "normal_activity"), default="empty_bowl")
    parser.add_argument("--output", type=Path, default=DEFAULT_RECORD_PATH, help="Local JSONL record path")
    parser.add_argument("--use-campus-llm", action="store_true", help="Call the course API proxy before rule validation")
    args = parser.parse_args()
    event = make_pet_scenario(args.scenario)
    proposal_provider = None
    if args.use_campus_llm:
        from services.campus_proxy import CampusProxyConfig, propose_pet_risk

        try:
            config = CampusProxyConfig.from_environment()
        except ValueError as exc:
            parser.error(str(exc))
        proposal_provider = lambda observation: propose_pet_risk(observation, config)
    result = monitor_pet_workflow(event, record_path=args.output, proposal_provider=proposal_provider)
    print(json.dumps({"event": event.to_dict(), "assessment": result.assessment.to_dict(),
                      "workflow": result.workflow.to_dict(), "record_path": str(args.output)}, indent=2))
    print("Simulated input only. Alerts, when needed, are local-only; no external notification or feeder action occurred.")


if __name__ == "__main__":
    main()
