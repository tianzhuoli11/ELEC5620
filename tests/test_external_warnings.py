"""OR-06 simulated source validation, area relevance and shared workflow."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from domains.home_security.external_warnings import HAZARD_TYPES, assess_external_warning
from domains.home_security.integration import monitor_security_workflow
from domains.home_security.llm import propose_external_warning_risk
from services.campus_proxy import CampusProxyConfig
from simulation.external_warning_scenarios import make_warning_scenario


def changed_warning(event, **fields):
    warning = {**event.context["warning"], **fields}
    return replace(event, context={"warning": warning})


class ExternalWarningTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "security.jsonl"

    def test_all_four_relevant_hazards_use_shared_agents(self) -> None:
        cases = {
            "relevant_earthquake": ("HIGH", True),
            "relevant_flood": ("MEDIUM", False),
            "relevant_storm": ("HIGH", True),
            "relevant_bushfire": ("HIGH", True),
        }
        for name, (level, activates_mode) in cases.items():
            with self.subTest(name=name):
                result = monitor_security_workflow(make_warning_scenario(name), record_path=self.path)
                self.assertTrue(result.assessment.valid)
                self.assertTrue(result.assessment.relevant)
                self.assertIn(result.assessment.warning_type, HAZARD_TYPES)
                self.assertEqual(result.assessment.risk_level, level)
                self.assertEqual(result.workflow.outcome, "COMPLETE")
                self.assertEqual(result.workflow.notification_result.status, "SIMULATED")
                self.assertEqual([item.agent for item in result.workflow.trace[:2]], [
                    "HomeCoordinatorAgent", "MonitoringAgent",
                ])
                if activates_mode:
                    self.assertEqual([item.device_id for item in result.workflow.action_results], ["emergency_mode"])
                    self.assertTrue(result.workflow.action_results[0].success)
                    self.assertEqual(result.device_tool.read_state("emergency_mode"), {"active": True})
                else:
                    self.assertEqual(result.workflow.action_results, ())
                    self.assertEqual(result.device_tool.dispatch_count, 0)

    def test_irrelevant_valid_warning_is_only_recorded(self) -> None:
        result = monitor_security_workflow(make_warning_scenario("irrelevant_flood"), record_path=self.path)
        self.assertTrue(result.assessment.valid)
        self.assertFalse(result.assessment.relevant)
        self.assertEqual(result.assessment.risk_level, "LOW")
        self.assertEqual(result.workflow.outcome, "ASSESSED")
        self.assertIsNone(result.workflow.notification_result)
        self.assertEqual(result.device_tool.dispatch_count, 0)
        record = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(record["record_type"], "external_warning_workflow")
        self.assertEqual(record["event"]["raw_warning"]["areas"], ["BLUE_MOUNTAINS"])
        self.assertFalse(record["assessment"]["relevant"])
        self.assertEqual(record["workflow"]["outcome"], "ASSESSED")

    def test_untrusted_source_and_missing_fields_cannot_notify_or_act(self) -> None:
        valid = make_warning_scenario("relevant_bushfire")
        cases = (
            make_warning_scenario("invalid_source"),
            changed_warning(valid, source_id="simulated-untrusted-feed"),
            changed_warning(valid, warning_id=""),
            changed_warning(valid, areas=[]),
            changed_warning(valid, severity="UNKNOWN"),
            changed_warning(valid, simulated=False),
            replace(valid, simulated=False),
            replace(valid, context={}),
        )
        for event in cases:
            with self.subTest(warning=event.context.get("warning")):
                result = monitor_security_workflow(
                    event, record_path=self.path,
                    proposal_provider=lambda _: self.fail("invalid warning must not reach the LLM"),
                )
                self.assertFalse(result.assessment.valid)
                self.assertFalse(result.assessment.relevant)
                self.assertEqual(result.assessment.risk_level, "LOW")
                self.assertTrue(result.assessment.validation_errors)
                self.assertEqual(result.assessment.llm_status, "NOT_REQUESTED")
                self.assertEqual(result.workflow.action_results, ())
                self.assertIsNone(result.workflow.notification_result)
                self.assertEqual(result.device_tool.dispatch_count, 0)
        records = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(records), len(cases))
        self.assertEqual(records[0]["event"]["raw_warning"], cases[0].context["warning"])

    def test_expired_future_and_timezone_free_warnings_are_invalid(self) -> None:
        event = make_warning_scenario("relevant_storm")
        past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        cases = (
            changed_warning(event, expires_at=past),
            changed_warning(event, issued_at=future),
            changed_warning(event, issued_at="2026-10-28T12:00:00"),
        )
        for item in cases:
            with self.subTest(warning=item.context["warning"]):
                result = assess_external_warning(item)
                self.assertFalse(result.valid)
                self.assertFalse(result.relevant)

    def test_llm_cannot_promote_irrelevant_or_downgrade_emergency(self) -> None:
        cases = (
            ("irrelevant_flood", "HIGH", "LOW"),
            ("relevant_bushfire", "LOW", "HIGH"),
        )
        for name, proposed, expected in cases:
            with self.subTest(name=name):
                result = monitor_security_workflow(
                    make_warning_scenario(name), record_path=self.path,
                    proposal_provider=lambda _, level=proposed: {
                        "risk_level": level, "rationale": "model suggestion",
                    },
                )
                self.assertEqual(result.assessment.risk_level, expected)
                self.assertEqual(result.assessment.llm_status, "CONFLICT")
                self.assertTrue(result.assessment.policy_override)
                self.assertEqual(bool(result.workflow.action_results), expected == "HIGH")

    def test_invalid_model_output_and_timeout_keep_fixed_warning_rule(self) -> None:
        event = make_warning_scenario("relevant_bushfire")
        for provider, status in (
            (lambda _: {"risk_level": "UNKNOWN"}, "INVALID"),
            (lambda _: (_ for _ in ()).throw(TimeoutError()), "TIMEOUT"),
        ):
            with self.subTest(status=status):
                result = assess_external_warning(event, provider)
                self.assertEqual(result.risk_level, "HIGH")
                self.assertEqual(result.llm_status, status)
                self.assertTrue(result.fallback_used)

    def test_offline_emergency_mode_is_failed_and_owner_is_not_falsely_assured(self) -> None:
        result = monitor_security_workflow(
            make_warning_scenario("relevant_bushfire"), record_path=self.path,
            offline_devices=("emergency_mode",),
        )
        self.assertEqual(result.workflow.outcome, "FAILED")
        self.assertFalse(result.workflow.action_results[0].success)
        self.assertEqual([item["purpose"] for item in result.notification_history], ["response", "failed_action"])
        record = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(record["workflow"]["outcome"], "FAILED")
        self.assertFalse(record["workflow"]["action_results"][0]["verified"])

    def test_notification_failure_does_not_claim_complete_response(self) -> None:
        class BrokenNotifier:
            def send(self, request):
                raise TimeoutError("fictional notification outage")

        result = monitor_security_workflow(
            make_warning_scenario("relevant_bushfire"), record_path=self.path,
            notifier=BrokenNotifier(),
        )
        self.assertTrue(result.workflow.action_results[0].success)
        self.assertEqual(result.workflow.notification_result.status, "FAILED")
        self.assertEqual(result.workflow.outcome, "PARTIAL")
        record = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(record["notifications"][0]["status"], "FAILED")
        self.assertEqual(record["workflow"]["outcome"], "PARTIAL")

    def test_campus_warning_prompt_uses_existing_proxy_and_allowlisted_fields(self) -> None:
        event = make_warning_scenario("relevant_bushfire")
        event = replace(event, context={**event.context, "private_address": "not-for-model"})
        reply = {"choices": [{"message": {"content": json.dumps({
            "risk_level": "HIGH", "rationale": "Fictional bushfire emergency affects the home area."
        })}}]}
        config = CampusProxyConfig(api_key="test-only-key")
        with patch("services.campus_proxy.urlopen", return_value=BytesIO(json.dumps(reply).encode())) as send:
            result = monitor_security_workflow(
                event, record_path=self.path,
                proposal_provider=lambda observation: propose_external_warning_risk(observation, config),
            )
        request = send.call_args.args[0]
        body = json.loads(request.data)
        self.assertIn("BUSHFIRE", json.dumps(body))
        self.assertNotIn("not-for-model", json.dumps(body))
        self.assertNotIn("test-only-key", json.dumps(body))
        self.assertNotIn(event.context["warning"]["warning_id"], json.dumps(body))
        self.assertEqual(result.assessment.llm_status, "ACCEPTED")
        self.assertTrue(result.workflow.action_results[0].success)


if __name__ == "__main__":
    unittest.main()
