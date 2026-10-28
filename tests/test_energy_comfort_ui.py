"""Streamlit integration checks for the Energy & Comfort assessment page."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import ui.domain_views as domain_views
import ui.energy_comfort as energy_ui


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class EnergyComfortPageTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.addCleanup(temporary.cleanup)
        self.record_path = Path(temporary.name) / "energy_comfort.jsonl"
        record_patch = patch.object(energy_ui, "DEFAULT_RECORD_PATH", self.record_path)
        record_patch.start()
        self.addCleanup(record_patch.stop)
        self.app = AppTest.from_file(str(APP_PATH), default_timeout=120)

    def open_page(self) -> None:
        self.app.run()
        self.app.sidebar.radio[0].set_value("Energy & Comfort").run()
        self.assertEqual(list(self.app.exception), [])

    def records(self) -> list[dict]:
        return [json.loads(line) for line in self.record_path.read_text(encoding="utf-8").splitlines()]

    def test_page_is_registered_not_pending(self) -> None:
        self.open_page()
        self.assertIn("Energy & Comfort", domain_views.DOMAIN_VIEWS)
        text = "\n".join(item.value for item in self.app.markdown)
        self.assertIn("Energy & Comfort", text)
        self.assertNotIn(
            "not available in this version",
            "\n".join(item.value for item in self.app.info),
        )

    def test_comfort_ok_runs_assessment_only_without_dispatch(self) -> None:
        self.open_page()
        self.app.button(key="run-energy-assessment").click().run()
        self.assertEqual(list(self.app.exception), [])
        saved = self.app.session_state["energy_result"]
        self.assertEqual(saved["assessment"].decision, "NO_ADJUSTMENT")
        self.assertEqual(saved["workflow"].outcome, "ASSESSED")
        self.assertEqual(saved["workflow"].action_results, ())
        self.assertEqual(saved["explanation"].execution_status, "NOT_EXECUTED")
        self.assertFalse(saved["eligibility"].eligible)
        self.assertEqual(saved["scope"]["assessment"], "ASSESSMENT_ONLY")
        self.assertEqual(saved["scope"]["formal_energy_comfort_control"], "PENDING")
        self.assertFalse(saved["readiness"].ready)
        self.assertEqual(saved["action_requests_created"], 0)
        self.assertFalse(saved["dispatched"])
        record = self.records()[-1]
        self.assertEqual(record["assessment"]["decision"], "NO_ADJUSTMENT")
        self.assertEqual(record["workflow"]["outcome"], "ASSESSED")
        self.assertEqual(record["workflow"]["action_results"], [])
        self.assertFalse(record["eligibility"]["eligible"])
        self.assertFalse(record["formal_control"]["ready"])
        self.assertEqual(record["formal_control"]["action_requests_created"], 0)

    def test_edit_clears_stale_result_and_unoccupied_needs_adjustment(self) -> None:
        self.open_page()
        self.app.button(key="run-energy-assessment").click().run()
        self.assertEqual(self.app.session_state["energy_result"]["assessment"].decision, "NO_ADJUSTMENT")
        self.app.selectbox(key="energy_scenario").set_value("Unoccupied high power").run()
        self.assertNotIn("energy_result", self.app.session_state)
        self.app.button(key="run-energy-assessment").click().run()
        saved = self.app.session_state["energy_result"]
        self.assertEqual(saved["assessment"].decision, "ADJUSTMENT_NEEDED")
        self.assertEqual(saved["workflow"].outcome, "ASSESSED")
        self.assertEqual(saved["explanation"].execution_status, "NOT_EXECUTED")
        self.assertEqual(saved["scope"]["formal_energy_comfort_control"], "PENDING")
        self.assertEqual(saved["workflow"].action_results, ())
        self.assertEqual(self.records()[-1]["assessment"]["decision"], "ADJUSTMENT_NEEDED")

    def test_eligibility_demo_still_reports_not_executed(self) -> None:
        self.open_page()
        self.app.selectbox(key="energy_scenario").set_value("Unoccupied high power").run()
        self.app.checkbox(key="energy_shutdown_basis").set_value(True).run()
        self.app.checkbox(key="energy_control_authorized").set_value(True).run()
        self.app.text_input(key="energy_auth_source").set_value("fictional-team-source").run()
        self.app.checkbox(key="energy_trust_source").set_value(True).run()
        self.app.selectbox(key="energy_safety_passed").set_value("Passed").run()
        self.app.button(key="run-energy-assessment").click().run()
        self.assertEqual(list(self.app.exception), [])
        saved = self.app.session_state["energy_result"]
        self.assertTrue(saved["eligibility"].eligible)
        self.assertEqual(saved["explanation"].execution_status, "NOT_EXECUTED")
        self.assertEqual(saved["explanation"].safety_status, "ELIGIBLE_FOR_LATER_PLANNING")
        self.assertEqual(saved["workflow"].action_results, ())
        self.assertEqual(saved["scope"]["formal_energy_comfort_control"], "PENDING")
        self.assertFalse(saved["readiness"].ready)
        self.assertIn("m2_observation_to_control_mapping_unapproved", saved["readiness"].blockers)
        self.assertEqual(saved["action_requests_created"], 0)
        record = self.records()[-1]
        self.assertTrue(record["eligibility"]["eligible"])
        self.assertEqual(record["explanation"]["execution_status"], "NOT_EXECUTED")
        self.assertEqual(record["scope"]["formal_energy_comfort_control"], "PENDING")
        self.assertFalse(record["formal_control"]["ready"])
        self.assertEqual(record["formal_control"]["action_requests_created"], 0)
