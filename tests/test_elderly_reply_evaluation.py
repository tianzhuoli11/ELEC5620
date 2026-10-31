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

    def test_reassuring_start_does_not_hide_a_problem(self):
        for reply in ("Okay, I can't breathe", "Ok but I hit my head", "Okay, there is blood"):
            self.assertEqual(evaluation.interpret_by_rules(1, reply), "help", reply)
        self.assertEqual(evaluation.interpret_by_rules(1, "Okay but I fell"), "unclear")
        self.assertEqual(evaluation.interpret_by_rules(1, "I'm fine, I just sat down."), "safe")

    def test_second_answer_no_is_a_whole_word_and_not_mixed(self):
        self.assertEqual(evaluation.interpret_by_rules(2, "Not sure"), "unclear")
        self.assertEqual(evaluation.interpret_by_rules(2, "No, please come"), "unclear")
        self.assertEqual(evaluation.interpret_by_rules(2, "no thanks"), "safe")

    def test_report_is_written_without_a_key(self):
        folder = Path(tempfile.mkdtemp())
        code = evaluation.main(["--output", str(folder / "e.json"), "--report", str(folder / "e.md")])
        self.assertEqual(code, 0)
        self.assertIn("Rules only", (folder / "e.md").read_text(encoding="utf-8"))

    def test_live_run_stops_when_the_model_cannot_be_called(self):
        def broken(_payload):
            raise TimeoutError("no route")
        with self.assertRaises(evaluation.ModelUnavailable):
            evaluation.preflight(broken)
        evaluation.preflight(lambda _payload: {"verdict": "safe", "rationale": "ok"})


if __name__ == "__main__":
    unittest.main()
