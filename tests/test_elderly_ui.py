"""Streamlit integration checks for the Elderly Safety page (requires streamlit)."""

from __future__ import annotations

import json
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import ui.elderly_safety as elderly_ui


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class ElderlySafetyPageTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.addCleanup(temporary.cleanup)
        self.record_path = Path(temporary.name) / "elderly.jsonl"
        record_patch = patch.object(elderly_ui, "DEFAULT_RECORD_PATH", self.record_path)
        record_patch.start()
        self.addCleanup(record_patch.stop)
        environment_patch = patch.dict(os.environ, {"ELEC5620_API_KEY": ""})
        environment_patch.start()
        self.addCleanup(environment_patch.stop)
        self.app = AppTest.from_file(str(APP_PATH), default_timeout=45)

    def open_page(self) -> None:
        self.app.run()
        self.app.sidebar.radio[0].set_value("Elderly Safety").run()
        self.assertEqual(list(self.app.exception), [])

    def run_scenario(self, label: str, fault: str = "No simulated fault"):
        self.open_page()
        self.app.selectbox(key="elderly_scenario").set_value(label).run()
        self.app.selectbox(key="elderly_fault").set_value(fault).run()
        self.app.button(key="run-elderly-scenario").click().run()
        self.assertEqual(list(self.app.exception), [])
        return self.app.session_state["elderly_result"]["workflow"]

    def records(self) -> list[dict]:
        return [json.loads(line) for line in self.record_path.read_text(encoding="utf-8").splitlines()]

    def workflow_records(self) -> list[dict]:
        """Only the shared-workflow records; escalation steps are logged separately."""
        return [r for r in self.records() if r["record_type"] == "elderly_safety"]

    def test_page_is_registered_not_pending(self) -> None:
        self.open_page()
        text = "\n".join(item.value for item in self.app.markdown)
        self.assertIn("Elderly Safety", text)
        self.assertNotIn("not available in this version", "\n".join(item.value for item in self.app.info))

    def test_high_fall_alerts_and_lights_room(self) -> None:
        result = self.run_scenario("Fall, still on the floor (90 s)")
        self.assertEqual(result.outcome, "COMPLETE")
        self.assertTrue(result.action_results[0].success)
        self.assertEqual(self.app.session_state["elderly_result"]["device_tool"].states["bathroom_light"]["power"], "on")
        self.assertEqual(self.workflow_records()[-1]["workflow"]["outcome"], "COMPLETE")
        self.assertEqual(self.records()[-1]["record_type"], "elderly_escalation")

    def test_medium_fall_asks_then_safe_reply_closes(self) -> None:
        result = self.run_scenario("Fall, then not moving (30 s)")
        self.assertEqual(result.outcome, "AWAITING_CONFIRMATION")
        self.assertIn("Are you okay?", "\n".join(item.value for item in self.app.warning))
        self.app.button(key="quick-I'm fine").click().run()
        result = self.app.session_state["elderly_result"]["workflow"]
        self.assertEqual(result.outcome, "ASSESSED")
        self.assertEqual(result.confirmation_replies[0].verdict, "safe")
        self.assertEqual([r["workflow"]["outcome"] for r in self.workflow_records()], ["AWAITING_CONFIRMATION", "ASSESSED"])

    def test_typed_help_reply_escalates(self) -> None:
        self.run_scenario("Fall, then not moving (30 s)")
        self.app.text_input(key="elderly_reply").set_value("help me please").run()
        self.app.button(key="send-elderly-reply").click().run()
        result = self.app.session_state["elderly_result"]["workflow"]
        self.assertEqual(result.outcome, "COMPLETE")
        self.assertEqual(result.assessment.risk_level, "HIGH")

    def test_unclear_then_timeout_escalates(self) -> None:
        self.run_scenario("Fall, then not moving (30 s)")
        self.app.button(key="quick-Unclear").click().run()
        result = self.app.session_state["elderly_result"]["workflow"]
        self.assertEqual(result.pending_confirmation.attempt, 2)
        self.assertIn("contact your family", "\n".join(item.value for item in self.app.warning))
        self.app.button(key="elderly-timeout").click().run()
        result = self.app.session_state["elderly_result"]["workflow"]
        self.assertEqual([r.verdict for r in result.confirmation_replies], ["unclear", "timeout"])
        self.assertEqual(result.outcome, "COMPLETE")

    def test_offline_lights_are_reported_failed(self) -> None:
        result = self.run_scenario("Fall, still on the floor (90 s)", "All room lights offline")
        self.assertEqual(result.outcome, "FAILED")
        self.assertFalse(result.action_results[0].accepted)


    def test_escalation_ack_after_one_timeout(self) -> None:
        self.run_scenario("Fall, still on the floor (90 s)")
        state = self.app.session_state["elderly_result"]["escalation"]
        self.assertEqual(state.status, "AWAITING_ACK")
        self.app.button(key="elderly-ack-timeout").click().run()
        state = self.app.session_state["elderly_result"]["escalation"]
        self.assertEqual((state.status, state.current.role), ("AWAITING_ACK", "secondary contact"))
        self.app.button(key="elderly-ack").click().run()
        self.assertEqual(list(self.app.exception), [])
        self.assertEqual(self.app.session_state["elderly_result"]["escalation"].status, "RESOLVED")

    def test_escalation_failure_then_operator_closes(self) -> None:
        self.run_scenario("Fall, still on the floor (90 s)")
        self.app.button(key="elderly-ack-timeout").click().run()
        self.app.button(key="elderly-ack-timeout").click().run()
        state = self.app.session_state["elderly_result"]["escalation"]
        self.assertEqual(state.status, "ESCALATION_FAILED")
        self.assertIn("Human Operator informed", "\n".join(item.value for item in self.app.error))
        self.app.text_input(key="elderly_operator_note").set_value("phoned resident").run()
        self.app.button(key="elderly-operator-close").click().run()
        self.assertEqual(list(self.app.exception), [])
        state = self.app.session_state["elderly_result"]["escalation"]
        self.assertEqual(state.status, "CLOSED_BY_OPERATOR")
        statuses = [r["escalation"]["status"] for r in self.records() if r["record_type"] == "elderly_escalation"]
        self.assertEqual(statuses, ["AWAITING_ACK", "AWAITING_ACK", "ESCALATION_FAILED", "CLOSED_BY_OPERATOR"])

    def test_safe_reply_has_no_escalation_panel(self) -> None:
        self.run_scenario("Fall, then not moving (30 s)")
        self.app.button(key="quick-I'm fine").click().run()
        self.assertIsNone(self.app.session_state["elderly_result"]["escalation"])


    def test_ai_requested_without_key_falls_back_and_says_so(self) -> None:
        self.open_page()
        self.app.toggle(key="elderly_use_ai").set_value(True).run()
        self.app.button(key="run-elderly-scenario").click().run()
        self.assertEqual(list(self.app.exception), [])
        saved = self.app.session_state["elderly_result"]
        self.assertTrue(saved["requested_ai"])
        self.assertFalse(saved["ai_configured"])
        self.assertEqual(saved["handler"].fall_assessment.evidence_source, "llm_fallback")
        self.assertIn("no key was available", "\n".join(item.value for item in self.app.info))


if __name__ == "__main__":
    unittest.main()
