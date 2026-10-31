"""Regression guard for the SCRUM-35 Smart Home acceptance evidence."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from simulation import smart_home_acceptance as acceptance


class SmartHomeAcceptanceTests(unittest.TestCase):
    def test_every_acceptance_case_passes(self):
        cases = acceptance.run_cases()
        failing = {
            case.case_id: case.error or [label for label, ok in case.checks if not ok]
            for case in cases if not case.passed
        }
        self.assertEqual(failing, {})
        self.assertGreaterEqual(len(cases), 10)

    def test_scrum35_required_paths_are_covered(self):
        titles = " ".join(title.lower() for _, title, *_ in acceptance.CASES)
        for path in ("sleep", "away", "conflicting", "unsupported", "waits", "denied", "approved", "offline", "mismatch", "ai proposal"):
            self.assertIn(path, titles)

    def test_report_and_log_are_written(self):
        folder = Path(tempfile.mkdtemp())
        report_path = folder / "report.md"
        log_path = folder / "log.json"
        code = acceptance.main(["--report", str(report_path), "--log", str(log_path), "--quiet"])
        self.assertEqual(code, 0)
        report = report_path.read_text(encoding="utf-8")
        self.assertIn("10 / 10 passed", report)
        self.assertIn("no physical home device was operated", report)
        self.assertIn("not evidence that the group coordination work", report)
        data = json.loads(log_path.read_text(encoding="utf-8"))
        self.assertTrue(all(case["passed"] for case in data["cases"]))
        self.assertIn("git_commit", data["environment"])


if __name__ == "__main__":
    unittest.main()
