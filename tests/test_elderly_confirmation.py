"""Resident confirmation and caregiver notification (SCRUM-24, UC-01 steps 5-6).

Paths: safe reply, help request, unclear then safe, unclear twice, timeout,
notification failure after escalation, model interpreter fallback, resume
guard, and unchanged behaviour for a domain without confirmation (Pet Care).
"""

from __future__ import annotations

import unittest

from agents.graph import SmartHomeWorkflow
from domains.elderly_safety import ElderlySafetyHandler, default_devices
from domains.elderly_safety.confirmation import CONFIRMATION_TIMEOUT_S, MAX_ATTEMPTS, QUESTIONS, interpret, interpret_by_rules
from domains.pet_care.integration import PetCareHandler
from models import NotificationRequest, NotificationResult
from simulation.devices import SimulatedDeviceTool
from simulation.elderly_scenarios import make_fall_scenario
from simulation.events import make_sensor_event
from simulation.notifications import SimulatedNotificationService


class FailingNotifier:
    def send(self, request: NotificationRequest) -> NotificationResult:
        raise ConnectionError("simulated transport down")


def start(notifier=None, interpreter=None):
    devices = SimulatedDeviceTool(default_devices())
    handler = ElderlySafetyHandler(reply_interpreter=interpreter)
    workflow = SmartHomeWorkflow([handler], devices, notifier=notifier or SimulatedNotificationService())
    return workflow, workflow.run(make_fall_scenario("medium_wait")), devices


def agents_in(result):
    return [e.outcome for e in result.trace]


class RuleInterpreterTests(unittest.TestCase):
    def test_first_attempt(self):
        self.assertEqual(interpret_by_rules(1, "I'm fine, just dropped a cup"), "safe")
        self.assertEqual(interpret_by_rules(1, "help, I can't get up"), "help")
        self.assertEqual(interpret_by_rules(1, "the cat"), "unclear")
        self.assertEqual(interpret_by_rules(1, "   "), "unclear")

    def test_second_attempt_yes_no(self):
        self.assertEqual(interpret_by_rules(2, "yes please"), "help")
        self.assertEqual(interpret_by_rules(2, "no, I'm fine"), "safe")
        self.assertEqual(interpret_by_rules(2, "what?"), "unclear")
        self.assertEqual(interpret_by_rules(2, "my hip hurts"), "help")  # help words still win

    def test_questions_and_limits(self):
        self.assertEqual(CONFIRMATION_TIMEOUT_S, 30)
        self.assertEqual(MAX_ATTEMPTS, 2)
        self.assertEqual(QUESTIONS[1], "Are you okay? Please reply.")
        self.assertEqual(QUESTIONS[2], "Do you need me to contact your family? Please answer 'yes' or 'no'.")


class ModelInterpreterTests(unittest.TestCase):
    def setUp(self):
        self.event = make_fall_scenario("medium_wait")

    def test_valid_model_verdict_is_used(self):
        r = interpret(self.event, 1, "all good thanks", lambda p: {"verdict": "safe", "rationale": "resident reassured"})
        self.assertEqual((r.verdict, r.interpreted_by), ("safe", "llm"))

    def test_model_cannot_turn_help_into_safe(self):
        r = interpret(self.event, 1, "help me", lambda p: {"verdict": "safe"})
        self.assertEqual((r.verdict, r.interpreted_by), ("help", "rules (llm fallback)"))

    def test_invalid_or_failing_model_falls_back(self):
        def explode(p):
            raise TimeoutError()
        for bad in (lambda p: {"verdict": "maybe"}, lambda p: "text", explode):
            r = interpret(self.event, 1, "the cat", bad)
            self.assertEqual((r.verdict, r.interpreted_by), ("unclear", "rules (llm fallback)"))

    def test_model_sees_only_reply_and_attempt(self):
        seen = {}
        interpret(self.event, 2, "no", lambda p: seen.update(p) or {"verdict": "safe"})
        self.assertEqual(set(seen), {"reply", "attempt"})


class ConfirmationFlowTests(unittest.TestCase):
    def test_medium_pauses_with_first_question(self):
        _, result, devices = start()
        self.assertEqual(result.outcome, "AWAITING_CONFIRMATION")
        p = result.pending_confirmation
        self.assertEqual((p.question, p.attempt, p.timeout_seconds, p.max_attempts), (QUESTIONS[1], 1, 30, 2))
        self.assertEqual(devices.dispatch_count, 0)
        self.assertIsNone(result.notification_result)
        self.assertIn("awaiting_confirmation:1", agents_in(result))

    def test_safe_reply_closes_without_alert_or_light(self):
        workflow, pending, devices = start()
        done = workflow.resume(pending, "I'm fine, I just sat down")
        self.assertEqual(done.outcome, "ASSESSED")
        self.assertIsNone(done.pending_confirmation)
        self.assertEqual(done.confirmation_replies[0].verdict, "safe")
        self.assertIsNone(done.notification_result)
        self.assertEqual(devices.dispatch_count, 0)
        self.assertEqual(done.assessment.risk_level, "MEDIUM")
        self.assertIn("resident_reply:safe", agents_in(done))

    def test_help_reply_alerts_caregiver_and_lights_room(self):
        workflow, pending, devices = start()
        done = workflow.resume(pending, "help, I can't get up")
        self.assertEqual(done.outcome, "COMPLETE")
        self.assertEqual(done.assessment.risk_level, "HIGH")
        self.assertIn("resident asked for help", done.assessment.rationale)
        self.assertEqual(done.notification_result.status, "SIMULATED")
        self.assertTrue(done.action_results[0].success)
        self.assertEqual(devices.states["living_light"]["power"], "on")
        self.assertIn("escalated:help", agents_in(done))

    def test_unclear_then_safe(self):
        workflow, pending, devices = start()
        again = workflow.resume(pending, "the cat knocked something")
        self.assertEqual(again.outcome, "AWAITING_CONFIRMATION")
        self.assertEqual(again.pending_confirmation.attempt, 2)
        self.assertEqual(again.pending_confirmation.question, QUESTIONS[2])
        done = workflow.resume(again, "no")
        self.assertEqual(done.outcome, "ASSESSED")
        self.assertEqual([r.verdict for r in done.confirmation_replies], ["unclear", "safe"])
        self.assertEqual(devices.dispatch_count, 0)

    def test_ambiguous_reply_asks_again_then_escalates(self):
        # PR #26 review: replies with a safe start but unrecognised content must not close the event.
        for first, second in (("Okay, I am down", "No, I am down"), ("I am fine, I am down", "No thanks, I am down"),
                              ("Okay, \u6211\u6454\u5012\u4e86\u8d77\u4e0d\u6765", "No, \u6211\u8d77\u4e0d\u6765")):
            with self.subTest(first=first, second=second):
                workflow, pending, devices = start()
                again = workflow.resume(pending, first)
                self.assertEqual(again.outcome, "AWAITING_CONFIRMATION")
                self.assertEqual(again.pending_confirmation.question, QUESTIONS[2])
                self.assertIsNone(again.notification_result)
                done = workflow.resume(again, second)
                self.assertEqual([r.verdict for r in done.confirmation_replies], ["unclear", "unclear"])
                self.assertEqual(done.assessment.risk_level, "HIGH")
                self.assertEqual(done.notification_result.status, "SIMULATED")
                self.assertEqual(devices.states["living_light"]["power"], "on")

    def test_unclear_twice_escalates(self):
        workflow, pending, _ = start()
        again = workflow.resume(pending, "hmm")
        done = workflow.resume(again, "what do you mean")
        self.assertEqual(done.outcome, "COMPLETE")
        self.assertEqual([r.verdict for r in done.confirmation_replies], ["unclear", "unclear"])
        self.assertIn("reply unclear after a follow-up question", done.assessment.rationale)
        self.assertEqual(done.notification_result.status, "SIMULATED")

    def test_timeout_escalates_without_second_question(self):
        workflow, pending, devices = start()
        done = workflow.resume(pending, None)
        self.assertEqual(done.outcome, "COMPLETE")
        self.assertEqual(done.confirmation_replies[0].verdict, "timeout")
        self.assertIn("no reply within the confirmation timeout", done.assessment.rationale)
        self.assertEqual(devices.states["living_light"]["power"], "on")

    def test_notification_failure_after_escalation_is_partial(self):
        workflow, pending, devices = start(notifier=FailingNotifier())
        done = workflow.resume(pending, None)
        self.assertEqual(done.notification_result.status, "FAILED")
        self.assertEqual(done.outcome, "PARTIAL")  # light verified, alert failed
        self.assertEqual(devices.states["living_light"]["power"], "on")

    def test_trace_carries_over_and_keeps_event_id(self):
        workflow, pending, _ = start()
        done = workflow.resume(pending, "help")
        # resumed, reply, escalated, device, notification, result_ready
        self.assertEqual(len(done.trace), len(pending.trace) + 6)
        self.assertEqual(done.trace[len(pending.trace)].outcome, "resumed_confirmation")
        self.assertTrue(all(e.event_id == done.event.event_id for e in done.trace))
        self.assertEqual(done.event.event_id, pending.event.event_id)

    def test_resume_requires_pending(self):
        workflow, pending, _ = start()
        done = workflow.resume(pending, "I'm ok")
        with self.assertRaises(ValueError):
            workflow.resume(done, "I'm ok")

    def test_high_never_pauses(self):
        workflow = SmartHomeWorkflow([ElderlySafetyHandler()], SimulatedDeviceTool(default_devices()), notifier=SimulatedNotificationService())
        result = workflow.run(make_fall_scenario("high_floor"))
        self.assertEqual(result.outcome, "COMPLETE")
        self.assertIsNone(result.pending_confirmation)

    def test_domain_without_confirmation_is_unchanged(self):
        workflow = SmartHomeWorkflow([PetCareHandler()], SimulatedDeviceTool({}), notifier=SimulatedNotificationService())
        result = workflow.run(make_sensor_event("pet_bowl_level", "food_level_percent", 0, "%"))
        self.assertEqual(result.outcome, "COMPLETE")
        self.assertIsNone(result.pending_confirmation)
        self.assertEqual(result.to_dict()["pending_confirmation"], None)


if __name__ == "__main__":
    unittest.main()
