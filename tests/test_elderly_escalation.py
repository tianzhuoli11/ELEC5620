"""Multi-level emergency escalation (SCRUM-25, OR-04; UC-01 step 9 / extension 6).

Paths: acknowledged at level 1, acknowledged at level 2, all timeouts ->
operator informed -> operator closes, failed send skips ahead without
waiting, every level failing, guards on invalid transitions, no tracking
when no alert was sent, audit records, follow-up sent via the coordinator.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from domains.elderly_safety import default_devices
from domains.elderly_safety.escalation import ACK_TIMEOUT_S, CONTACT_LEVELS, OPERATOR_REF
from domains.elderly_safety.integration import (
    acknowledge_alert, acknowledgement_timeout, build_workflow, operator_close_event,
    resume_elderly_safety, run_elderly_safety, start_escalation,
)
from models import NotificationRequest, NotificationResult
from simulation.devices import SimulatedDeviceTool
from simulation.elderly_scenarios import make_fall_scenario


class ScriptedNotifier:
    """Returns the scripted status per call (default SIMULATED) and records requests."""

    def __init__(self, statuses=()):
        self.statuses = list(statuses)
        self.sent: list[NotificationRequest] = []

    def send(self, request: NotificationRequest) -> NotificationResult:
        self.sent.append(request)
        status = self.statuses.pop(0) if self.statuses else "SIMULATED"
        if status == "RAISE":
            raise ConnectionError("simulated transport down")
        return NotificationResult(request.event_id, status, f"scripted {status}")


def high_fall(notifier=None, record_path=None):
    notifier = notifier or ScriptedNotifier()
    workflow, handler = build_workflow(device_tool=SimulatedDeviceTool(default_devices()), notifier=notifier)
    result = run_elderly_safety(make_fall_scenario("high_floor"), workflow=workflow, handler=handler, record_path=record_path)
    return workflow, handler, result, notifier


class EscalationTests(unittest.TestCase):
    def test_policy_values(self):
        self.assertEqual(ACK_TIMEOUT_S, 60)
        self.assertEqual([role for role, _ in CONTACT_LEVELS], ["primary caregiver", "secondary contact"])

    def test_level_one_acknowledgement_resolves(self):
        workflow, _, result, notifier = high_fall()
        state = start_escalation(result, workflow=workflow, record_path=None)
        self.assertEqual(state.status, "AWAITING_ACK")
        self.assertFalse(state.current.acknowledged)  # a simulated send is not an acknowledgement
        state = acknowledge_alert(state, record_path=None)
        self.assertEqual(state.status, "RESOLVED")
        self.assertFalse(state.is_open)
        self.assertEqual([a.outcome for a in state.attempts], ["acknowledged"])
        self.assertEqual(len(notifier.sent), 1)  # only the original alert

    def test_timeout_then_level_two_acknowledges(self):
        workflow, _, result, notifier = high_fall()
        state = start_escalation(result, workflow=workflow, record_path=None)
        state = acknowledgement_timeout(state, workflow=workflow, record_path=None)
        self.assertEqual((state.status, state.current.level, state.current.role), ("AWAITING_ACK", 2, "secondary contact"))
        self.assertEqual(notifier.sent[-1].recipient_ref, "fictional-family-member")
        self.assertIn("not acknowledged within 60 s", notifier.sent[-1].message)
        state = acknowledge_alert(state, record_path=None)
        self.assertEqual(state.status, "RESOLVED")
        self.assertEqual([a.outcome for a in state.attempts], ["ack_timeout", "acknowledged"])

    def test_all_timeouts_inform_operator_and_keep_event_open(self):
        workflow, _, result, notifier = high_fall()
        state = start_escalation(result, workflow=workflow, record_path=None)
        state = acknowledgement_timeout(state, workflow=workflow, record_path=None)
        state = acknowledgement_timeout(state, workflow=workflow, record_path=None)
        self.assertEqual(state.status, "ESCALATION_FAILED")
        self.assertTrue(state.is_open)
        self.assertEqual(state.current.recipient_ref, OPERATOR_REF)
        self.assertEqual([a.outcome for a in state.attempts], ["ack_timeout", "ack_timeout", "operator_informed"])
        self.assertIn("Event remains open", notifier.sent[-1].message)
        with self.assertRaises(ValueError):
            acknowledge_alert(state, record_path=None)  # nobody left to acknowledge
        closed = operator_close_event(state, "operator phoned the resident", record_path=None)
        self.assertEqual(closed.status, "CLOSED_BY_OPERATOR")
        self.assertFalse(closed.is_open)
        self.assertIn("closed by human operator: operator phoned the resident", closed.log)

    def test_failed_first_send_skips_to_next_level_without_waiting(self):
        workflow, _, result, notifier = high_fall(ScriptedNotifier(["FAILED"]))
        self.assertEqual(result.notification_result.status, "FAILED")
        state = start_escalation(result, workflow=workflow, record_path=None)
        self.assertEqual(state.current.level, 2)
        self.assertEqual([a.outcome for a in state.attempts], ["send_failed", "awaiting_ack"])
        self.assertIn("failed to send", notifier.sent[-1].message)

    def test_every_level_failing_reaches_operator_immediately(self):
        workflow, _, result, notifier = high_fall(ScriptedNotifier(["FAILED", "RAISE", "FAILED"]))
        state = start_escalation(result, workflow=workflow, record_path=None)
        self.assertEqual(state.status, "ESCALATION_FAILED")
        self.assertEqual([a.send_status for a in state.attempts], ["FAILED", "FAILED", "FAILED"])
        self.assertEqual([a.outcome for a in state.attempts], ["send_failed", "send_failed", "operator_informed"])
        self.assertEqual(len(notifier.sent), 3)

    def test_cannot_acknowledge_a_failed_send(self):
        from domains.elderly_safety import escalation
        workflow, _, result, _ = high_fall(ScriptedNotifier(["FAILED"]))
        state = escalation.start(result)  # raw start, before skipping
        with self.assertRaises(ValueError):
            escalation.acknowledge(state)

    def test_guards(self):
        workflow, _, result, _ = high_fall()
        state = acknowledge_alert(start_escalation(result, workflow=workflow, record_path=None), record_path=None)
        with self.assertRaises(ValueError):
            acknowledgement_timeout(state, workflow=workflow, record_path=None)
        with self.assertRaises(ValueError):
            operator_close_event(state, record_path=None)

    def test_no_tracking_without_an_alert(self):
        workflow, handler = build_workflow(device_tool=SimulatedDeviceTool(default_devices()), notifier=ScriptedNotifier())
        paused = run_elderly_safety(make_fall_scenario("medium_wait"), workflow=workflow, handler=handler, record_path=None)
        self.assertIsNone(start_escalation(paused, workflow=workflow, record_path=None))  # still asking the resident
        safe = resume_elderly_safety(paused, "I'm fine", workflow=workflow, handler=handler, record_path=None)
        self.assertIsNone(start_escalation(safe, workflow=workflow, record_path=None))  # no alert was sent

    def test_escalation_after_resident_timeout(self):
        workflow, handler = build_workflow(device_tool=SimulatedDeviceTool(default_devices()), notifier=ScriptedNotifier())
        paused = run_elderly_safety(make_fall_scenario("medium_wait"), workflow=workflow, handler=handler, record_path=None)
        escalated = resume_elderly_safety(paused, None, workflow=workflow, handler=handler, record_path=None)
        state = start_escalation(escalated, workflow=workflow, record_path=None)
        self.assertEqual(state.status, "AWAITING_ACK")
        self.assertEqual(state.event_id, paused.event.event_id)

    def test_every_step_is_recorded(self):
        path = Path(tempfile.mkdtemp()) / "elderly.jsonl"
        workflow, _, result, _ = high_fall(record_path=path)
        state = start_escalation(result, workflow=workflow, record_path=path)
        state = acknowledgement_timeout(state, workflow=workflow, record_path=path)
        acknowledge_alert(state, record_path=path)
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([r["record_type"] for r in records], ["elderly_safety", "elderly_escalation", "elderly_escalation", "elderly_escalation"])
        self.assertEqual([r["escalation"]["status"] for r in records[1:]], ["AWAITING_ACK", "AWAITING_ACK", "RESOLVED"])
        self.assertTrue(all(r["escalation"]["simulated"] for r in records[1:]))
        self.assertTrue(all(r["escalation"]["event_id"] == result.event.event_id for r in records[1:]))

    def test_workflow_notify_reports_adapter_failure_instead_of_raising(self):
        workflow, _, result, _ = high_fall(ScriptedNotifier(["SIMULATED", "RAISE"]))
        outcome = workflow.notify(NotificationRequest(result.event.event_id, "x", "m", True))
        self.assertEqual(outcome.status, "FAILED")


if __name__ == "__main__":
    unittest.main()
