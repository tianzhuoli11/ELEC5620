"""SCRUM-15 rule, fallback, shared-graph and persistence behaviour."""

from __future__ import annotations

from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from domains.home_security.integration import monitor_security_workflow
from domains.home_security.llm import propose_security_risk
from domains.home_security.monitoring import assess_security_event
from models import SensorReading
from services.campus_proxy import CampusProxyConfig
from simulation.security_scenarios import make_security_observation, make_security_scenario


class SecurityRuleTests(unittest.TestCase):
    def test_repeatable_scenario_levels(self) -> None:
        expected = {
            "normal": "LOW", "smoke": "HIGH", "gas": "HIGH",
            "water_leak": "HIGH", "unusual_door": "MEDIUM",
            "suspicious_motion": "MEDIUM", "suspected_intrusion": "HIGH",
        }
        for name, level in expected.items():
            with self.subTest(name=name):
                event = make_security_scenario(name)
                self.assertTrue(event.simulated)
                self.assertEqual(len(event.readings), 5)
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
        self.assertEqual(assess_security_event(expected_door).risk_level, "LOW")
        self.assertEqual(assess_security_event(unexplained_door).risk_level, "MEDIUM")
        self.assertEqual(assess_security_event(closed_valve).risk_level, "MEDIUM")

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

    def test_missing_smoke_does_not_lower_active_gas_alarm(self) -> None:
        event = make_security_scenario("gas")
        result = assess_security_event(replace(event, readings=event.readings[1:]))
        self.assertEqual(result.risk_level, "HIGH")
        self.assertTrue(result.requires_human_review)

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
        for name in ("smoke", "gas"):
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

    def test_shared_agents_assess_and_record_without_later_stage_actions(self) -> None:
        event = make_security_scenario("smoke")
        result = monitor_security_workflow(event, record_path=self.path)
        self.assertEqual(result.assessment.risk_level, "HIGH")
        self.assertTrue(result.assessment.requires_human_review)
        self.assertEqual(result.workflow.domain, "home_security")
        self.assertEqual(result.workflow.outcome, "ASSESSED")
        self.assertEqual(result.workflow.action_results, ())
        self.assertIsNone(result.workflow.notification_result)
        self.assertEqual([entry.agent for entry in result.workflow.trace], [
            "HomeCoordinatorAgent", "MonitoringAgent", "HomeCoordinatorAgent",
        ])
        record = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(record["event"]["event_id"], event.event_id)
        self.assertEqual(record["assessment"]["risk_level"], "HIGH")
        self.assertEqual(record["workflow"]["outcome"], "ASSESSED")
        self.assertGreaterEqual(record["classification_ms"], 0)

    def test_each_preset_runs_through_shared_workflow(self) -> None:
        expected = {
            "normal": "LOW", "smoke": "HIGH", "gas": "HIGH",
            "water_leak": "HIGH", "unusual_door": "MEDIUM",
            "suspicious_motion": "MEDIUM", "suspected_intrusion": "HIGH",
        }
        for name, level in expected.items():
            with self.subTest(name=name):
                result = monitor_security_workflow(
                    make_security_scenario(name), record_path=self.path,
                )
                self.assertEqual(result.assessment.risk_level, level)
                self.assertEqual(result.workflow.outcome, "ASSESSED")
                self.assertEqual(result.workflow.action_results, ())
                self.assertIsNone(result.workflow.notification_result)
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

    def test_campus_client_uses_allowlisted_prompt_and_shared_transport(self) -> None:
        event = make_security_scenario("gas")
        event = replace(event, context={**event.context, "private_address": "private-do-not-send"})
        reply = {"choices": [{"message": {"content": json.dumps({
            "risk_level": "HIGH", "rationale": "Gas alarm is active."
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
        self.assertNotIn("private-do-not-send", self.path.read_text(encoding="utf-8"))
        self.assertEqual(result.assessment.llm_status, "ACCEPTED")
        self.assertFalse(result.assessment.fallback_used)


if __name__ == "__main__":
    unittest.main()
