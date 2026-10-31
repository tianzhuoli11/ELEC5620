"""Resident-reply interpretation: rules only versus rules + campus-qwen (UC-01 steps 5-6).

Evaluation only. It calls the same `interpret()` the workflow uses and never
runs the workflow, operates a device or sends a notification. The cases are
fictional replies written and labelled by the domain owner, so the result
describes this small sample, not general language understanding.

    python -m simulation.elderly_reply_evaluation                  # rules only, no key needed
    python -m simulation.elderly_reply_evaluation --live           # adds campus-qwen (key + campus network/VPN)

Consequence of a verdict in the workflow:
    safe     -> event closed, nobody contacted
    help     -> escalate: caregiver alert + light
    unclear  -> attempt 1: ask the follow-up question; attempt 2: escalate
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from domains.elderly_safety.confirmation import interpret, interpret_by_rules
from simulation.elderly_scenarios import make_fall_scenario

DEFAULT_OUTPUT = Path("data/runtime/elderly_reply_evaluation.json")
DEFAULT_REPORT = Path("data/runtime/elderly_reply_evaluation.md")

# (attempt, reply, expected verdict). Attempt 1: "Are you okay? Please reply."
# Attempt 2: "Do you need me to contact your family? Please answer 'yes' or 'no'."
CASES: tuple[tuple[int, str, str], ...] = (
    (1, "I'm fine", "safe"),
    (1, "I'm okay, just resting", "safe"),
    (1, "Help, I can't get up", "help"),
    (1, "My hip hurts", "help"),
    (1, "Yes, I'm alright, I just slipped a little", "safe"),
    (1, "No worries, I'm back on my feet", "safe"),
    (1, "I'm not okay", "help"),
    (1, "I can't move my leg", "help"),
    (1, "I fell and I feel faint", "help"),
    (1, "Don't worry about me, I sat down on purpose", "safe"),
    (1, "Everything is under control", "safe"),
    (1, "hmm", "unclear"),
    (1, "What?", "unclear"),
    (2, "No", "safe"),
    (2, "Yes please", "help"),
    (2, "No, I can't move", "help"),
    (2, "Please don't, I'm fine", "safe"),
    (2, "Not needed, my son is already here", "safe"),
    (2, "I think so, my head is bleeding", "help"),
    (2, "Call my daughter", "help"),
    # Added in the second iteration: replies that start reassuringly but report a problem.
    (1, "Okay, I can't breathe", "help"),
    (1, "Ok but I hit my head", "help"),
    (1, "Fine... I think my wrist is broken", "help"),
    (1, "Okay, there is blood", "help"),
    (2, "Not sure", "unclear"),
    (2, "No, please come", "help"),
)


def consequence(attempt: int, verdict: str) -> str:
    if verdict == "safe":
        return "close"
    if verdict == "help" or attempt >= 2:
        return "escalate"
    return "ask_again"


def _summary(rows: list[dict], key: str) -> dict:
    n = len(rows)
    correct = sum(r[key]["verdict"] == r["expected"] for r in rows)
    expected_outcome = [consequence(r["attempt"], r["expected"]) for r in rows]
    outcomes = [r[key]["outcome"] for r in rows]
    return {
        "cases": n,
        "verdict_correct": correct,
        "outcome_correct": sum(a == b for a, b in zip(outcomes, expected_outcome)),
        # Safety-critical: someone who needs help but the event is closed.
        "help_closed_as_safe": sum(r["expected"] == "help" and o == "close" for r, o in zip(rows, outcomes)),
        "unneeded_escalation": sum(r["expected"] == "safe" and o == "escalate" for r, o in zip(rows, outcomes)),
        "extra_follow_up_question": sum(r["expected"] != "unclear" and o == "ask_again" for r, o in zip(rows, outcomes)),
        "help_delayed_by_follow_up": sum(r["expected"] == "help" and o == "ask_again" for r, o in zip(rows, outcomes)),
    }


class ModelUnavailable(RuntimeError):
    """The live comparison would silently measure rules twice, so stop instead."""


def preflight(interpreter) -> None:
    """One test call before a live run; report why the model cannot be used."""
    try:
        proposal = interpreter({"reply": "I'm fine", "attempt": 1})
    except Exception as error:  # urllib HTTPError, timeout, invalid JSON ...
        detail = f"HTTP {error.code}" if hasattr(error, "code") else type(error).__name__
        raise ModelUnavailable(f"campus-qwen test call failed ({detail}: {error}). "
                               "Check the key, the campus network/VPN and the proxy address.") from error
    if not isinstance(proposal, dict) or proposal.get("verdict") not in ("safe", "help", "unclear"):
        raise ModelUnavailable(f"campus-qwen returned an unusable test reply: {proposal!r}")


def _model_used() -> dict:
    """Model name and provider host only; never the key."""
    from urllib.parse import urlparse
    from services.campus_proxy import DEFAULT_BASE_URL, DEFAULT_MODEL
    return {"model": os.getenv("ELEC5620_MODEL", DEFAULT_MODEL),
            "provider_host": urlparse(os.getenv("ELEC5620_BASE_URL", DEFAULT_BASE_URL)).hostname,
            "thinking_disabled": os.getenv("ELEC5620_DISABLE_THINKING", "").strip() == "1"}


def run(live: bool = False) -> dict:
    interpreter = None
    if live:
        from services.elderly_llm import campus_providers
        _, interpreter = campus_providers()  # raises if no key is configured
        preflight(interpreter)
    event = make_fall_scenario("medium_wait")  # only supplies an event ID; never executed
    rows = []
    for attempt, reply, expected in CASES:
        rule = interpret_by_rules(attempt, reply)
        row = {"attempt": attempt, "reply": reply, "expected": expected,
               "rules": {"verdict": rule, "outcome": consequence(attempt, rule)}}
        if live:
            started = perf_counter()
            result = interpret(event, attempt, reply, interpreter)
            row["with_ai"] = {"verdict": result.verdict, "outcome": consequence(attempt, result.verdict),
                              "interpreted_by": result.interpreted_by, "ms": round((perf_counter() - started) * 1000, 1)}
        rows.append(row)
    output = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "mode": "live" if live else "rules_only",
        "note": "Fictional replies labelled by the domain owner; small sample, not a general benchmark.",
        "model": _model_used() if live else None,
        "summary": {"rules": _summary(rows, "rules")},
        "cases": rows,
    }
    if live:
        output["summary"]["with_ai"] = _summary(rows, "with_ai")
        times = [r["with_ai"]["ms"] for r in rows]
        output["summary"]["with_ai"].update({
            "model_used": sum(r["with_ai"]["interpreted_by"] == "llm" for r in rows),
            "fallback_to_rules": sum(r["with_ai"]["interpreted_by"] != "llm" for r in rows),
            "mean_ms": round(statistics.mean(times), 1), "max_ms": max(times),
        })
    return output


def markdown(result: dict) -> str:
    live = "with_ai" in result["summary"]
    cols = ["rules"] + (["with_ai"] if live else [])
    model = (result.get("model") or {}).get("model", "model")
    names = {"rules": "Rules only", "with_ai": f"Rules + {model}"}
    metrics = [
        ("verdict_correct", "Verdict matches label"),
        ("outcome_correct", "Workflow outcome matches label"),
        ("help_closed_as_safe", "**Help needed but event closed (must be 0)**"),
        ("help_delayed_by_follow_up", "Help needed but delayed by an extra question"),
        ("unneeded_escalation", "Resident fine but caregiver alerted"),
        ("extra_follow_up_question", "Clear reply but asked again"),
    ]
    used = result.get("model")
    where = f" Model `{used['model']}` at `{used['provider_host']}`." if used else ""
    lines = [f"Run {result['run_at'][:16]} UTC, mode `{result['mode']}`, {result['summary']['rules']['cases']} fictional replies.{where} {result['note']}", "",
             "| Metric | " + " | ".join(names[c] for c in cols) + " |", "| --- |" + " --- |" * len(cols)]
    for key, label in metrics:
        lines.append(f"| {label} | " + " | ".join(str(result["summary"][c][key]) for c in cols) + " |")
    if live:
        s = result["summary"]["with_ai"]
        lines += ["", f"Model verdict used in {s['model_used']} cases, rule fallback in {s['fallback_to_rules']}; "
                      f"mean {s['mean_ms']} ms, max {s['max_ms']} ms per reply."]
    lines += ["", "| # | Attempt | Reply | Label | Rules | " + ("AI (by) |" if live else ""),
              "| --- | --- | --- | --- | --- |" + (" --- |" if live else "")]
    for i, r in enumerate(result["cases"], 1):
        extra = f" {r['with_ai']['verdict']} ({r['with_ai']['interpreted_by']}) |" if live else ""
        lines.append(f"| {i} | {r['attempt']} | {r['reply']} | {r['expected']} | {r['rules']['verdict']} |{extra}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--live", action="store_true", help="also ask campus-qwen (needs ELEC5620_API_KEY and campus network/VPN)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        result = run(live=args.live)
    except ModelUnavailable as error:
        print(f"Live evaluation stopped: {error}")
        return 2
    for path, text in ((args.output, json.dumps(result, indent=2, ensure_ascii=False)), (args.report, markdown(result))):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(markdown(result))
    print(f"Saved {args.output} and {args.report}. No device was operated and nobody was contacted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
