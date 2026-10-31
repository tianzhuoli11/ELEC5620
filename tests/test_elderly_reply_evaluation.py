"""Offline guard for the resident-reply evaluation (no model, no network)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from simulation import elderly_reply_evaluation as evaluation


class ElderlyReplyEvaluationTests(unittest.TestCase):
    def test_rules_never_close_a_labelled_help_reply(self):
        summary = evaluation.run(live=False)["summary"]["rules"]
        self.assertEqual(summary["help_closed_as_safe"], 0)
        self.assertEqual(summary["help_delayed_by_follow_up"], 0)

    def test_negative_answer_with_injury_escalates(self):
        self.assertEqual(evaluation.interpret_by_rules(2, "No, I can't move"), "help")
        self.assertEqual(evaluation.interpret_by_rules(1, "I'm not okay"), "help")
        self.assertEqual(evaluation.interpret_by_rules(2, "Not needed, my son is already here"), "safe")

    def test_report_is_written_without_a_key(self):
        folder = Path(tempfile.mkdtemp())
        code = evaluation.main(["--output", str(folder / "e.json"), "--report", str(folder / "e.md")])
        self.assertEqual(code, 0)
        self.assertIn("Rules only", (folder / "e.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
