"""SCRUM-38 repeatable acceptance-evidence checks for implemented UC-05 scope."""

from __future__ import annotations

import unittest

from simulation.energy_comfort_acceptance import run_uc05_acceptance_evidence


class EnergyComfortAcceptanceEvidenceTests(unittest.TestCase):
    def test_all_implemented_cases_pass_with_zero_device_side_effects(self) -> None:
        evidence = run_uc05_acceptance_evidence()
        self.assertEqual(evidence["summary"], {"passed": 10, "failed": 0})
        self.assertTrue(evidence["pending"])
        for case in evidence["cases"]:
            with self.subTest(case=case["case_id"]):
                self.assertEqual(case["test_result"], "PASS")
                self.assertEqual(case["actual"]["dispatch_calls"], 0)
                self.assertEqual(case["actual"]["read_calls"], 0)

    def test_evidence_contains_required_decisions_traces_and_explanations(self) -> None:
        evidence = run_uc05_acceptance_evidence()
        by_id = {case["case_id"]: case for case in evidence["cases"]}
        decisions = {
            case["decision"]["decision"]
            for case in evidence["cases"] if case["decision"] is not None
        }
        self.assertEqual(decisions, {
            "NO_ADJUSTMENT", "ADJUSTMENT_NEEDED", "INSUFFICIENT_DATA",
        })
        self.assertTrue(by_id["no_adjustment"]["trace"])
        self.assertIsNone(by_id["invalid_temperature_unit"]["decision"])
        self.assertEqual(
            by_id["safety_conflict_denied"]["explanation"]["safety_status"],
            "BLOCKED_BY_SAFETY",
        )
        self.assertEqual(
            by_id["trusted_eligibility_non_executable"]["explanation"]["execution_status"],
            "NOT_EXECUTED",
        )


if __name__ == "__main__":
    unittest.main()
