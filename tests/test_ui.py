"""Exercise the resident-facing app without writing to its normal event log."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import streamlit as st
from streamlit.testing.v1 import AppTest

import ui.dashboard as dashboard
import ui.domain_views as domain_views
from domains.pet_care.records import monitor_pet_event
from simulation.events import make_sensor_event


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class HavenAppTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.record_path = Path(temporary.name) / "pet_events.jsonl"
        self.record_patch = patch.object(dashboard, "DEFAULT_RECORD_PATH", self.record_path)
        self.record_patch.start()
        self.addCleanup(self.record_patch.stop)
        environment_patch = patch.dict(os.environ, {"ELEC5620_API_KEY": ""})
        environment_patch.start()
        self.addCleanup(environment_patch.stop)
        # The first dataframe render may import Arrow/Pandas on a cold Windows run.
        self.app = AppTest.from_file(str(APP_PATH), default_timeout=45)

    def assert_app_ok(self) -> None:
        self.assertEqual(list(self.app.exception), [])

    def markdown(self) -> str:
        return "\n".join(element.value for element in self.app.markdown)

    def open_pet_care(self) -> None:
        self.app.run()
        self.app.sidebar.radio[0].set_value("Pet Care").run()
        self.assert_app_ok()

    def run_check(self) -> None:
        self.app.button(key="run-pet-check").click().run()
        self.assert_app_ok()

    def saved_records(self) -> list[dict]:
        return [json.loads(line) for line in self.record_path.read_text(encoding="utf-8").splitlines()]

    def test_overview_starts_without_coursework_or_project_status_text(self) -> None:
        self.app.run()
        self.assert_app_ok()
        text = self.markdown().lower()
        for unwanted in ("elec5620", "group 11", "project status", "domain integration", "awaiting integration", "home feels better, together", 'class="hero'):
            with self.subTest(text=unwanted):
                self.assertNotIn(unwanted, text)
        self.assertIn("run a pet check", text)
        self.assertIn("check result", text)
        self.assertEqual(self.app.selectbox(key="pet_scenario").value, "Food bowl")
        self.assertEqual(self.app.number_input(key="pet_value").value, 0.0)
        self.assertFalse(self.app.button(key="run-pet-check").disabled)
        self.assertFalse(self.record_path.exists())

    def test_sidebar_navigates_to_pet_care(self) -> None:
        self.open_pet_care()
        self.assertEqual(self.app.session_state["page"], "Pet Care")
        self.assertEqual(self.app.selectbox(key="pet_scenario").value, "Food bowl")
        self.assertIn("Run a pet check", self.markdown())

    def test_service_action_navigates_and_keeps_sidebar_in_sync(self) -> None:
        self.app.run()
        self.app.button(key="open-Pet Care").click().run()
        self.assert_app_ok()
        self.assertEqual(self.app.session_state["page"], "Pet Care")
        self.assertEqual(self.app.sidebar.radio[0].value, "Pet Care")
        self.assertEqual(self.app.selectbox(key="pet_scenario").value, "Food bowl")

    def test_standard_check_saves_actual_assessment_to_temporary_log(self) -> None:
        self.open_pet_care()
        self.assertFalse(self.app.toggle(key="pet_use_ai").value)
        self.run_check()
        records = self.saved_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["event"]["event_type"], "pet_bowl_level")
        self.assertEqual(records[0]["assessment"]["risk_level"], "MEDIUM")
        self.assertEqual(records[0]["workflow"]["notification_result"]["status"], "SIMULATED")
        self.assertEqual(self.app.session_state["pet_result"]["workflow"].notification_result.status, "SIMULATED")
        self.assertEqual(self.app.session_state["pet_result"]["observation"], "Food bowl")
        self.assertIn("Needs attention", self.markdown())
        self.assertIn("refill it as appropriate", self.markdown())

    def test_overview_uses_edited_reading_and_clears_result_when_input_changes(self) -> None:
        self.app.run()
        self.app.number_input(key="pet_value").set_value(45.0).run()
        self.run_check()
        result = self.app.session_state["pet_result"]
        self.assertEqual(result["assessment"].risk_level, "LOW")
        self.assertEqual(result["event"].readings[0].value, 45.0)
        self.assertEqual(self.saved_records()[0]["event"]["readings"][0]["value"], 45.0)

        self.app.number_input(key="pet_value").set_value(0.0).run()
        self.assert_app_ok()
        self.assertNotIn("pet_result", self.app.session_state)
        self.assertIn("Ready for a reading", self.markdown())
        self.assertEqual(len(self.saved_records()), 1)

        self.run_check()
        self.assertEqual(self.app.session_state["pet_result"]["assessment"].risk_level, "MEDIUM")
        records = self.saved_records()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[1]["event"]["readings"][0]["value"], 0.0)
        self.assertEqual(records[1]["assessment"]["risk_level"], "MEDIUM")

    def test_scenario_presets_replace_input_and_produce_actual_risks(self) -> None:
        self.app.run()
        self.app.selectbox(key="pet_scenario").set_value("Activity check").run()
        self.assertEqual(self.app.number_input(key="pet_value").value, 150.0)
        self.run_check()
        self.assertEqual(self.app.session_state["pet_result"]["assessment"].risk_level, "HIGH")
        self.assertIn("pet_result", self.app.session_state)

        self.app.selectbox(key="pet_scenario").set_value("Normal activity").run()
        self.assert_app_ok()
        self.assertNotIn("pet_result", self.app.session_state)
        self.assertEqual(self.app.number_input(key="pet_value").value, 5.0)
        self.assertEqual(len(self.saved_records()), 1)
        self.run_check()
        result = self.app.session_state["pet_result"]
        self.assertEqual(result["observation"], "Normal activity")
        self.assertEqual(result["assessment"].risk_level, "LOW")
        self.assertEqual(result["event"].readings[0].value, 5.0)
        self.assertEqual([record["assessment"]["risk_level"] for record in self.saved_records()], ["HIGH", "LOW"])

    def test_normal_history_filter_finds_older_record_beyond_recent_five(self) -> None:
        # Seed actual domain results: the only LOW reading predates six MEDIUMs.
        for value in [45.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0]:
            event = make_sensor_event("pet_bowl_level", "food_level_percent", value, "%")
            monitor_pet_event(event, record_path=self.record_path)
        self.app.run()
        self.app.radio(key="history_filter").set_value("Normal").run()
        self.assert_app_ok()
        self.assertEqual(len(self.app.dataframe), 1)
        history = self.app.dataframe[0].value
        self.assertEqual(history["Risk"].tolist(), ["LOW"])
        self.assertIn("45", history.iloc[0]["Reading"])
        self.assertEqual(len(self.saved_records()), 7)

    def test_reset_inputs_clears_current_result_and_preserves_saved_history(self) -> None:
        self.app.run()
        self.app.selectbox(key="pet_scenario").set_value("Activity check").run()
        self.run_check()
        saved_before = self.record_path.read_bytes()
        self.app.toggle(key="pet_use_ai").set_value(True).run()
        self.assertTrue(self.app.button(key="run-pet-check").disabled)
        reset = [button for button in self.app.button if button.label == "Reset inputs"]
        self.assertEqual(len(reset), 1)
        reset[0].click().run()
        self.assert_app_ok()
        self.assertEqual(self.app.selectbox(key="pet_scenario").value, "Food bowl")
        self.assertEqual(self.app.number_input(key="pet_value").value, 0.0)
        self.assertFalse(self.app.toggle(key="pet_use_ai").value)
        self.assertFalse(self.app.button(key="run-pet-check").disabled)
        self.assertNotIn("pet_result", self.app.session_state)
        self.assertEqual(self.record_path.read_bytes(), saved_before)

    def test_registered_domain_uses_only_its_renderer(self) -> None:
        def custom_view() -> None:
            st.markdown("Custom caregiver view")

        custom = Mock(side_effect=custom_view)
        other = Mock()
        with patch.dict(domain_views.DOMAIN_VIEWS, {"Elderly Safety": custom, "Home Security": other}), patch.object(domain_views, "render_pending") as pending:
            self.app.run()
            self.app.sidebar.radio[0].set_value("Elderly Safety").run()
            self.assert_app_ok()
            custom.assert_called_once_with()
            other.assert_not_called()
            pending.assert_not_called()
            self.assertIn("Custom caregiver view", self.markdown())
            self.assertFalse(self.record_path.exists())


if __name__ == "__main__":
    unittest.main()
