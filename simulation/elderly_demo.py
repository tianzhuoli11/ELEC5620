"""Run a SIMULATED elderly fall scenario through the shared workflow (SCRUM-12 evidence).

No LLM call is made, so the assessment uses the documented rule-based MEDIUM
fallback where applicable. No real device is operated, no real person is
contacted.

    python -m simulation.elderly_demo --list
    python -m simulation.elderly_demo --scenario high_floor
    python -m simulation.elderly_demo --scenario medium_wait                      # pauses with a question
    python -m simulation.elderly_demo --scenario medium_wait --reply "I'm fine"    # safe -> closed
    python -m simulation.elderly_demo --scenario medium_wait --reply "help"        # help -> alert + light
    python -m simulation.elderly_demo --scenario medium_wait --reply "hmm" --reply "no"   # unclear, then safe
    python -m simulation.elderly_demo --scenario medium_wait --timeout             # no reply -> alert + light
    python -m simulation.elderly_demo --scenario high_floor --offline
"""

from __future__ import annotations

import argparse
import json

from agents.graph import SmartHomeWorkflow
from domains.elderly_safety import ElderlySafetyHandler, default_devices
from simulation.devices import SimulatedDeviceTool
from simulation.elderly_scenarios import SCENARIOS, make_fall_scenario
from simulation.notifications import SimulatedNotificationService


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="high_floor")
    parser.add_argument("--offline", action="store_true", help="simulate all lights offline")
    parser.add_argument("--reply", action="append", default=[], help="resident reply (repeat for a second reply)")
    parser.add_argument("--timeout", action="store_true", help="no reply within the confirmation timeout")
    parser.add_argument("--list", action="store_true", help="list scenarios and exit")
    args = parser.parse_args()

    if args.list:
        for name, (impact, seconds, posture, room, hour, expected) in SCENARIOS.items():
            print(f"{name:<26} impact={impact!s:<5} inactivity={seconds!s:<5} posture={posture:<8} room={room:<12} hour={hour:<3} rule={expected}")
        return

    event = make_fall_scenario(args.scenario)
    devices = SimulatedDeviceTool(default_devices())
    if args.offline:
        devices.offline.update(devices.states)
    handler = ElderlySafetyHandler()  # rule-only; pass a proposal provider to use the campus model
    workflow = SmartHomeWorkflow([handler], devices, notifier=SimulatedNotificationService())
    result = workflow.run(event)
    replies = list(args.reply) + ([None] if args.timeout else [])
    for reply in replies:
        if result.pending_confirmation is None:
            break
        print(f"system asks ({result.pending_confirmation.attempt}/{result.pending_confirmation.max_attempts}, "
              f"{result.pending_confirmation.timeout_seconds}s): {result.pending_confirmation.question}")
        print(f"resident: {'<no reply - timeout>' if reply is None else reply!r}")
        result = workflow.resume(result, reply)

    fall = handler.fall_assessment
    print(f"SIMULATED scenario={args.scenario} event_id={event.event_id}")
    print(f"outcome: {result.outcome}")
    print(f"assessment: {fall.risk_level} source={fall.evidence_source} fallback={fall.fallback_used} "
          f"override={fall.policy_override} confirm={fall.requires_confirmation} ({fall.classification_ms:.2f} ms)")
    print(f"  {fall.rationale}")
    if result.pending_confirmation:
        p = result.pending_confirmation
        print(f"waiting for resident ({p.attempt}/{p.max_attempts}, {p.timeout_seconds}s): {p.question}")
    for r in result.confirmation_replies:
        print(f"reply {r.attempt}: {r.reply!r} -> {r.verdict} ({r.interpreted_by})")
    for r in result.action_results:
        print(f"action: {r.device_id} {r.action} accepted={r.accepted} verified={r.verified} state={r.returned_state} error={r.error}")
    if result.notification_result:
        n = result.notification_result
        print(f"notification: {n.status} acknowledged={n.acknowledged} - {n.detail}")
    print("trace:")
    for entry in result.trace:
        print(f"  {entry.agent:<22} {entry.outcome}")
    print("No real device was operated and no real person was contacted.")


if __name__ == "__main__":
    main()
