"""Command-line SCRUM-15 demo using the shared LangGraph workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from domains.home_security.integration import monitor_security_workflow
from simulation.security_scenarios import SCENARIOS, make_security_scenario

DEFAULT_RECORD_PATH = Path("data/runtime/security_events.jsonl")


def main() -> None:
    parser = argparse.ArgumentParser(description="Assess fictional Home Security observations")
    parser.add_argument("--scenario", choices=tuple(SCENARIOS), default="normal")
    parser.add_argument("--output", type=Path, default=DEFAULT_RECORD_PATH)
    parser.add_argument("--use-campus-llm", action="store_true", help="Request real campus LLM advice")
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
    result = monitor_security_workflow(event, record_path=args.output, proposal_provider=provider)
    print(json.dumps({
        "scenario": args.scenario, "event": event.to_dict(),
        "assessment": result.assessment.to_dict(),
        "workflow": result.workflow.to_dict(),
        "classification_ms": result.classification_ms,
        "record_path": str(args.output),
    }, indent=2))
    print("Fictional simulated inputs. SCRUM-15 records assessment only; no notification or device action occurred.")


if __name__ == "__main__":
    main()
