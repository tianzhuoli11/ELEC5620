import unittest
from simulation.ai_evaluation import run


class EvaluationEvidenceTests(unittest.TestCase):
    def test_injected_failures_recover_and_never_lower_high_policy_risk(self):
        report = run()
        self.assertFalse(report['live'])
        high = [r for r in report['cases'] if r['policy_reference_or_curated_intent'] == 'HIGH']
        self.assertTrue(high)
        self.assertTrue(all(r['final'] == 'HIGH' for r in high))
        self.assertTrue(any(c.get('error_type') == 'TimeoutError' for r in report['cases'] for c in r['calls']))
        self.assertTrue(all(r['fallback_used'] for r in report['cases'] if r['calls']))

    def test_negation_evidence_records_provider_bypass_not_network_success(self):
        rows = [r for r in run()['cases'] if r['scenario'] == 'Do not turn off the bedroom light']
        self.assertTrue(rows)
        self.assertTrue(all(r['calls'] == [] and r['final'] == 'clarify' for r in rows))
