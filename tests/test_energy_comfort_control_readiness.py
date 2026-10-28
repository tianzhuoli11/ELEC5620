"""SCRUM-32 formal-control readiness stays PENDING without team contracts."""

from __future__ import annotations

import unittest

from domains.energy_comfort.control_policy import (
    EXPLICIT_LIGHT_SHUTDOWN_BASIS,
    LightShutdownPolicyInput,
)
from domains.energy_comfort.control_readiness import (
    ACTIVE_FORMAL_CONTROL_CONTRACT,
    CANDIDATE_M2_LIGHT_ID,
    FormalControlContractStatus,
    PROTECTED_DEVICE_IDS,
    assess_formal_control_readiness,
)
from domains.energy_comfort.integration import (
    evaluate_formal_control_attempt,
    evaluate_light_shutdown_candidate,
)
from models import DeviceObservation, EnergyProfile, HomeContext, HomeEnvironment
from simulation.energy_comfort_demo import make_energy_comfort_event
from simulation.devices import SimulatedDeviceTool


def _unoccupied_event():
    context = HomeContext(
        HomeEnvironment(None, False),
        preference=None,
        energy=EnergyProfile(900.0, 400.0),
        devices=(DeviceObservation("observed-light", True, {"power": "on"}),),
        simulated=True,
    )
    return make_energy_comfort_event(context)


class FormalControlReadinessTests(unittest.TestCase):
    def test_active_contract_gates_are_all_false(self) -> None:
        contract = ACTIVE_FORMAL_CONTROL_CONTRACT
        self.assertFalse(contract.m2_observation_to_control_mapping_approved)
        self.assertFalse(contract.m2_command_and_expected_state_schema_approved)
        self.assertFalse(contract.m2_executable_authorization_source_approved)
        self.assertFalse(contract.m4_safety_conflict_feed_approved)
        self.assertIsNone(contract.approved_control_device_id)
        self.assertIsNone(contract.approved_authorization_source)

    def test_protected_devices_include_elderly_and_security_targets(self) -> None:
        self.assertIn("bathroom_light", PROTECTED_DEVICE_IDS)
        self.assertIn("security_lights", PROTECTED_DEVICE_IDS)
        self.assertIn("siren", PROTECTED_DEVICE_IDS)
        self.assertNotIn(CANDIDATE_M2_LIGHT_ID, PROTECTED_DEVICE_IDS)

    def test_eligible_case_still_pending_without_contracts(self) -> None:
        tool = SimulatedDeviceTool({"should-not-be-used": {"power": "on"}})
        outcome = evaluate_formal_control_attempt(
            _unoccupied_event(),
            LightShutdownPolicyInput(
                observed_device_id="observed-light",
                shutdown_basis=EXPLICIT_LIGHT_SHUTDOWN_BASIS,
                control_authorized=True,
                authorization_source="fictional-reviewed-policy",
                safety_policy_passed=True,
            ),
            trusted_authorization_sources=frozenset({"fictional-reviewed-policy"}),
            device_tool=tool,
        )
        self.assertTrue(outcome.eligibility.eligible)
        self.assertFalse(outcome.readiness.ready)
        self.assertEqual(outcome.readiness.status, "PENDING")
        self.assertEqual(outcome.action_requests_created, 0)
        self.assertFalse(outcome.dispatched)
        self.assertEqual(outcome.workflow.action_results, ())
        self.assertIn("m2_observation_to_control_mapping_unapproved", outcome.readiness.blockers)
        self.assertIn("m4_safety_conflict_feed_unapproved", outcome.readiness.blockers)
        self.assertEqual(tool.dispatch_count, 0)

    def test_protected_observed_device_is_blocked(self) -> None:
        context = HomeContext(
            HomeEnvironment(None, False),
            preference=None,
            energy=EnergyProfile(900.0, 400.0),
            devices=(DeviceObservation("security_lights", True, {"power": "on"}),),
            simulated=True,
        )
        outcome = evaluate_formal_control_attempt(
            make_energy_comfort_event(context),
            LightShutdownPolicyInput(
                observed_device_id="security_lights",
                shutdown_basis=EXPLICIT_LIGHT_SHUTDOWN_BASIS,
                control_authorized=True,
                authorization_source="fictional-reviewed-policy",
                safety_policy_passed=True,
            ),
            trusted_authorization_sources=frozenset({"fictional-reviewed-policy"}),
        )
        self.assertIn(
            "observed_device_is_protected_by_elderly_or_security",
            outcome.readiness.blockers,
        )
        self.assertEqual(outcome.action_requests_created, 0)

    def test_hypothetical_approved_contract_marks_ready_but_active_path_stays_pending(self) -> None:
        eligibility = evaluate_light_shutdown_candidate(
            _unoccupied_event(),
            LightShutdownPolicyInput(
                observed_device_id="observed-light",
                shutdown_basis=EXPLICIT_LIGHT_SHUTDOWN_BASIS,
                control_authorized=True,
                authorization_source="team-approved-source",
                safety_policy_passed=True,
            ),
            trusted_authorization_sources=frozenset({"team-approved-source"}),
        )
        readiness = assess_formal_control_readiness(
            eligibility.assessment,
            eligibility.eligibility,
            contract=FormalControlContractStatus(
                m2_observation_to_control_mapping_approved=True,
                m2_command_and_expected_state_schema_approved=True,
                m2_executable_authorization_source_approved=True,
                m4_safety_conflict_feed_approved=True,
                approved_control_device_id=CANDIDATE_M2_LIGHT_ID,
                approved_authorization_source="team-approved-source",
            ),
        )
        self.assertTrue(readiness.ready)
        active = evaluate_formal_control_attempt(
            _unoccupied_event(),
            LightShutdownPolicyInput(
                observed_device_id="observed-light",
                shutdown_basis=EXPLICIT_LIGHT_SHUTDOWN_BASIS,
                control_authorized=True,
                authorization_source="team-approved-source",
                safety_policy_passed=True,
            ),
            trusted_authorization_sources=frozenset({"team-approved-source"}),
        )
        self.assertFalse(active.readiness.ready)
        self.assertEqual(active.action_requests_created, 0)


if __name__ == "__main__":
    unittest.main()
