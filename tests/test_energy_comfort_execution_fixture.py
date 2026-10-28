"""Test-only SCRUM-32 execution prevalidation without domain action generation."""

from __future__ import annotations

import unittest

from simulation.energy_comfort_execution_fixture import run_test_only_execution_cases


class EnergyComfortExecutionFixtureTests(unittest.TestCase):
    def test_uncovered_execution_failures_are_explicit_and_state_safe(self) -> None:
        cases = run_test_only_execution_cases()
        self.assertEqual(len(cases), 2)
        for case in cases:
            with self.subTest(case=case["case_id"]):
                self.assertEqual(case["scope"], "TEST_ONLY_SIMULATION")
                self.assertEqual(case["test_result"], "PASS")
                self.assertFalse(case["actual"]["accepted"])
                self.assertFalse(case["actual"]["verified"])
                self.assertTrue(case["actual"]["state_unchanged"])


if __name__ == "__main__":
    unittest.main()
