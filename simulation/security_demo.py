"""Command-line UC-04 demo using the shared LangGraph workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from domains.home_security.integration import monitor_security_workflow, resume_security_workflow
from simulation.security_scenarios import SCENARIOS, make_security_scenario

DEFAULT_RECORD_PATH = Path("data/runtime/security_events.jsonl")


def main() -> None:
    parser = argparse.ArgumentParser(description="Assess fictional Home Security observations")
    parser.add_argument("--scenario", choices=tuple(SCENARIOS), default="normal")
    parser.add_argument("--output", type=Path, default=DEFAULT_RECORD_PATH)
    parser.add_argument("--use-campus-llm", action="store_true", help="Request real campus LLM advice")
    parser.add_argument("--reply", choices=("approve", "reject", "timeout"),
                        help="Resolve a MEDIUM confirmation; timeout simulates no reply")
    parser.add_argument("--device-failure", action="store_true", help="Make simulated response devices offline")
    args = parser.parse_args()

    provider = None
    if args.use_campus_llm:
        from domains.home_security.llm import propose_security_risk
        from services.campus_proxy import CampusProxyConfig

        try:
            config = CampusProxyConfig.from_environment()
        except ValueError as exc:
            parser.error(str(exc))
        provider = lambda event: propose_security_risk(event, config)

    event = make_security_scenario(args.scenario)
    offline = args.device_failure or args.scenario == "device_failure"
    result = monitor_security_workflow(
        event, record_path=args.output, proposal_provider=provider,
        offline_devices=("appliance", "gas_valve", "water_valve", "security_lights", "siren") if offline else (),
    )
    if args.reply:
        if result.workflow.pending_confirmation is None:
            parser.error("--reply requires a MEDIUM scenario awaiting confirmation")
        result = resume_security_workflow(
            result, None if args.reply == "timeout" else args.reply,
            record_path=args.output,
        )
    print(json.dumps({
        "scenario": args.scenario, "event": event.to_dict(),
        "assessment": result.assessment.to_dict(),
        "workflow": result.workflow.to_dict(),
        "classification_ms": result.classification_ms,
        "record_path": str(args.output),
    }, indent=2))
    print("Fictional simulated sensors, notifications and devices; no real hardware or owner message.")


if __name__ == "__main__":
    main()
