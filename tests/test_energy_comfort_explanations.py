"""Deterministic OR-05 explanation tests using fictional offline evidence."""

from __future__ import annotations

from dataclasses import replace
import unittest

from domains.energy_comfort.control_policy import LightShutdownEligibility
from domains.energy_comfort.explanations import explain_energy_comfort
from domains.energy_comfort.post_action import assess_post_action_environment
from domains.energy_comfort.integration import monitor_energy_comfort_workflow
from models import ActionResult
from simulation.energy_comfort_demo import example_contexts, make_energy_comfort_event


class EnergyComfortExplanationTests(unittest.TestCase):
    def outcome(self, name):
        return monitor_energy_comfort_workflow(
            make_energy_comfort_event(example_contexts()[name])
        )

    def test_three_decisions_are_explained_without_execution_claims(self) -> None:
        expected = {
            "no_adjustment": "NO_ADJUSTMENT",
            "adjustment_needed": "ADJUSTMENT_NEEDED",
            "insufficient_data": "INSUFFICIENT_DATA",
        }
        for name, decision in expected.items():
            with self.subTest(name=name):
                outcome = self.outcome(name)
                explanation = explain_energy_comfort(
                    outcome.assessment, workflow=outcome.workflow,
                )
                self.assertEqual(explanation.decision, decision)
                self.assertEqual(explanation.evidence_status, "CONSISTENT")
                self.assertEqual(explanation.execution_status, "NOT_EXECUTED")
                self.assertIn("UNKNOWN_NOT_MEASURED", explanation.environment_effect)

    def test_missing_workflow_evidence_remains_unknown(self) -> None:
        outcome = self.outcome("adjustment_needed")
        explanation = explain_energy_comfort(outcome.assessment)
        self.assertEqual(explanation.evidence_status, "MISSING")
        self.assertEqual(explanation.execution_status, "UNKNOWN")
        self.assertIn("not supplied", explanation.execution_detail)

    def test_conflicting_workflow_evidence_is_not_used(self) -> None:
        assessment = self.outcome("adjustment_needed").assessment
        other_workflow = self.outcome("no_adjustment").workflow
        explanation = explain_energy_comfort(assessment, workflow=other_workflow)
        self.assertEqual(explanation.evidence_status, "CONFLICTING")
        self.assertEqual(explanation.execution_status, "UNKNOWN")

    def test_safety_conflict_explains_priority_without_execution_claim(self) -> None:
        outcome = self.outcome("adjustment_needed")
        eligibility = LightShutdownEligibility(
            False, "observed-light", ("conflicting_safety_conditions",),
            ("assessment=ADJUSTMENT_NEEDED",),
        )
        explanation = explain_energy_comfort(
            outcome.assessment, workflow=outcome.workflow, eligibility=eligibility,
        )
        self.assertEqual(explanation.safety_status, "BLOCKED_BY_SAFETY")
        self.assertEqual(explanation.execution_status, "NOT_EXECUTED")

    def test_supplied_verified_result_is_described_but_effect_remains_unknown(self) -> None:
        outcome = self.outcome("adjustment_needed")
        result = ActionResult(
            outcome.assessment.event_id, "fictional-light", "set_state",
            accepted=True, verified=True, returned_state={"power": "off"},
        )
        workflow = replace(
            outcome.workflow, action_result=result, action_results=(result,),
        )
        explanation = explain_energy_comfort(
            outcome.assessment, workflow=workflow,
        )
        self.assertEqual(explanation.execution_status, "VERIFIED")
        self.assertIn("UNKNOWN_NOT_MEASURED", explanation.environment_effect)

    def test_post_action_observation_overrides_environment_effect(self) -> None:
        outcome = self.outcome("adjustment_needed")
        post = assess_post_action_environment(workflow=outcome.workflow, planned_actions=0)
        explanation = explain_energy_comfort(
            outcome.assessment, workflow=outcome.workflow, post_action_environment=post,
        )
        self.assertIn("not_applicable_no_device_execution", explanation.environment_effect)


if __name__ == "__main__":
    unittest.main()
