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

    def test_only_an_unambiguous_no_closes_the_event(self):
        # Examples from the PR #26 review: none of these may close the event.
        for reply in ("Not sure", "No idea", "Nothing makes sense", "No, I fell again", "No, I cannot stand up",
                      "No, wait", "no, where am I", "no... what happened", "No I don't know", "no no no"):
            self.assertNotEqual(evaluation.interpret_by_rules(2, reply), "safe", reply)
        self.assertEqual(evaluation.interpret_by_rules(2, "No, I cannot stand up"), "help")
        for reply in ("No", "nope", "no thanks", "No, I'm fine", "Not needed, my son is already here"):
            self.assertEqual(evaluation.interpret_by_rules(2, reply), "safe", reply)

    def test_only_complete_listed_replies_are_safe(self):
        # Second PR #26 review (Yang Yang, Jinjing Huang): a word whitelist accepted "I am down".
        for attempt, reply in ((1, "Okay, I am down"), (1, "I am fine, I am down"),
                               (2, "No, I am down"), (2, "No thanks, I am down")):
            self.assertEqual(evaluation.interpret_by_rules(attempt, reply), "unclear", reply)
        # Non-English content after a safe start is not readable by the rules, so never safe.
        self.assertEqual(evaluation.interpret_by_rules(1, "Okay, \u6211\u6454\u5012\u4e86\u8d77\u4e0d\u6765"), "unclear")
        self.assertEqual(evaluation.interpret_by_rules(2, "No, \u6211\u8d77\u4e0d\u6765"), "unclear")
        self.assertEqual(evaluation.interpret_by_rules(1, "I'm fine, I just sat down."), "safe")
        self.assertEqual(evaluation.interpret_by_rules(1, "I\u2019m fine!"), "safe")

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
