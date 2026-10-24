"""Streamlit integration checks for the Smart Home Control page."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import ui.smart_home_control as smart_home_ui


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class SmartHomeControlPageTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.addCleanup(temporary.cleanup)
        self.record_path = Path(temporary.name) / "smart_home.jsonl"
        record_patch = patch.object(smart_home_ui, "DEFAULT_RECORD_PATH", self.record_path)
        record_patch.start()
        self.addCleanup(record_patch.stop)
        environment_patch = patch.dict(os.environ, {"ELEC5620_API_KEY": ""})
        environment_patch.start()
        self.addCleanup(environment_patch.stop)
        self.app = AppTest.from_file(str(APP_PATH), default_timeout=45)

    def open_page(self) -> None:
        self.app.run()
        self.app.sidebar.radio[0].set_value("Smart Home Control").run()
        self.assertEqual(list(self.app.exception), [])

    def test_good_night_command_shows_four_verified_actions(self) -> None:
        self.open_page()
        self.app.button(key="run-smart-home-command").click().run()
        self.assertEqual(list(self.app.exception), [])
        result = self.app.session_state["smart_home_result"]["workflow"]
        self.assertEqual(result.outcome, "COMPLETE")
        self.assertEqual(len(result.action_results), 4)
        self.assertEqual(self.app.session_state["smart_home_mode_state"].current_mode, "NIGHT")
        record = json.loads(self.record_path.read_text(encoding="utf-8").strip())
        self.assertEqual(record["outcome"], "COMPLETE")

    def test_offline_air_conditioner_is_visible_as_partial(self) -> None:
        self.open_page()
        self.app.selectbox(key="smart_home_fault").set_value("Air conditioner offline").run()
        self.app.button(key="run-smart-home-command").click().run()
        result = self.app.session_state["smart_home_result"]["workflow"]
        self.assertEqual(result.outcome, "PARTIAL")
        self.assertIn("Some actions could not be completed", "\n".join(item.value for item in self.app.markdown))

    def test_sensitive_preset_requires_confirmation_then_executes(self) -> None:
        self.open_page()
        self.app.selectbox(key="smart_home_scenario").set_value("Sensitive action").run()
        self.app.button(key="run-smart-home-command").click().run()
        result = self.app.session_state["smart_home_result"]["workflow"]
        self.assertEqual(result.outcome, "AWAITING_CONFIRMATION")
        self.assertTrue(result.assessment.requires_human_review)
        self.assertTrue(self.app.session_state["smart_home_result"]["states"]["front-door-lock"]["locked"])
        self.app.button(key="approve-smart-home-sensitive").click().run()
        result = self.app.session_state["smart_home_result"]["workflow"]
        self.assertEqual(result.outcome, "COMPLETE")
        self.assertFalse(self.app.session_state["smart_home_result"]["states"]["front-door-lock"]["locked"])


if __name__ == "__main__":
    unittest.main()
