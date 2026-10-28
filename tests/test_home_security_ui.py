"""Unified Home Security page runs and resumes actual shared-graph results."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import ui.home_security as security_ui


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class HomeSecurityPageTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.record_path = Path(temporary.name) / "security.jsonl"
        path_patch = patch.object(security_ui, "DEFAULT_RECORD_PATH", self.record_path)
        path_patch.start()
        self.addCleanup(path_patch.stop)
        environment_patch = patch.dict(os.environ, {"ELEC5620_API_KEY": ""})
        environment_patch.start()
        self.addCleanup(environment_patch.stop)
        # A cold Windows import of Streamlit's dataframe dependencies can exceed 45 seconds.
        self.app = AppTest.from_file(str(APP_PATH), default_timeout=120)
        self.app.run()
        self.app.sidebar.radio[0].set_value("Home Security").run()
        self.assertEqual(list(self.app.exception), [])

    def test_smoke_preset_runs_shared_graph_and_saves_actual_result(self) -> None:
        self.app.selectbox(key="security_scenario").set_value("smoke").run()
        self.assertTrue(self.app.checkbox(key="security_smoke_alarm").value)
        self.app.button(key="security_run").click().run()
        self.assertEqual(list(self.app.exception), [])
        result = self.app.session_state["security_result"]
        self.assertEqual(result.assessment.risk_level, "HIGH")
        self.assertEqual(result.workflow.outcome, "COMPLETE")
        self.assertEqual(result.workflow.notification_result.status, "SIMULATED")
        self.assertTrue(all(item.success for item in result.workflow.action_results))
        record = json.loads(self.record_path.read_text(encoding="utf-8"))
        self.assertEqual(record["assessment"]["risk_level"], "HIGH")
        self.assertEqual(record["assessment"]["llm_status"], "NOT_REQUESTED")

    def test_edit_clears_stale_result_and_unconfigured_llm_cannot_run(self) -> None:
        self.app.button(key="security_run").click().run()
        self.assertEqual(self.app.session_state["security_result"].assessment.risk_level, "LOW")
        self.app.checkbox(key="security_gas_alarm").set_value(True).run()
        self.assertNotIn("security_result", self.app.session_state)
        self.app.button(key="security_run").click().run()
        self.assertEqual(self.app.session_state["security_result"].assessment.risk_level, "HIGH")
        self.app.toggle(key="security_use_ai").set_value(True).run()
        self.assertTrue(self.app.button(key="security_run").disabled)
        self.assertNotIn("security_result", self.app.session_state)

    def test_appliance_overheat_preset_runs_and_records_high_risk(self) -> None:
        self.app.selectbox(key="security_scenario").set_value("appliance_overheat").run()
        self.assertTrue(self.app.checkbox(key="security_appliance_overheat_alarm").value)
        self.app.button(key="security_run").click().run()
        self.assertEqual(list(self.app.exception), [])
        self.assertEqual(self.app.session_state["security_result"].assessment.risk_level, "HIGH")
        record = json.loads(self.record_path.read_text(encoding="utf-8"))
        self.assertEqual(record["assessment"]["risk_level"], "HIGH")
        self.assertIn("appliance_overheat_alarm", record["assessment"]["evidence"])

    def test_medium_door_approval_resumes_the_same_workflow(self) -> None:
        self.app.selectbox(key="security_scenario").set_value("unusual_door").run()
        self.app.button(key="security_run").click().run()
        first = self.app.session_state["security_result"]
        self.assertEqual(first.workflow.outcome, "AWAITING_CONFIRMATION")
        event_id = first.workflow.event.event_id
        self.app.button(key="security_approve").click().run()
        self.assertEqual(list(self.app.exception), [])
        approved = self.app.session_state["security_result"]
        self.assertEqual(approved.workflow.event.event_id, event_id)
        self.assertEqual(approved.workflow.outcome, "COMPLETE")
        self.assertEqual(approved.workflow.confirmation_replies[-1].verdict, "help")
        self.assertIn("Confirmation: approved", [item.value for item in self.app.markdown])
        displayed = security_ui._display_workflow(approved.workflow)
        self.assertEqual(displayed["confirmation_replies"][-1]["verdict"], "approved")
        self.assertEqual(json.loads(self.app.json[0].value)["confirmation_replies"][-1]["verdict"], "approved")
        self.assertIn("Homeowner confirmation: approved.", displayed["assessment"]["rationale"])
        self.assertIn("resident_reply:approved", [item["outcome"] for item in displayed["trace"]])
        self.assertTrue(all(item.success for item in approved.workflow.action_results))
        self.assertEqual(len(self.record_path.read_text(encoding="utf-8").splitlines()), 2)

    def test_medium_door_rejection_displays_rejected_without_actions(self) -> None:
        self.app.selectbox(key="security_scenario").set_value("unusual_door").run()
        self.app.button(key="security_run").click().run()
        self.app.button(key="security_reject").click().run()
        self.assertEqual(list(self.app.exception), [])
        result = self.app.session_state["security_result"]
        self.assertEqual(result.workflow.confirmation_replies[-1].verdict, "safe")
        self.assertIn("Confirmation: rejected", [item.value for item in self.app.markdown])
        displayed = security_ui._display_workflow(result.workflow)
        self.assertEqual(displayed["confirmation_replies"][-1]["verdict"], "rejected")
        self.assertEqual(json.loads(self.app.json[0].value)["confirmation_replies"][-1]["verdict"], "rejected")
        self.assertIn("resident_reply:rejected", [item["outcome"] for item in displayed["trace"]])
        self.assertEqual(result.workflow.action_results, ())

    def test_timeout_records_no_unauthorised_device_action(self) -> None:
        self.app.selectbox(key="security_scenario").set_value("unusual_door").run()
        self.app.button(key="security_run").click().run()
        self.app.button(key="security_timeout").click().run()
        self.assertEqual(list(self.app.exception), [])
        result = self.app.session_state["security_result"]
        self.assertEqual(result.workflow.confirmation_replies[-1].verdict, "timeout")
        self.assertIn("Confirmation: timeout", [item.value for item in self.app.markdown])
        self.assertEqual(result.workflow.action_results, ())

    def test_failed_confirmation_notice_is_explicit_without_authorizing_actions(self) -> None:
        class BrokenNotifier:
            def send(self, request):
                raise TimeoutError("fictional notification outage")

        real_workflow = security_ui.monitor_security_workflow

        def with_failed_notice(event, **kwargs):
            return real_workflow(event, notifier=BrokenNotifier(), **kwargs)

        self.app.selectbox(key="security_scenario").set_value("unusual_door").run()
        with patch.object(security_ui, "monitor_security_workflow", side_effect=with_failed_notice):
            self.app.button(key="security_run").click().run()

        self.assertEqual(list(self.app.exception), [])
        result = self.app.session_state["security_result"]
        self.assertEqual(result.workflow.outcome, "AWAITING_CONFIRMATION")
        self.assertEqual(result.workflow.notification_result.status, "FAILED")
        self.assertEqual(result.device_tool.dispatch_count, 0)
        self.assertIn(
            "Workflow outcome: **AWAITING_CONFIRMATION (confirmation notification FAILED)**",
            [item.value for item in self.app.markdown],
        )
        self.assertIn(
            "No homeowner delivery is confirmed",
            "\n".join(item.value for item in self.app.error),
        )
        record = json.loads(self.record_path.read_text(encoding="utf-8"))
        self.assertEqual(record["workflow"]["outcome"], "AWAITING_CONFIRMATION")
        self.assertEqual(record["workflow"]["notification_result"]["status"], "FAILED")
        self.assertEqual(record["notifications"][0]["status"], "FAILED")

    def test_device_failure_preset_is_reported_as_failed(self) -> None:
        self.app.selectbox(key="security_scenario").set_value("device_failure").run()
        self.assertTrue(self.app.checkbox(key="security_failure").value)
        self.app.button(key="security_run").click().run()
        self.assertEqual(list(self.app.exception), [])
        result = self.app.session_state["security_result"]
        self.assertEqual(result.workflow.outcome, "FAILED")
        self.assertTrue(all(not item.success for item in result.workflow.action_results))

    def test_external_warning_area_shows_relevant_irrelevant_and_invalid_results(self) -> None:
        selector = self.app.selectbox(key="security_warning_scenario")
        self.assertTrue(all("SIMULATED" not in option for option in selector.options))
        self.assertIn("External Warning · SIMULATED", [item.value for item in self.app.subheader])
        cases = (
            ("relevant_bushfire", True, True, "HIGH", "COMPLETE", 1, 1),
            ("irrelevant_flood", True, False, "LOW", "ASSESSED", 0, 0),
            ("invalid_source", False, False, "LOW", "ASSESSED", 0, 0),
        )
        for name, valid, relevant, risk, outcome, actions, notices in cases:
            with self.subTest(name=name):
                self.app.selectbox(key="security_warning_scenario").set_value(name).run()
                self.app.button(key="security_warning_run").click().run()
                self.assertEqual(list(self.app.exception), [])
                self.assertIn("Warning details and audit trace", [item.label for item in self.app.expander])
                result = self.app.session_state["security_warning_result"]
                self.assertEqual(result.assessment.valid, valid)
                self.assertEqual(result.assessment.relevant, relevant)
                self.assertEqual(result.assessment.risk_level, risk)
                self.assertEqual(result.workflow.outcome, outcome)
                self.assertEqual(len(result.workflow.action_results), actions)
                self.assertEqual(len(result.notification_history), notices)
                self.assertIn("SIMULATED", result.assessment.rationale)
                visible_rationale = security_ui._warning_text(result.assessment.rationale)
                self.assertIn(visible_rationale, [item.value for item in self.app.markdown])
                self.assertNotIn("SIMULATED", visible_rationale)
                self.assertNotIn("SIMULATED", security_ui._display_workflow(result.workflow)["assessment"]["rationale"])
                if notices:
                    self.assertEqual(self.app.dataframe[0].value.iloc[0]["status"], "Recorded locally")
                    self.assertEqual(result.notification_history[0]["status"], "SIMULATED")
        records = [json.loads(line) for line in self.record_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(records), len(cases))
        self.assertTrue(all(item["record_type"] == "external_warning_workflow" for item in records))
        self.assertTrue(all("SIMULATED" in item["assessment"]["rationale"] for item in records))
        self.assertTrue(all(item["event"]["raw_warning"]["simulated"] for item in records))
        self.assertTrue(all("SIMULATED" not in reason for reason in self.app.dataframe[-1].value["Reason"]))


if __name__ == "__main__":
    unittest.main()
