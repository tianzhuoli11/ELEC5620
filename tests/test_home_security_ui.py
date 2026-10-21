"""Home Security page uses actual editable inputs and saves graph results."""

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
        self.app = AppTest.from_file(str(APP_PATH), default_timeout=45)
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
        self.assertEqual(result.workflow.outcome, "ASSESSED")
        self.assertIsNone(result.workflow.notification_result)
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


if __name__ == "__main__":
    unittest.main()
