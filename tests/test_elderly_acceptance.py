"""Keeps the SCRUM-34 acceptance run green in the normal test suite.

The real evidence is the report produced by
`python -m simulation.elderly_acceptance`; this test only guarantees that
every acceptance case still passes and that the report/log are written.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from simulation import elderly_acceptance as acceptance


class ElderlyAcceptanceTests(unittest.TestCase):
    def test_every_acceptance_case_passes(self):
        cases = acceptance.run_cases()
        failing = {c.case_id: c.error or [label for label, ok in c.checks if not ok] for c in cases if not c.passed}
        self.assertEqual(failing, {})
        self.assertGreaterEqual(len(cases), 18)

    def test_required_paths_are_covered(self):
        titles = " ".join(title.lower() for _, title, *_ in acceptance.CASES)
        for path in ("safe reply", "help request", "no reply", "unclear", "caregiver timeout",
                     "fallback", "offline", "mismatch", "de-identified"):
            self.assertIn(path, titles)

    def test_report_and_log_are_written(self):
        folder = Path(tempfile.mkdtemp())
        code = acceptance.main(["--report", str(folder / "r.md"), "--log", str(folder / "l.json")])
        self.assertEqual(code, 0)
        report = (folder / "r.md").read_text(encoding="utf-8")
        self.assertIn("no real device was operated", report)
        self.assertIn("| AT-E01 |", report)
        log = json.loads((folder / "l.json").read_text(encoding="utf-8"))
        self.assertTrue(all(case["passed"] for case in log["cases"]))
        self.assertIn("git_commit", log["environment"])


if __name__ == "__main__":
    unittest.main()
