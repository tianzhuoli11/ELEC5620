"""UC-04 fixed risk, confirmation, device verification and audit behaviour."""

from __future__ import annotations

from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from domains.home_security.integration import monitor_security_workflow, resume_security_workflow
from domains.home_security.llm import propose_security_risk
from domains.home_security.monitoring import READING_TYPES, assess_security_event
from models import SensorReading
from services.campus_proxy import CampusProxyConfig
from simulation.security_scenarios import make_security_observation, make_security_scenario
from simulation.devices import SimulatedDeviceTool
from domains.home_security.response import INITIAL_DEVICE_STATES


class SecurityRuleTests(unittest.TestCase):
    def test_repeatable_scenario_levels(self) -> None:
        expected = {
            "normal": "LOW", "smoke": "HIGH", "device_failure": "HIGH", "gas": "HIGH",
            "water_leak": "HIGH", "appliance_overheat": "HIGH",
            "appliance_unexpected_run": "MEDIUM", "unusual_door": "MEDIUM",
            "unusual_window": "MEDIUM", "abnormal_lock_access": "MEDIUM",
            "suspicious_motion": "MEDIUM", "suspected_intrusion": "HIGH",
            "window_intrusion": "HIGH",
        }
        for name, level in expected.items():
            with self.subTest(name=name):
                event = make_security_scenario(name)
                self.assertTrue(event.simulated)
                self.assertEqual(len(event.readings), len(READING_TYPES))
                self.assertEqual(assess_security_event(event).risk_level, level)

    def test_context_changes_risk_without_presetting_result(self) -> None:
        expected_door = make_security_observation(
            {"door_open": 1}, authorized_entry=True, front_door_lock="unlocked",
        )
        unexplained_door = make_security_observation(
            {"door_open": 1}, home_mode="AWAY", recent_activity="NONE",
            authorized_entry=False, front_door_lock="unlocked",
        )
        closed_valve = make_security_observation({"water_leak": 1}, water_valve="closed")
        expected_window = make_security_observation({"window_open": 1}, recent_activity="EXPECTED")
        self.assertEqual(assess_security_event(expected_door).risk_level, "LOW")
        self.assertEqual(assess_security_event(unexplained_door).risk_level, "MEDIUM")
        self.assertEqual(assess_security_event(closed_valve).risk_level, "MEDIUM")
        self.assertEqual(assess_security_event(expected_window).risk_level, "LOW")

    def test_multiple_events_keep_highest_fixed_risk(self) -> None:
        event = make_security_observation(
            {"water_leak": 1, "appliance_overheat_alarm": 1}, water_valve="closed",
        )
        result = assess_security_event(event)
        self.assertEqual(result.risk_level, "HIGH")
        self.assertIn("overheat", result.rationale)

    def test_missing_duplicate_and_invalid_readings_need_review(self) -> None:
        normal = make_security_scenario("normal")
        missing = replace(normal, readings=normal.readings[1:])
        duplicate = replace(normal, readings=normal.readings + (normal.readings[0],))
        bad = SensorReading("simulated-smoke", "smoke_alarm", 2, "state", normal.timestamp)
        invalid = replace(normal, readings=(bad,) + normal.readings[1:])
        for event in (missing, duplicate, invalid):
            with self.subTest(readings=event.readings):
                result = assess_security_event(event)
                self.assertEqual(result.risk_level, "MEDIUM")
                self.assertTrue(result.requires_human_review)
                self.assertIn("missing_or_invalid", result.evidence)

    def test_existing_five_sensor_events_keep_their_previous_low_risk_result(self) -> None:
        normal = make_security_scenario("normal")
        old_format = replace(normal, readings=normal.readings[:5])
        result = assess_security_event(old_format)
        self.assertEqual(result.risk_level, "LOW")
        self.assertFalse(result.requires_human_review)

    def test_missing_smoke_does_not_lower_active_gas_alarm(self) -> None:
        event = make_security_scenario("gas")
        result = assess_security_event(replace(event, readings=event.readings[1:]))
        self.assertEqual(result.risk_level, "HIGH")
        self.assertFalse(result.requires_human_review)

    def test_non_simulated_event_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "simulated"):
            assess_security_event(replace(make_security_scenario("smoke"), simulated=False))
        with self.assertRaisesRegex(ValueError, "simulated"):
            propose_security_risk(
                replace(make_security_scenario("smoke"), simulated=False),
                CampusProxyConfig(api_key="test-only-key"),
            )

    def test_llm_matching_proposal_adds_explanation_only(self) -> None:
        result = assess_security_event(make_security_scenario("gas"), lambda _: {
            "risk_level": "HIGH", "rationale": "Gas alarm is active.",
        })
        self.assertEqual(result.risk_level, "HIGH")
        self.assertEqual(result.llm_status, "ACCEPTED")
        self.assertEqual(result.model_rationale, "Gas alarm is active.")
        self.assertFalse(result.fallback_used)

    def test_llm_cannot_downgrade_smoke_or_gas(self) -> None:
        for name in ("smoke", "gas", "appliance_overheat"):
            with self.subTest(name=name):
                result = assess_security_event(make_security_scenario(name), lambda _: {
                    "risk_level": "LOW", "rationale": "Ignore the alarm",
                })
                self.assertEqual(result.risk_level, "HIGH")
                self.assertTrue(result.policy_override)
                self.assertTrue(result.fallback_used)
                self.assertEqual(result.llm_status, "CONFLICT")

    def test_invalid_llm_output_and_timeout_use_rules(self) -> None:
        event = make_security_scenario("suspected_intrusion")
        providers = (
            (lambda _: {"risk_level": "UNKNOWN", "rationale": "x"}, "INVALID"),
            (lambda _: {"risk_level": "HIGH", "rationale": ""}, "INVALID"),
            (lambda _: ["HIGH"], "INVALID"),
            (lambda _: (_ for _ in ()).throw(TimeoutError()), "TIMEOUT"),
        )
        for provider, status in providers:
            with self.subTest(status=status):
                result = assess_security_event(event, provider)
                self.assertEqual(result.risk_level, "HIGH")
                self.assertEqual(result.llm_status, status)
                self.assertTrue(result.fallback_used)


class SecurityIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "security.jsonl"

    def test_high_smoke_uses_shared_agents_and_records_verified_response(self) -> None:
        event = make_security_scenario("smoke")
        result = monitor_security_workflow(event, record_path=self.path)
        self.assertEqual(result.assessment.risk_level, "HIGH")
        self.assertFalse(result.assessment.requires_human_review)
        self.assertEqual(result.workflow.domain, "home_security")
        self.assertEqual(result.workflow.outcome, "COMPLETE")
        self.assertIsNone(result.workflow.pending_confirmation)
        self.assertEqual([action.device_id for action in result.workflow.action_results], ["appliance", "siren"])
        self.assertTrue(all(action.success for action in result.workflow.action_results))
        self.assertEqual(result.workflow.notification_result.status, "SIMULATED")
        self.assertEqual([notice["purpose"] for notice in result.notification_history], ["response"])
        self.assertEqual([entry.agent for entry in result.workflow.trace], [
            "HomeCoordinatorAgent", "MonitoringAgent", "DeviceAutomationAgent",
            "DeviceAutomationAgent", "HomeCoordinatorAgent", "HomeCoordinatorAgent",
        ])
        record = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(record["event"]["event_id"], event.event_id)
        self.assertEqual(record["assessment"]["risk_level"], "HIGH")
        self.assertEqual(record["workflow"]["outcome"], "COMPLETE")
        self.assertTrue(record["workflow"]["action_results"][0]["verified"])
        self.assertGreaterEqual(record["classification_ms"], 0)

    def test_classification_and_workflow_durations_are_recorded_separately(self) -> None:
        # The notification and device steps occur after the handler's assessment.
        with patch("domains.home_security.integration.perf_counter",
                   side_effect=(10.0, 10.005, 10.015, 10.1)):
            result = monitor_security_workflow(make_security_scenario("smoke"), record_path=self.path)
        record = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(result.classification_ms, 10.0)
        self.assertEqual(result.workflow_ms, 100.0)
        self.assertEqual(record["classification_ms"], 10.0)
        self.assertEqual(record["workflow_ms"], 100.0)

    def test_failed_smoke_notification_is_recorded_as_partial(self) -> None:
        class BrokenNotifier:
            def send(self, request):
                raise TimeoutError("fictional notification outage")

        result = monitor_security_workflow(
            make_security_scenario("smoke"), record_path=self.path,
            notifier=BrokenNotifier(),
        )
        self.assertTrue(all(item.success for item in result.workflow.action_results))
        self.assertEqual(result.workflow.notification_result.status, "FAILED")
        self.assertEqual(result.workflow.outcome, "PARTIAL")
        record = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(record["notifications"][0]["status"], "FAILED")
        self.assertEqual(record["workflow"]["outcome"], "PARTIAL")

    def test_failed_confirmation_notice_never_authorizes_medium_actions(self) -> None:
        class BrokenNotifier:
            def send(self, request):
                raise TimeoutError("fictional notification outage")

        first = monitor_security_workflow(
            make_security_scenario("unusual_door"), record_path=self.path,
            notifier=BrokenNotifier(),
        )
        self.assertEqual(first.workflow.notification_result.status, "FAILED")
        self.assertEqual(first.workflow.action_results, ())
        final = resume_security_workflow(first, None, record_path=self.path)
        self.assertEqual(final.workflow.confirmation_replies[-1].verdict, "timeout")
        self.assertEqual(final.device_tool.dispatch_count, 0)
        self.assertEqual([item["status"] for item in final.notification_history], ["FAILED", "FAILED"])
        records = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(records[0]["workflow"]["outcome"], "AWAITING_CONFIRMATION")
        self.assertEqual(records[1]["workflow"]["outcome"], "FAILED")

    def test_each_preset_runs_through_shared_workflow(self) -> None:
        expected = {
            "normal": "LOW", "smoke": "HIGH", "gas": "HIGH",
            "water_leak": "HIGH", "appliance_overheat": "HIGH",
            "appliance_unexpected_run": "MEDIUM", "unusual_door": "MEDIUM",
            "unusual_window": "MEDIUM", "abnormal_lock_access": "MEDIUM",
            "suspicious_motion": "MEDIUM", "suspected_intrusion": "HIGH",
            "window_intrusion": "HIGH",
        }
        for name, level in expected.items():
            with self.subTest(name=name):
                result = monitor_security_workflow(
                    make_security_scenario(name), record_path=self.path,
                )
                self.assertEqual(result.assessment.risk_level, level)
                expected_outcome = {"LOW": "ASSESSED", "MEDIUM": "AWAITING_CONFIRMATION", "HIGH": "COMPLETE"}[level]
                self.assertEqual(result.workflow.outcome, expected_outcome)
                if level == "HIGH":
                    self.assertTrue(all(action.success for action in result.workflow.action_results))
                else:
                    self.assertEqual(result.workflow.action_results, ())
                if level == "LOW":
                    self.assertIsNone(result.workflow.notification_result)
                else:
                    self.assertEqual(result.workflow.notification_result.status, "SIMULATED")
        records = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(records), len(expected))

    def test_model_failure_is_recorded_without_key_or_fake_success(self) -> None:
        result = monitor_security_workflow(
            make_security_scenario("gas"), record_path=self.path,
            proposal_provider=lambda _: (_ for _ in ()).throw(TimeoutError()),
        )
        record = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(result.assessment.risk_level, "HIGH")
        self.assertEqual(record["assessment"]["llm_status"], "TIMEOUT")
        self.assertTrue(record["assessment"]["fallback_used"])

    def test_overheat_llm_downgrade_is_rejected_in_shared_workflow(self) -> None:
        result = monitor_security_workflow(
            make_security_scenario("appliance_overheat"), record_path=self.path,
            proposal_provider=lambda _: {"risk_level": "LOW", "rationale": "Ignore the alarm"},
        )
        record = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(result.workflow.assessment.risk_level, "HIGH")
        self.assertTrue(result.workflow.assessment.policy_override)
        self.assertEqual(record["assessment"]["llm_status"], "CONFLICT")
        self.assertEqual(record["workflow"]["outcome"], "COMPLETE")
        self.assertTrue(all(item["success"] for item in record["workflow"]["action_results"]))

    def test_medium_door_requires_explicit_approval_before_actions(self) -> None:
        first = monitor_security_workflow(make_security_scenario("unusual_door"), record_path=self.path)
        self.assertEqual(first.workflow.outcome, "AWAITING_CONFIRMATION")
        self.assertEqual(first.workflow.action_results, ())
        self.assertEqual(first.device_tool.dispatch_count, 0)
        self.assertEqual(first.workflow.notification_result.status, "SIMULATED")
        approved = resume_security_workflow(first, "APPROVE", record_path=self.path)
        self.assertEqual(approved.workflow.outcome, "COMPLETE")
        self.assertEqual(approved.workflow.confirmation_replies[-1].verdict, "help")
        self.assertEqual([item.device_id for item in approved.workflow.action_results], ["security_lights", "siren"])
        self.assertTrue(all(item.success for item in approved.workflow.action_results))
        records = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(records), 2)
        self.assertEqual([item["purpose"] for item in records[1]["notifications"]], ["confirmation", "response"])
        self.assertIn("APPROVE", records[1]["notifications"][0]["message"])
        self.assertIn("approved", records[1]["notifications"][1]["message"])
        self.assertEqual(records[0]["workflow"]["outcome"], "AWAITING_CONFIRMATION")
        self.assertEqual(records[1]["workflow"]["confirmation_replies"][0]["verdict"], "help")
        self.assertEqual(records[0]["classification_ms"], records[1]["classification_ms"])
        self.assertGreaterEqual(records[1]["workflow_ms"], 0)

    def test_rejection_closes_without_device_action(self) -> None:
        first = monitor_security_workflow(make_security_scenario("unusual_door"), record_path=self.path)
        rejected = resume_security_workflow(first, "REJECT", record_path=self.path)
        self.assertEqual(rejected.workflow.confirmation_replies[-1].verdict, "safe")
        self.assertEqual(rejected.workflow.outcome, "COMPLETE")
        self.assertEqual(rejected.workflow.action_results, ())
        self.assertEqual(rejected.device_tool.dispatch_count, 0)
        self.assertIn("rejected", rejected.notification_history[-1]["message"])
        self.assertNotIn("timed out", rejected.notification_history[-1]["message"])

    def test_timeout_never_grants_medium_device_permission(self) -> None:
        first = monitor_security_workflow(make_security_scenario("unusual_door"), record_path=self.path)
        timed_out = resume_security_workflow(first, None, record_path=self.path)
        self.assertEqual(timed_out.workflow.confirmation_replies[-1].verdict, "timeout")
        self.assertEqual(timed_out.workflow.action_results, ())
        self.assertEqual(timed_out.device_tool.dispatch_count, 0)
        self.assertEqual(timed_out.workflow.notification_result.status, "SIMULATED")
        self.assertIn("confirmation_verdict=timeout", timed_out.workflow.assessment.evidence)

    def test_ambiguous_reply_retries_then_falls_back_safely(self) -> None:
        first = monitor_security_workflow(make_security_scenario("unusual_door"), record_path=self.path)
        second = resume_security_workflow(first, "maybe", record_path=self.path)
        self.assertEqual(second.workflow.pending_confirmation.attempt, 2)
        final = resume_security_workflow(second, None, record_path=self.path)
        self.assertIsNone(final.workflow.pending_confirmation)
        self.assertEqual([item.verdict for item in final.workflow.confirmation_replies], ["unclear", "timeout"])
        self.assertEqual(final.workflow.action_results, ())
        self.assertEqual(len(self.path.read_text(encoding="utf-8").splitlines()), 3)

    def test_invalid_duplicate_sensor_cannot_trigger_a_device_on_approval(self) -> None:
        event = make_security_scenario("normal")
        duplicate_alarm = replace(event.readings[0], value=1)
        event = replace(event, readings=event.readings + (duplicate_alarm,))
        first = monitor_security_workflow(event, record_path=self.path)
        self.assertEqual(first.workflow.assessment.risk_level, "MEDIUM")
        approved = resume_security_workflow(first, "APPROVE", record_path=self.path)
        self.assertEqual(approved.workflow.action_results, ())
        self.assertEqual(approved.device_tool.dispatch_count, 0)
        self.assertIn("no safe automatic action", approved.notification_history[-1]["message"])

    def test_high_gas_closes_valve_without_normal_confirmation(self) -> None:
        result = monitor_security_workflow(make_security_scenario("gas"), record_path=self.path)
        self.assertIsNone(result.workflow.pending_confirmation)
        self.assertEqual([item.device_id for item in result.workflow.action_results], ["gas_valve", "siren"])
        self.assertEqual(result.device_tool.read_state("gas_valve"), {"open": False})
        self.assertEqual(result.device_tool.read_state("siren"), {"power": "on"})

    def test_offline_primary_device_uses_siren_as_safe_alternative(self) -> None:
        result = monitor_security_workflow(
            make_security_scenario("gas"), record_path=self.path,
            offline_devices=("gas_valve",),
        )
        self.assertEqual(result.workflow.outcome, "PARTIAL")
        self.assertFalse(result.workflow.action_results[0].success)
        self.assertEqual(result.workflow.action_results[0].attempts, 2)
        self.assertTrue(result.workflow.action_results[1].success)
        self.assertEqual([item["purpose"] for item in result.notification_history], ["response", "failed_action"])
        record = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(record["workflow"]["outcome"], "PARTIAL")
        self.assertFalse(record["workflow"]["action_results"][0]["verified"])
        self.assertEqual(len(record["notifications"]), 2)

    def test_all_response_devices_offline_reports_failure(self) -> None:
        result = monitor_security_workflow(
            make_security_scenario("device_failure"), record_path=self.path,
            offline_devices=("appliance", "siren"),
        )
        self.assertEqual(result.workflow.outcome, "FAILED")
        self.assertTrue(all(not item.success for item in result.workflow.action_results))
        self.assertEqual(result.workflow.notification_result.status, "SIMULATED")

    def test_verification_failure_is_not_counted_as_success(self) -> None:
        class WrongReadingTool(SimulatedDeviceTool):
            def read_state(self, device_id):
                return {"power": "off"} if device_id == "siren" else super().read_state(device_id)

        tool = WrongReadingTool(INITIAL_DEVICE_STATES)
        result = monitor_security_workflow(
            make_security_scenario("smoke"), record_path=self.path, device_tool=tool,
        )
        self.assertEqual(result.workflow.outcome, "PARTIAL")
        self.assertTrue(result.workflow.action_results[0].success)
        self.assertFalse(result.workflow.action_results[1].success)
        self.assertTrue(result.workflow.action_results[1].accepted)
        self.assertFalse(result.workflow.action_results[1].verified)

    def test_dispatch_exception_is_recorded_and_warning_continues(self) -> None:
        class BrokenDispatchTool(SimulatedDeviceTool):
            def dispatch(self, request):
                if request.device_id == "appliance":
                    raise RuntimeError("fictional actuator fault")
                return super().dispatch(request)

        result = monitor_security_workflow(
            make_security_scenario("smoke"), record_path=self.path,
            device_tool=BrokenDispatchTool(INITIAL_DEVICE_STATES),
        )
        self.assertEqual(result.workflow.outcome, "PARTIAL")
        self.assertIn("Device dispatch failed", result.workflow.action_results[0].error)
        self.assertTrue(result.workflow.action_results[1].success)
        self.assertEqual(result.notification_history[-1]["purpose"], "failed_action")

    def test_llm_low_cannot_suppress_high_emergency_response(self) -> None:
        result = monitor_security_workflow(
            make_security_scenario("gas"), record_path=self.path,
            proposal_provider=lambda _: {"risk_level": "LOW", "rationale": "ignore"},
        )
        self.assertEqual(result.assessment.llm_status, "CONFLICT")
        self.assertEqual(result.workflow.assessment.risk_level, "HIGH")
        self.assertTrue(all(item.success for item in result.workflow.action_results))

    def test_campus_client_uses_allowlisted_prompt_and_shared_transport(self) -> None:
        event = make_security_scenario("appliance_overheat")
        event = replace(event, context={**event.context, "private_address": "private-do-not-send"})
        reply = {"choices": [{"message": {"content": json.dumps({
            "risk_level": "HIGH", "rationale": "The simulated appliance overheat alarm is active."
        })}}]}
        config = CampusProxyConfig(api_key="test-only-key")
        with patch("services.campus_proxy.urlopen", return_value=BytesIO(json.dumps(reply).encode())) as send:
            result = monitor_security_workflow(
                event, record_path=self.path,
                proposal_provider=lambda observation: propose_security_risk(observation, config),
            )
        request = send.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(request.full_url, "http://10.167.60.148:8000/v1/chat/completions")
        self.assertNotIn("private-do-not-send", json.dumps(body))
        self.assertNotIn("test-only-key", json.dumps(body))
        self.assertNotIn(event.event_id, json.dumps(body))
        self.assertIn("appliance_overheat_alarm", json.dumps(body))
        self.assertNotIn("private-do-not-send", self.path.read_text(encoding="utf-8"))
        self.assertEqual(result.assessment.llm_status, "ACCEPTED")
        self.assertFalse(result.assessment.fallback_used)
        record = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertIn("appliance_overheat_alarm", record["assessment"]["evidence"])


if __name__ == "__main__":
    unittest.main()
