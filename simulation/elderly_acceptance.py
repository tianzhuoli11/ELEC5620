"""Elderly Safety scenario acceptance run (SCRUM-34; AR-01 / UC-01 / OR-04).

Runs every acceptance case through the real shared workflow (LangGraph
agents, domain rules, device verification, escalation) with SIMULATED
sensors, lights and contacts, then writes:

    docs/acceptance/ELDERLY_SAFETY_ACCEPTANCE.md   human-readable report
    data/runtime/elderly_acceptance.json           full machine log (git-ignored)

Usage, from the repository root:

    python -m simulation.elderly_acceptance
    python -m simulation.elderly_acceptance --use-campus-llm      # adds live model cases (VPN + key)
    python -m simulation.elderly_acceptance --report other.md --log other.json

Exit code is 0 only when every case passes. Each case records the input,
the expected result, what actually happened, and the evidence it was
checked against. No real device is operated and no real person is
contacted; the report says so.
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

from domains.elderly_safety import default_devices
from domains.elderly_safety.confirmation import CONFIRMATION_TIMEOUT_S, QUESTIONS
from domains.elderly_safety.context import collect_context
from domains.elderly_safety.escalation import ACK_TIMEOUT_S, OPERATOR_REF
from domains.elderly_safety.integration import (
    acknowledge_alert, acknowledgement_timeout, build_workflow, operator_close_event,
    resume_elderly_safety, run_elderly_safety, start_escalation,
)
from models import ActionRequest, NotificationRequest, NotificationResult
from simulation.devices import SimulatedDeviceTool
from simulation.elderly_scenarios import make_fall_scenario
from simulation.notifications import SimulatedNotificationService
from tools.device import DispatchResult

DEFAULT_REPORT = Path("docs/acceptance/ELDERLY_SAFETY_ACCEPTANCE.md")
DEFAULT_LOG = Path("data/runtime/elderly_acceptance.json")
CLASSIFICATION_LIMIT_MS = 1000.0  # NFR-02 prototype limit for the rule path (receipt -> classification)


# --- simulated doubles used only by specific cases ---------------------------

class MismatchDeviceTool(SimulatedDeviceTool):
    """SIMULATED light that accepts the command but reads back unchanged state."""

    def dispatch(self, request: ActionRequest) -> DispatchResult:
        self.dispatch_count += 1
        return DispatchResult(True)


class FailingNotifier:
    """SIMULATED transport outage."""

    def send(self, request: NotificationRequest) -> NotificationResult:
        raise ConnectionError("simulated transport down")


# --- case bookkeeping --------------------------------------------------------

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
            "case_id": self.case_id, "title": self.title, "requirement": self.requirement,
            "given": self.given, "expected": self.expected, "actual": self.actual,
            "passed": self.passed, "checks": [{"check": c, "ok": ok} for c, ok in self.checks],
            "error": self.error, "evidence": self.evidence,
        }


def _workflow(device_tool=None, notifier=None, provider=None, interpreter=None):
    tool = device_tool or SimulatedDeviceTool(default_devices())
    workflow, handler = build_workflow(device_tool=tool, notifier=notifier or SimulatedNotificationService(),
                                       proposal_provider=provider, reply_interpreter=interpreter)
    return workflow, handler, tool


def _trace(result) -> list[str]:
    return [f"{e.agent}:{e.outcome}" for e in result.trace]


def _evidence(result, handler, tool, escalation=None) -> dict[str, Any]:
    fall = handler.fall_assessment
    return {
        "event_id": result.event.event_id,
        "outcome": result.outcome,
        "risk_level": result.assessment.risk_level,
        "initial_assessment": fall.to_dict() if fall else None,
        "replies": [{"attempt": r.attempt, "reply": r.reply, "verdict": r.verdict, "by": r.interpreted_by}
                    for r in result.confirmation_replies],
        "pending_question": result.pending_confirmation.question if result.pending_confirmation else None,
        "actions": [a.to_dict() for a in result.action_results],
        "notification": None if result.notification_result is None else {
            "status": result.notification_result.status, "acknowledged": result.notification_result.acknowledged,
            "detail": result.notification_result.detail},
        "device_states": deepcopy(getattr(tool, "states", {})),
        "dispatch_count": getattr(tool, "dispatch_count", None),
        "trace": _trace(result),
        "escalation": escalation.to_dict() if escalation is not None else None,
    }


# --- acceptance cases --------------------------------------------------------

def case_high_urgent(c: Case) -> None:
    workflow, handler, tool = _workflow()
    r = run_elderly_safety(make_fall_scenario("high_floor"), workflow=workflow, handler=handler, record_path=None)
    c.evidence = _evidence(r, handler, tool)
    c.check("assessed HIGH", r.assessment.risk_level == "HIGH")
    c.check("resident not asked (confirmation skipped)", r.pending_confirmation is None and not r.confirmation_replies)
    c.check("caregiver alert sent (SIMULATED)", r.notification_result and r.notification_result.status == "SIMULATED")
    c.check("bathroom light verified on by read-back", r.action_results and r.action_results[0].success
            and tool.states["bathroom_light"]["power"] == "on")
    c.check("all three agents in trace", {"HomeCoordinatorAgent", "MonitoringAgent", "DeviceAutomationAgent"}
            <= {e.agent for e in r.trace})
    c.actual = (f"{r.outcome}; HIGH; no question; alert {r.notification_result.status}; "
                f"bathroom_light power={tool.states['bathroom_light']['power']} verified={r.action_results[0].verified}")


def case_safe_reply(c: Case) -> None:
    workflow, handler, tool = _workflow()
    paused = run_elderly_safety(make_fall_scenario("medium_wait"), workflow=workflow, handler=handler, record_path=None)
    c.check("MEDIUM pauses with question 1", paused.outcome == "AWAITING_CONFIRMATION"
            and paused.pending_confirmation.question == QUESTIONS[1])
    c.check("nothing dispatched while waiting", tool.dispatch_count == 0 and paused.notification_result is None)
    done = resume_elderly_safety(paused, "I'm fine, I just sat down.", workflow=workflow, handler=handler, record_path=None)
    c.evidence = _evidence(done, handler, tool)
    c.check("reply interpreted as safe", done.confirmation_replies[-1].verdict == "safe")
    c.check("event closed without alert or device action",
            done.outcome == "ASSESSED" and done.notification_result is None and tool.dispatch_count == 0)
    c.actual = f"asked '{QUESTIONS[1]}'; reply -> safe; {done.outcome}; no alert; dispatches={tool.dispatch_count}"


def case_help_reply(c: Case) -> None:
    workflow, handler, tool = _workflow()
    paused = run_elderly_safety(make_fall_scenario("medium_wait"), workflow=workflow, handler=handler, record_path=None)
    done = resume_elderly_safety(paused, "Help, I can't get up.", workflow=workflow, handler=handler, record_path=None)
    c.evidence = _evidence(done, handler, tool)
    c.check("reply interpreted as help", done.confirmation_replies[-1].verdict == "help")
    c.check("escalated to HIGH", done.assessment.risk_level == "HIGH" and "resident asked for help" in done.assessment.rationale)
    c.check("caregiver alert sent (SIMULATED)", done.notification_result.status == "SIMULATED")
    c.check("living-room light verified on", done.action_results[0].success and tool.states["living_light"]["power"] == "on")
    c.actual = f"reply -> help; escalated HIGH; {done.outcome}; alert SIMULATED; living_light on (verified)"


def case_unclear_then_safe(c: Case) -> None:
    workflow, handler, tool = _workflow()
    paused = run_elderly_safety(make_fall_scenario("medium_wait"), workflow=workflow, handler=handler, record_path=None)
    again = resume_elderly_safety(paused, "hmm", workflow=workflow, handler=handler, record_path=None)
    c.check("unclear reply asks follow-up question 2", again.outcome == "AWAITING_CONFIRMATION"
            and again.pending_confirmation.attempt == 2 and again.pending_confirmation.question == QUESTIONS[2])
    done = resume_elderly_safety(again, "no", workflow=workflow, handler=handler, record_path=None)
    c.evidence = _evidence(done, handler, tool)
    c.check("'no' to question 2 is safe", [r.verdict for r in done.confirmation_replies] == ["unclear", "safe"])
    c.check("closed without alert or device action", done.outcome == "ASSESSED" and tool.dispatch_count == 0)
    c.actual = f"'hmm' -> unclear -> asked '{QUESTIONS[2]}'; 'no' -> safe; {done.outcome}"


def case_unclear_twice(c: Case) -> None:
    workflow, handler, tool = _workflow()
    paused = run_elderly_safety(make_fall_scenario("medium_wait"), workflow=workflow, handler=handler, record_path=None)
    again = resume_elderly_safety(paused, "hmm", workflow=workflow, handler=handler, record_path=None)
    done = resume_elderly_safety(again, "what?", workflow=workflow, handler=handler, record_path=None)
    c.evidence = _evidence(done, handler, tool)
    c.check("two unclear replies recorded", [r.verdict for r in done.confirmation_replies] == ["unclear", "unclear"])
    c.check("treated as needing help", done.assessment.risk_level == "HIGH"
            and "reply unclear after a follow-up question" in done.assessment.rationale)
    c.check("alert sent and light verified", done.notification_result.status == "SIMULATED" and done.action_results[0].success)
    c.actual = f"unclear x2 -> escalated HIGH; {done.outcome}; alert SIMULATED; light verified"


def case_no_reply(c: Case) -> None:
    workflow, handler, tool = _workflow()
    paused = run_elderly_safety(make_fall_scenario("medium_wait"), workflow=workflow, handler=handler, record_path=None)
    c.check(f"confirmation timeout is {CONFIRMATION_TIMEOUT_S} s", paused.pending_confirmation.timeout_seconds == CONFIRMATION_TIMEOUT_S)
    done = resume_elderly_safety(paused, None, workflow=workflow, handler=handler, record_path=None)
    c.evidence = _evidence(done, handler, tool)
    c.check("silence recorded as timeout, never safe", done.confirmation_replies[-1].verdict == "timeout")
    c.check("escalated without a second question", len(done.confirmation_replies) == 1 and done.assessment.risk_level == "HIGH")
    c.check("alert sent and light verified", done.notification_result.status == "SIMULATED" and done.action_results[0].success)
    c.actual = f"no reply in {CONFIRMATION_TIMEOUT_S} s -> timeout -> escalated HIGH; {done.outcome}"


def _fallback_case(c: Case, provider: Callable, scenario: str) -> None:
    workflow, handler, tool = _workflow(provider=provider)
    r = run_elderly_safety(make_fall_scenario(scenario), workflow=workflow, handler=handler, record_path=None)
    fall = handler.fall_assessment
    c.evidence = _evidence(r, handler, tool)
    c.check("rules alone say LOW", "upright" in fall.rationale.lower() or "dropped" in fall.rationale.lower())
    c.check("documented MEDIUM fallback applied", fall.risk_level == "MEDIUM" and fall.fallback_used
            and fall.evidence_source == "llm_fallback")
    c.check("resident is asked (not silently closed)", r.outcome == "AWAITING_CONFIRMATION")
    c.check("fallback logged in shared assessment", r.assessment.fallback_used and "[llm_fallback]" in r.assessment.evidence)
    c.actual = f"model {c.title.split(':')[-1].strip()} -> MEDIUM fallback; {r.outcome}; evidence={r.assessment.evidence}"


def case_llm_unavailable(c: Case) -> None:
    def timeout(view):
        raise TimeoutError("simulated campus proxy timeout")
    _fallback_case(c, timeout, "low_dropped_object")


def case_llm_invalid(c: Case) -> None:
    _fallback_case(c, lambda view: {"risk_level": "SEVERE", "rationale": "not a valid level"}, "low_dropped_object")


def case_llm_cannot_lower(c: Case) -> None:
    workflow, handler, tool = _workflow(provider=lambda view: {"risk_level": "LOW", "rationale": "probably fine"})
    r = run_elderly_safety(make_fall_scenario("high_floor"), workflow=workflow, handler=handler, record_path=None)
    fall = handler.fall_assessment
    c.evidence = _evidence(r, handler, tool)
    c.check("rules keep HIGH", r.assessment.risk_level == "HIGH")
    c.check("override recorded", fall.policy_override and r.assessment.policy_override)
    c.check("urgent response still executed", r.notification_result.status == "SIMULATED" and r.action_results[0].success)
    c.actual = f"model proposed LOW; rules kept HIGH (policy_override={fall.policy_override}); {r.outcome}"


def case_light_offline(c: Case) -> None:
    tool = SimulatedDeviceTool(default_devices())
    tool.offline.update(tool.states)
    workflow, handler, tool = _workflow(device_tool=tool)
    r = run_elderly_safety(make_fall_scenario("high_floor"), workflow=workflow, handler=handler, record_path=None)
    a = r.action_results[0]
    c.evidence = _evidence(r, handler, tool)
    c.check("light action reported failed, not success", not a.accepted and not a.verified and "offline" in (a.error or "").lower())
    c.check("workflow outcome FAILED (not hidden)", r.outcome == "FAILED")
    c.check("caregiver alert still sent", r.notification_result.status == "SIMULATED")
    c.actual = f"{r.outcome}; light accepted={a.accepted} verified={a.verified} error='{a.error}'; alert {r.notification_result.status}"


def case_light_mismatch(c: Case) -> None:
    tool = MismatchDeviceTool(default_devices())
    workflow, handler, tool = _workflow(device_tool=tool)
    r = run_elderly_safety(make_fall_scenario("high_floor"), workflow=workflow, handler=handler, record_path=None)
    a = r.action_results[0]
    c.evidence = _evidence(r, handler, tool)
    c.check("command accepted", a.accepted)
    c.check("read-back mismatch -> not verified", not a.verified and "did not match" in (a.error or ""))
    c.check("not reported as success", not a.success and r.outcome in ("FAILED", "PARTIAL"))
    c.actual = (f"{r.outcome}; light accepted={a.accepted} verified={a.verified} "
                f"returned={a.returned_state} error='{a.error}'")


def case_notification_failure(c: Case) -> None:
    workflow, handler, tool = _workflow(notifier=FailingNotifier())
    r = run_elderly_safety(make_fall_scenario("high_floor"), workflow=workflow, handler=handler, record_path=None)
    c.evidence = _evidence(r, handler, tool)
    c.check("alert failure reported", r.notification_result.status == "FAILED")
    c.check("outcome PARTIAL (light verified, alert failed)", r.outcome == "PARTIAL" and r.action_results[0].success)
    esc = start_escalation(r, workflow=workflow, record_path=None)
    c.evidence["escalation"] = esc.to_dict()
    c.check("failed level skipped immediately, without waiting", [a.outcome for a in esc.attempts][0] == "send_failed")
    c.actual = f"{r.outcome}; alert FAILED; escalation moved on: {[(a.role, a.outcome) for a in esc.attempts]}"


def case_caregiver_ack(c: Case) -> None:
    workflow, handler, tool = _workflow()
    r = run_elderly_safety(make_fall_scenario("high_floor"), workflow=workflow, handler=handler, record_path=None)
    esc = start_escalation(r, workflow=workflow, record_path=None)
    c.check("simulated send is not an acknowledgement", esc.status == "AWAITING_ACK" and not esc.current.acknowledged)
    esc = acknowledge_alert(esc, record_path=None)
    c.evidence = _evidence(r, handler, tool, esc)
    c.check("acknowledgement resolves the event", esc.status == "RESOLVED" and not esc.is_open)
    c.check("no further contacts", len(esc.attempts) == 1)
    c.actual = f"level 1 primary caregiver acknowledged (simulated) -> {esc.status}"


def case_caregiver_timeout(c: Case) -> None:
    workflow, handler, tool = _workflow()
    r = run_elderly_safety(make_fall_scenario("high_floor"), workflow=workflow, handler=handler, record_path=None)
    esc = start_escalation(r, workflow=workflow, record_path=None)
    esc = acknowledgement_timeout(esc, workflow=workflow, record_path=None)
    c.check(f"after {ACK_TIMEOUT_S} s, secondary contact alerted", esc.current.level == 2 and esc.current.role == "secondary contact")
    esc = acknowledge_alert(esc, record_path=None)
    c.evidence = _evidence(r, handler, tool, esc)
    c.check("secondary acknowledgement resolves", esc.status == "RESOLVED")
    c.check("every contact recorded", [a.outcome for a in esc.attempts] == ["ack_timeout", "acknowledged"])
    c.actual = f"primary caregiver ack_timeout -> secondary contact acknowledged -> {esc.status}"


def case_escalation_failed(c: Case) -> None:
    workflow, handler, tool = _workflow()
    r = run_elderly_safety(make_fall_scenario("high_floor"), workflow=workflow, handler=handler, record_path=None)
    esc = start_escalation(r, workflow=workflow, record_path=None)
    esc = acknowledgement_timeout(esc, workflow=workflow, record_path=None)
    esc = acknowledgement_timeout(esc, workflow=workflow, record_path=None)
    c.check("Human Operator informed", esc.status == "ESCALATION_FAILED" and esc.current.recipient_ref == OPERATOR_REF)
    c.check("event stays open", esc.is_open)
    closed = operator_close_event(esc, "acceptance run: operator closes", record_path=None)
    c.evidence = _evidence(r, handler, tool, closed)
    c.check("only the operator closes it", closed.status == "CLOSED_BY_OPERATOR" and not closed.is_open)
    c.actual = f"2 ack timeouts -> {esc.status} (operator informed, open) -> {closed.status}"


def case_privacy(c: Case) -> None:
    seen: dict[str, Any] = {}
    event = make_fall_scenario("high_floor")
    event.context.update({"resident_name": "Fictional Resident", "address": "1 Example Street", "caregiver_phone": "0400000000"})
    workflow, handler, tool = _workflow(provider=lambda view: seen.update(view) or {"risk_level": "HIGH", "rationale": "ok"})
    r = run_elderly_safety(event, workflow=workflow, handler=handler, record_path=None)
    text = json.dumps(seen)
    c.evidence = {"model_input": seen, "event_id": event.event_id}
    for label, private in (("name", "Fictional Resident"), ("address", "Example Street"),
                           ("phone", "0400000000"), ("event ID", event.event_id)):
        c.check(f"model input excludes {label}", private not in text)
    c.check("room reduced to category", seen.get("room_category") == "bathroom" and "room" not in seen)
    c.actual = f"model received keys {sorted(seen)}"


def case_timing(c: Case) -> None:
    workflow, handler, tool = _workflow()
    times = []
    for scenario in ("high_floor", "medium_wait", "low_dropped_object", "medium_missing_duration", "medium_night_uplift"):
        run_elderly_safety(make_fall_scenario(scenario), workflow=workflow, handler=handler, record_path=None)
        times.append(round(handler.fall_assessment.classification_ms, 3))
    c.evidence = {"classification_ms": times, "limit_ms": CLASSIFICATION_LIMIT_MS}
    c.check("classification time recorded for every event", len(times) == 5 and all(t >= 0 for t in times))
    c.check(f"rule path under {CLASSIFICATION_LIMIT_MS:g} ms", max(times) < CLASSIFICATION_LIMIT_MS)
    c.actual = f"classification ms per scenario: {times} (max {max(times)})"


def case_simulated_labelling(c: Case) -> None:
    workflow, handler, tool = _workflow()
    r = run_elderly_safety(make_fall_scenario("high_floor"), workflow=workflow, handler=handler, record_path=None)
    esc = start_escalation(r, workflow=workflow, record_path=None)
    c.evidence = _evidence(r, handler, tool, esc)
    c.check("event marked simulated", r.event.simulated)
    c.check("device result marked simulated", all(a.simulated for a in r.action_results))
    c.check("notification says no external message sent", "no external message sent" in r.notification_result.detail)
    c.check("escalation contacts fictional and simulated", esc.simulated and all(a.recipient_ref.startswith("fictional-") for a in esc.attempts))
    c.actual = "event, light result, alert and contacts all labelled simulated / fictional"


def live_case(c: Case) -> None:
    """Records real campus-qwen behaviour; pass = rules held and the source is reported honestly."""
    from services.elderly_llm import campus_providers
    provider, interpreter = campus_providers()
    workflow, handler, tool = _workflow(provider=provider, interpreter=interpreter)
    r = run_elderly_safety(make_fall_scenario("high_floor"), workflow=workflow, handler=handler, record_path=None)
    fall = handler.fall_assessment
    c.check("rules floor held (HIGH stays HIGH)", r.assessment.risk_level == "HIGH")
    c.check("evidence source reported", fall.evidence_source in ("llm_confirmed", "llm_fallback"))
    workflow2, handler2, tool2 = _workflow(provider=provider, interpreter=interpreter)
    paused = run_elderly_safety(make_fall_scenario("medium_wait"), workflow=workflow2, handler=handler2, record_path=None)
    reply = None
    if paused.pending_confirmation is not None:
        done = resume_elderly_safety(paused, "Help, my hip hurts and I can't get up.", workflow=workflow2, handler=handler2, record_path=None)
        reply = done.confirmation_replies[-1]
        c.check("help request never classified safe", reply.verdict == "help")
    c.evidence = {"high_floor": fall.to_dict(), "medium_wait": handler2.fall_assessment.to_dict(),
                  "reply": None if reply is None else {"verdict": reply.verdict, "by": reply.interpreted_by}}
    c.actual = (f"high_floor source={fall.evidence_source} model={fall.model_rationale!r}; "
                f"medium_wait source={handler2.fall_assessment.evidence_source}; "
                f"help reply -> {reply.verdict if reply else 'n/a'} by {reply.interpreted_by if reply else 'n/a'}")


CASES: list[tuple[str, str, str, str, str, Callable[[Case], None]]] = [
    ("AT-E01", "Urgent fall: on the floor 90 s", "UC-01 ext. 3; AR-01",
     "Impact, 90 s no motion, posture floor, bathroom", "HIGH; no question; caregiver alert; bathroom light verified on", case_high_urgent),
    ("AT-E02", "Safe reply", "UC-01 steps 5-6, ext. 4",
     "Impact, 30 s no motion, living room; reply \"I'm fine, I just sat down.\"", "Question 1 asked; nothing sent while waiting; reply safe; closed, no alert, no device", case_safe_reply),
    ("AT-E03", "Help request", "UC-01 steps 6-8",
     "Same fall; reply \"Help, I can't get up.\"", "Reply help; escalated HIGH; alert sent; living-room light verified on", case_help_reply),
    ("AT-E04", "Unclear reply, then safe", "UC-01 ext. 5 (follow-up)",
     "Same fall; replies \"hmm\", then \"no\"", "Follow-up question 2 asked; 'no' is safe; closed", case_unclear_then_safe),
    ("AT-E05", "Unclear twice", "UC-01 ext. 5",
     "Same fall; replies \"hmm\", \"what?\"", "Treated as needing help; alert + light", case_unclear_twice),
    ("AT-E06", "No reply (confirmation timeout)", "UC-01 ext. 5",
     f"Same fall; no reply within {CONFIRMATION_TIMEOUT_S} s", "Recorded as timeout (never safe); escalated; alert + light", case_no_reply),
    ("AT-E07", "MEDIUM fallback: model unavailable", "UC-01 ext. 1; SCRUM-12; NFR-04",
     "Dropped object (rules LOW); model raises timeout", "MEDIUM fallback; resident asked; fallback logged", case_llm_unavailable),
    ("AT-E08", "MEDIUM fallback: model output invalid", "UC-01 ext. 1; SCRUM-12",
     "Dropped object; model returns risk_level \"SEVERE\"", "MEDIUM fallback; resident asked; fallback logged", case_llm_invalid),
    ("AT-E09", "Model cannot lower risk", "UC-01 step 3; safety policy",
     "Urgent fall; model proposes LOW", "Rules keep HIGH; override recorded; urgent response runs", case_llm_cannot_lower),
    ("AT-E10", "Protective light offline", "NFR-04; device verification",
     "Urgent fall; all lights offline", "Light failure reported; outcome FAILED; alert still sent", case_light_offline),
    ("AT-E11", "Protective light state mismatch", "NFR-04; device verification",
     "Urgent fall; light accepts command but reads back power=off", "Accepted but not verified; not reported as success", case_light_mismatch),
    ("AT-E12", "Caregiver alert fails to send", "NFR-04; OR-04",
     "Urgent fall; notification transport down", "Alert FAILED; outcome PARTIAL; escalation skips the level immediately", case_notification_failure),
    ("AT-E13", "Caregiver acknowledges", "UC-01 step 9",
     "Urgent fall; primary caregiver acknowledges (simulated)", "Simulated send is not an ack; ack resolves; no further contacts", case_caregiver_ack),
    ("AT-E14", "Caregiver timeout, secondary acknowledges", "OR-04",
     f"Urgent fall; no ack in {ACK_TIMEOUT_S} s; secondary contact acknowledges", "Secondary contact alerted; resolved; every contact recorded", case_caregiver_timeout),
    ("AT-E15", "No contact acknowledges", "UC-01 ext. 6; OR-04",
     "Urgent fall; two acknowledgement timeouts", "Human Operator informed; event stays open until operator closes", case_escalation_failed),
    ("AT-E16", "Model input is de-identified", "NFR-03",
     "Urgent fall with fictional name, address and phone in event context", "None of them, nor the event ID, reach the model; room reduced to category", case_privacy),
    ("AT-E17", "Classification time recorded", "NFR-02",
     "Five scenarios, rule path", f"Time recorded per event; each under {CLASSIFICATION_LIMIT_MS:g} ms", case_timing),
    ("AT-E18", "Simulated items reported honestly", "README / INTERFACES.md",
     "Urgent fall with escalation", "Event, light result, alert and contacts labelled simulated / fictional", case_simulated_labelling),
]
LIVE_CASE = ("AT-E19", "Live campus-qwen (opt-in)", "UC-01 steps 3, 6; NFR-03",
             "Urgent fall and a help reply with the real campus model", "Rules floor holds; source reported; help never classified safe", live_case)


# --- run and report ----------------------------------------------------------

def run_cases(include_live: bool = False) -> list[Case]:
    specs = CASES + ([LIVE_CASE] if include_live else [])
    results = []
    for case_id, title, requirement, given, expected, fn in specs:
        case = Case(case_id, title, requirement, given, expected)
        try:
            fn(case)
        except Exception as exc:  # a crash is a failed case, never a silent pass
            case.error = f"{type(exc).__name__}: {exc}"
            case.actual = case.actual or "crashed"
        results.append(case)
    return results


def _environment() -> dict[str, str]:
    def version(name: str) -> str:
        try:
            return metadata.version(name)
        except metadata.PackageNotFoundError:
            return "not installed"
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip() or "unknown"
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=5).stdout.strip()
        commit += " (uncommitted changes)" if dirty else ""
    except Exception:
        commit = "unknown"
    return {
        "run_at": datetime.now(ZoneInfo("Australia/Sydney")).strftime("%Y-%m-%d %H:%M %Z"),
        "git_commit": commit,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "langgraph": version("langgraph"),
        "streamlit": version("streamlit"),
    }


def _md(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def write_report(cases: list[Case], env: dict[str, str], path: Path) -> None:
    passed = sum(c.passed for c in cases)
    lines = [
        "# Elderly Safety scenario acceptance report (SCRUM-34)",
        "",
        "AR-01 / UC-01 / OR-04. Generated by `python -m simulation.elderly_acceptance`. "
        "Every case runs through the real shared workflow (LangGraph agents, domain rules, "
        "device read-back verification, escalation). **Sensors, lights and contacts are simulated; "
        "no real device was operated and no real person was contacted.**",
        "",
        "| Run | Value |", "| --- | --- |",
        *[f"| {k} | {_md(v)} |" for k, v in env.items()],
        f"| result | **{passed} / {len(cases)} passed** |",
        "",
        "## Results",
        "",
        "| ID | Case | Requirement | Input | Expected | Actual | Result |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for c in cases:
        result = "PASS" if c.passed else "**FAIL**"
        lines.append(f"| {c.case_id} | {_md(c.title)} | {_md(c.requirement)} | {_md(c.given)} | {_md(c.expected)} | {_md(c.actual)} | {result} |")
    lines += ["", "## Checks per case", ""]
    for c in cases:
        lines.append(f"**{c.case_id} {c.title}**" + ("" if c.passed else " — FAIL"))
        for label, ok in c.checks:
            lines.append(f"- [{'x' if ok else ' '}] {label}")
        if c.error:
            lines.append(f"- error: `{c.error}`")
        lines.append("")
    failed = [c for c in cases if not c.passed]
    lines += ["## Defects", ""]
    if failed:
        lines.append("Raise one linked Jira bug per failing case, fix, rerun this script, and record the retest here.")
        lines += [f"- {c.case_id} {c.title}: {c.error or 'check failed'}" for c in failed]
    else:
        lines.append("No failing case in this run. Defects found earlier and fixed are listed below with their retest.")
    lines += [
        "",
        "| Defect | Found | Fix | Retest |", "| --- | --- | --- | --- |",
        "| Page test read the escalation record as a workflow record (`KeyError: 'workflow'`) | 25 Oct, `tests/test_elderly_ui.py` | Select workflow records by `record_type` (commit 5377e46) | Full suite OK, 25 Oct |",
        "",
        "## Screenshots to attach (Streamlit page)",
        "",
        "Run `streamlit run app.py` → **Elderly Safety**, capture each, and attach to Jira SCRUM-34:",
        "",
        "1. **Safe reply** — \"Fall, then not moving (30 s)\" → Run → quick reply *I'm fine* → banner *No alert needed*.",
        "2. **Help request** — same scenario → type *Help, I can't get up* → Send → banner HIGH, alert SIMULATED, light verified.",
        "3. **No / unclear reply** — same scenario → *Unclear* → second question shown → *No reply (30 s)* → escalated.",
        "4. **Caregiver timeout** — \"Fall, still on the floor (90 s)\" → *No acknowledgement (60 s)* twice → *Human Operator informed* → close with a note.",
        "5. **Device failure** — \"Fall, still on the floor (90 s)\" + *All room lights offline* → FAILED, light error shown.",
        "6. Optional, on VPN with a key — AI toggle on, any scenario → *Model rationale* caption.",
        "",
        "Full machine log of this run: `data/runtime/elderly_acceptance.json` (git-ignored; attach to Jira if needed).",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_log(cases: list[Case], env: dict[str, str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"environment": env, "cases": [c.to_dict() for c in cases]},
                               indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--use-campus-llm", action="store_true", help="add the live campus-qwen case (needs key + VPN)")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    args = parser.parse_args(argv)

    cases = run_cases(include_live=args.use_campus_llm)
    env = _environment()
    write_report(cases, env, args.report)
    write_log(cases, env, args.log)
    for c in cases:
        print(f"{'PASS' if c.passed else 'FAIL'}  {c.case_id}  {c.title}" + (f"  ({c.error})" if c.error else ""))
    passed = sum(c.passed for c in cases)
    print(f"\n{passed}/{len(cases)} passed. Report: {args.report}  Log: {args.log}")
    print("All sensors, lights and contacts were simulated; no real device or person was contacted.")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
