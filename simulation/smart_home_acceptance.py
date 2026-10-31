"""Repeatable Smart Home Control acceptance run for SCRUM-35 / UC-02.

Every scenario uses the production Smart Home workflow with simulated devices.
The run writes a human-readable report and a machine-readable log:

    python -m simulation.smart_home_acceptance

No physical device is operated.  The generated report deliberately separates
automated evidence from screenshots, the final Canvas-source rehearsal and the
team review/retrospective, which must be recorded when they actually happen.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from importlib import metadata
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from domains.smart_home_control import (
    HomeModeState,
    default_device_states,
    resume_smart_home_confirmation,
    run_smart_home_control,
)
from simulation.devices import SimulatedDeviceTool
from simulation.events import make_user_goal_event


DEFAULT_REPORT = Path("docs/acceptance/SMART_HOME_CONTROL_ACCEPTANCE.md")
DEFAULT_LOG = Path("data/runtime/smart_home_acceptance.json")


class WrongAirConditionerReadback(SimulatedDeviceTool):
    """SIMULATED AC accepts the command but returns a stale mode."""

    def read_state(self, device_id: str) -> dict[str, Any]:
        state = super().read_state(device_id)
        if device_id == "living-room-ac":
            state["mode"] = "comfort"
        return state


@dataclass
class Case:
    case_id: str
    title: str
    requirement: str
    given: str
    expected: str
    actual: str = ""
    checks: list[tuple[str, bool]] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def check(self, label: str, ok: bool) -> None:
        self.checks.append((label, bool(ok)))

    @property
    def passed(self) -> bool:
        return self.error is None and bool(self.checks) and all(ok for _, ok in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "title": self.title,
            "requirement": self.requirement,
            "input": self.given,
            "expected": self.expected,
            "actual": self.actual,
            "passed": self.passed,
            "checks": [{"check": label, "ok": ok} for label, ok in self.checks],
            "error": self.error,
            "evidence": self.evidence,
        }


def _run(
    text: str,
    *,
    tool: SimulatedDeviceTool | None = None,
    provider=None,
    mode_state: HomeModeState | None = None,
):
    device_tool = tool or SimulatedDeviceTool(default_device_states())
    result = run_smart_home_control(
        make_user_goal_event(text),
        device_tool=device_tool,
        proposal_provider=provider,
        mode_state=mode_state,
        record_path=None,
    )
    return result, device_tool


def _evidence(result, tool: SimulatedDeviceTool, mode_state: HomeModeState | None = None) -> dict[str, Any]:
    return {
        "workflow": result.to_dict(),
        "device_states": deepcopy(tool.states),
        "dispatch_count": tool.dispatch_count,
        "home_mode": None if mode_state is None else mode_state.current_mode,
    }


def case_night_mode(c: Case) -> None:
    mode = HomeModeState()
    result, tool = _run("Good night", mode_state=mode)
    c.evidence = _evidence(result, tool, mode)
    c.check("workflow completed", result.outcome == "COMPLETE")
    c.check("all four device results were accepted and verified", len(result.action_results) == 4 and all(a.success for a in result.action_results))
    c.check("sleep states match the UC-02 plan", tool.states["bedroom-light"]["power"] == "off"
            and tool.states["bedroom-curtain"]["position"] == "closed"
            and tool.states["front-door-lock"]["locked"] is True
            and tool.states["living-room-ac"]["mode"] == "sleep")
    c.check("verified mode propagated as NIGHT", mode.current_mode == "NIGHT")
    c.check("shared coordinator and device agents are in the trace", {"HomeCoordinatorAgent", "DeviceAutomationAgent"}
            <= {entry.agent for entry in result.trace})
    c.actual = f"{result.outcome}; 4/4 verified; HomeMode={mode.current_mode}; devices={tool.states}"


def case_away_mode(c: Case) -> None:
    mode = HomeModeState()
    result, tool = _run("I'm leaving home", mode_state=mode)
    c.evidence = _evidence(result, tool, mode)
    c.check("workflow completed", result.outcome == "COMPLETE")
    c.check("all four device results were verified", len(result.action_results) == 4 and all(a.success for a in result.action_results))
    c.check("away states are safe", tool.states["bedroom-light"]["power"] == "off"
            and tool.states["bedroom-curtain"]["position"] == "closed"
            and tool.states["front-door-lock"]["locked"] is True
            and tool.states["living-room-ac"]["mode"] == "eco")
    c.check("verified mode propagated as AWAY", mode.current_mode == "AWAY")
    c.actual = f"{result.outcome}; 4/4 verified; HomeMode={mode.current_mode}; devices={tool.states}"


def case_conflicting_command(c: Case) -> None:
    result, tool = _run("Good night and turn on the bedroom light")
    c.evidence = _evidence(result, tool)
    c.check("conflict requires clarification", result.outcome == "CLARIFICATION_REQUIRED")
    c.check("question explains how to resolve it", "separate commands" in (result.goal.clarification_question or ""))
    c.check("nothing was dispatched", tool.dispatch_count == 0)
    c.actual = f"{result.outcome}; question={result.goal.clarification_question!r}; dispatches={tool.dispatch_count}"


def case_unsupported_request(c: Case) -> None:
    result, tool = _run("Order me a pizza")
    c.evidence = _evidence(result, tool)
    c.check("unsupported request requires clarification", result.outcome == "CLARIFICATION_REQUIRED")
    c.check("no device action was inferred", not result.action_results and tool.dispatch_count == 0)
    c.actual = f"{result.outcome}; question={result.goal.clarification_question!r}; dispatches={tool.dispatch_count}"


def case_sensitive_waits(c: Case) -> None:
    result, tool = _run("Unlock the front door")
    c.evidence = _evidence(result, tool)
    c.check("unlock pauses for a decision", result.outcome == "AWAITING_CONFIRMATION" and result.pending_confirmation is not None)
    c.check("assessment marks human review", result.assessment.requires_human_review)
    c.check("door remains locked and nothing is dispatched", tool.states["front-door-lock"]["locked"] is True and tool.dispatch_count == 0)
    c.actual = f"{result.outcome}; pending={result.pending_confirmation.question!r}; door_locked=True; dispatches=0"


def case_sensitive_declined(c: Case) -> None:
    initial, tool = _run("Turn off the bedroom light and unlock the front door")
    c.check("mixed request first pauses", initial.outcome == "AWAITING_CONFIRMATION" and tool.dispatch_count == 0)
    result = resume_smart_home_confirmation(initial, approved=False, device_tool=tool, record_path=None)
    c.evidence = _evidence(result, tool)
    c.check("safe action continues after denial", result.outcome == "COMPLETE" and tool.states["bedroom-light"]["power"] == "off")
    c.check("denied unlock never executes", tool.states["front-door-lock"]["locked"] is True and tool.dispatch_count == 1)
    c.check("denial is in the audit trace", "sensitive_action_declined" in [entry.outcome for entry in result.trace])
    c.actual = f"initial={initial.outcome}; final={result.outcome}; light=off; door_locked=True; dispatches={tool.dispatch_count}"


def case_sensitive_approved(c: Case) -> None:
    initial, tool = _run("Unlock the front door")
    result = resume_smart_home_confirmation(initial, approved=True, device_tool=tool, record_path=None)
    c.evidence = _evidence(result, tool)
    c.check("explicit approval completes", result.outcome == "COMPLETE")
    c.check("door unlock is accepted and verified", len(result.action_results) == 1 and result.action_results[0].success)
    c.check("exactly one command executes", tool.states["front-door-lock"]["locked"] is False and tool.dispatch_count == 1)
    c.check("approval is in the audit trace", "sensitive_action_approved" in [entry.outcome for entry in result.trace])
    c.actual = f"initial={initial.outcome}; final={result.outcome}; door_locked=False; verified=True; dispatches=1"


def case_device_offline(c: Case) -> None:
    tool = SimulatedDeviceTool(default_device_states())
    tool.offline.add("living-room-ac")
    mode = HomeModeState()
    result, tool = _run("Good night", tool=tool, mode_state=mode)
    failed = result.action_results[-1]
    c.evidence = _evidence(result, tool, mode)
    c.check("partial failure is not reported as full success", result.outcome == "PARTIAL")
    c.check("three independent actions still verify", sum(a.success for a in result.action_results) == 3)
    c.check("offline AC failure is explicit", not failed.success and "offline" in (failed.error or "").lower())
    c.check("mode remains HOME because the plan was not fully verified", mode.current_mode == "HOME")
    c.actual = f"{result.outcome}; verified=3/4; AC error={failed.error!r}; HomeMode={mode.current_mode}"


def case_readback_mismatch(c: Case) -> None:
    result, tool = _run("Good night", tool=WrongAirConditionerReadback(default_device_states()))
    failed = result.action_results[-1]
    c.evidence = _evidence(result, tool)
    c.check("command was accepted", failed.accepted)
    c.check("stale read-back is not verified", not failed.verified and "did not match" in (failed.error or ""))
    c.check("result is PARTIAL, never COMPLETE", result.outcome == "PARTIAL")
    c.actual = f"{result.outcome}; AC accepted={failed.accepted}; verified={failed.verified}; error={failed.error!r}"


def case_ai_extra_targets(c: Case) -> None:
    provider = lambda _: {
        "domain": "smart_home_control",
        "intent": "direct_control",
        "parameters": {"light_power": "off", "curtain_position": "closed", "ac_power": "off"},
    }
    result, tool = _run("Turn off the bedroom light", provider=provider)
    c.evidence = _evidence(result, tool)
    c.check("only the explicitly requested target remains", result.goal.parameters == {"light_power": "off"})
    c.check("only one command is dispatched", tool.dispatch_count == 1)
    c.check("unrequested devices remain unchanged", tool.states["bedroom-curtain"]["position"] == "open"
            and tool.states["living-room-ac"]["power"] == "on")
    c.check("policy fallback is recorded", "fallback" in result.goal.evidence.lower())
    c.actual = f"{result.outcome}; parameters={result.goal.parameters}; dispatches=1; unrequested devices unchanged; fallback recorded"


CaseSpec = tuple[str, str, str, str, str, Callable[[Case], None]]
CASES: list[CaseSpec] = [
    ("AT-SH01", "Sleep goal succeeds", "UC-02 main flow; OR-02", "Good night",
     "Four device actions verified; HomeMode becomes NIGHT; shared-agent trace retained", case_night_mode),
    ("AT-SH02", "Away goal succeeds", "UC-02 main flow; OR-02", "I'm leaving home",
     "Four safe away actions verified; HomeMode becomes AWAY", case_away_mode),
    ("AT-SH03", "Conflicting mode and direct command", "UC-02 clarification", "Good night and turn on the bedroom light",
     "Ask for separate commands; dispatch nothing", case_conflicting_command),
    ("AT-SH04", "Unsupported request", "UC-02 unsupported request", "Order me a pizza",
     "Ask what device state or mode is wanted; dispatch nothing", case_unsupported_request),
    ("AT-SH05", "Sensitive unlock waits", "UC-02 safety confirmation", "Unlock the front door",
     "Pause for explicit confirmation; keep the door locked; dispatch nothing", case_sensitive_waits),
    ("AT-SH06", "Sensitive unlock denied", "UC-02 denial path", "Turn off the bedroom light and unlock the front door; deny unlock",
     "Execute the safe light action only; keep the door locked; record denial", case_sensitive_declined),
    ("AT-SH07", "Sensitive unlock approved", "UC-02 confirmed path", "Unlock the front door; explicitly approve",
     "Execute exactly one verified unlock and record approval", case_sensitive_approved),
    ("AT-SH08", "Air conditioner offline", "UC-02 failure; NFR-04", "Good night; simulated AC offline",
     "Three verified actions plus explicit AC failure; PARTIAL; HomeMode remains HOME", case_device_offline),
    ("AT-SH09", "Returned-state mismatch", "UC-02 verification; NFR-04", "Good night; AC returns a stale mode",
     "Accepted but unverified AC; PARTIAL, never full success", case_readback_mismatch),
    ("AT-SH10", "AI proposal cannot add targets", "UC-02 policy; PR #23 retest", "Turn off the bedroom light; model proposes two extra devices",
     "Policy fallback executes only the explicitly requested light action", case_ai_extra_targets),
]


def run_cases() -> list[Case]:
    results: list[Case] = []
    for case_id, title, requirement, given, expected, fn in CASES:
        case = Case(case_id, title, requirement, given, expected)
        try:
            fn(case)
        except Exception as exc:
            case.error = f"{type(exc).__name__}: {exc}"
            case.actual = case.actual or "crashed"
        results.append(case)
    return results


def _environment() -> dict[str, str]:
    def version(package: str) -> str:
        try:
            return metadata.version(package)
        except metadata.PackageNotFoundError:
            return "not installed"

    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip() or "unknown"
        if subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=5).stdout.strip():
            commit += " (uncommitted changes)"
    except Exception:
        commit = "unknown"
    return {
        "run_at": datetime.now(ZoneInfo("Australia/Sydney")).strftime("%Y-%m-%d %H:%M %Z"),
        "git_commit": commit,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "langgraph": version("langgraph"),
    }


def _md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_report(cases: list[Case], environment: dict[str, str], path: Path) -> None:
    passed = sum(case.passed for case in cases)
    lines = [
        "# Smart Home Control scenario acceptance report (SCRUM-35)",
        "",
        "AR-02 / UC-02 / OR-02. Generated by `python -m simulation.smart_home_acceptance`. "
        "Every row below was executed through the production shared workflow and device read-back verification. "
        "**All devices are simulated; no physical home device was operated.**",
        "",
        "| Run | Value |", "| --- | --- |",
        *[f"| {_md(key)} | {_md(value)} |" for key, value in environment.items()],
        f"| result | **{passed} / {len(cases)} passed** |",
        "",
        "## Input, expected result, actual result and evidence",
        "",
        "| ID | Scenario | Requirement | Input | Expected | Actual / log evidence | Result |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case in cases:
        result = "PASS" if case.passed else "**FAIL**"
        lines.append(f"| {case.case_id} | {_md(case.title)} | {_md(case.requirement)} | {_md(case.given)} | {_md(case.expected)} | {_md(case.actual)} | {result} |")

    lines += ["", "## Checks per scenario", ""]
    for case in cases:
        lines.append(f"**{case.case_id} {case.title}**" + ("" if case.passed else " — FAIL"))
        lines.extend(f"- [{'x' if ok else ' '}] {label}" for label, ok in case.checks)
        if case.error:
            lines.append(f"- error: `{case.error}`")
        lines.append("")

    failed = [case for case in cases if not case.passed]
    lines += ["## Defects, fixes and retest", ""]
    if failed:
        lines.append("Open a linked Jira defect for each failed case, fix it, then rerun this command and replace the report/log.")
        lines.extend(f"- {case.case_id} {case.title}: {case.error or 'one or more checks failed'}" for case in failed)
    else:
        lines.append("No acceptance case failed in this run. The earlier integration defects below are covered by the passing retests.")
    lines += [
        "",
        "| Earlier defect | Fix evidence | Acceptance retest |",
        "| --- | --- | --- |",
        "| Model could add unrequested allow-listed device targets | PR [#23](https://github.com/tianzhuoli11/ELEC5620/pull/23), commit `8f4a6f7`, merged as `a3d9608` | AT-SH10 |",
        "| Mixed mode and explicit device commands could be rewritten | PR #23 fail-closed conflict validation | AT-SH03 |",
        "| Partial device failure and stale read-back needed visible status | Verified action results and PARTIAL outcome | AT-SH08, AT-SH09 |",
        "| Sensitive-action confirmation needed auditable approve/deny paths | Single-use confirmation with trace entries | AT-SH05–AT-SH07 |",
        "",
        "The full machine log is written to `data/runtime/smart_home_acceptance.json` (git-ignored). It includes the workflow result, agent trace, action read-backs, dispatch count and final simulated state for each row.",
        "",
        "## Manual evidence still required for SCRUM-35 / SCRUM-40",
        "",
        "These items are intentionally **not** marked complete by this automated run:",
        "",
        "- Attach Streamlit screenshots or a short recording for AT-SH01, AT-SH03, AT-SH06 and AT-SH08 to SCRUM-35.",
        "- Rehearse from the exact Canvas source archive on the demonstration laptop and record the real result.",
        "- Link this report, PR #23 and the final clean-source rehearsal in the group UC-01–UC-05 acceptance report.",
        "- Record the actual Sprint Review, feedback, follow-up issues/retests and Retrospective only after the team performs them.",
        "",
        "Suggested screenshots: Smart Home page after a verified Night run; conflict clarification with no dispatch; denied mixed unlock with the door still locked; offline AC showing PARTIAL and the explicit error.",
        "",
        "## Scope and honesty notes",
        "",
        "- This is deterministic offline acceptance evidence. It does not claim a successful live campus-qwen call.",
        "- Device I/O is simulated, although production policy, shared-agent routing, retries and returned-state verification are exercised.",
        "- A passing automated run is evidence for moving SCRUM-35 to In Review; it is not evidence that the group coordination work in SCRUM-40 is Done.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_log(cases: list[Case], environment: dict[str, str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"environment": environment, "cases": [case.to_dict() for case in cases]}, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    cases = run_cases()
    environment = _environment()
    write_report(cases, environment, args.report)
    write_log(cases, environment, args.log)
    if not args.quiet:
        for case in cases:
            print(f"{'PASS' if case.passed else 'FAIL'}  {case.case_id}  {case.title}" + (f"  ({case.error})" if case.error else ""))
        print(f"\n{sum(case.passed for case in cases)}/{len(cases)} passed. Report: {args.report}  Log: {args.log}")
        print("All devices were simulated; no physical home device was operated.")
    return 0 if all(case.passed for case in cases) else 1


if __name__ == "__main__":
    sys.exit(main())
