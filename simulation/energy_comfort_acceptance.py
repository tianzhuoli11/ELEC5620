"""Repeatable offline UC-05 acceptance evidence for implemented behavior only."""

from __future__ import annotations

from dataclasses import replace
import json
from typing import Any

from domains.energy_comfort.control_policy import (
    EXPLICIT_LIGHT_SHUTDOWN_BASIS, LightShutdownPolicyInput,
)
from domains.energy_comfort.explanations import explain_energy_comfort
from domains.energy_comfort.integration import (
    evaluate_light_shutdown_candidate, monitor_energy_comfort_workflow,
)
from models import DeviceObservation, EnergyProfile, HomeContext, HomeEnvironment, SensorReading, UserPreference
from simulation.energy_comfort_demo import make_energy_comfort_event
from simulation.energy_comfort_execution_fixture import run_test_only_execution_cases


class _RejectDeviceUse:
    def __init__(self) -> None:
        self.dispatch_calls = 0
        self.read_calls = 0

    def dispatch(self, request: object) -> object:
        self.dispatch_calls += 1
        raise AssertionError("acceptance preparation must not dispatch")

    def read_state(self, device_id: str) -> dict[str, Any]:
        self.read_calls += 1
        raise AssertionError("acceptance preparation must not read control state")


def _context(temperature: float | None, occupied: bool | None) -> HomeContext:
    return HomeContext(
        HomeEnvironment(temperature, occupied), UserPreference(20.0, 24.0),
        simulated=True,
    )


def _assessment_case(case_id: str, context: HomeContext, expected_decision: str) -> dict[str, Any]:
    event = make_energy_comfort_event(context)
    tool = _RejectDeviceUse()
    outcome = monitor_energy_comfort_workflow(event, device_tool=tool)
    explanation = explain_energy_comfort(outcome.assessment, workflow=outcome.workflow)
    actual = {
        "decision": outcome.assessment.decision,
        "workflow_outcome": outcome.workflow.outcome,
        "execution_status": explanation.execution_status,
        "dispatch_calls": tool.dispatch_calls,
        "read_calls": tool.read_calls,
    }
    expected = {
        "decision": expected_decision,
        "workflow_outcome": "ASSESSED",
        "execution_status": "NOT_EXECUTED",
        "dispatch_calls": 0,
        "read_calls": 0,
    }
    return {
        "case_id": case_id,
        "input": event.to_dict(),
        "expected": expected,
        "actual": actual,
        "decision": outcome.assessment.to_dict(),
        "trace": [item.outcome for item in outcome.workflow.trace],
        "test_result": "PASS" if actual == expected else "FAIL",
    }


def _eligibility_case(
    case_id: str,
    policy: LightShutdownPolicyInput,
    trusted_sources: frozenset[str],
    expected_eligible: bool,
    expected_reason: str | None,
) -> dict[str, Any]:
    context = HomeContext(
        HomeEnvironment(None, False), preference=None,
        energy=EnergyProfile(900.0, 400.0),
        devices=(DeviceObservation("observed-light", True, {"power": "on"}),),
        simulated=True,
    )
    event = make_energy_comfort_event(context)
    tool = _RejectDeviceUse()
    outcome = evaluate_light_shutdown_candidate(
        event, policy,
        trusted_authorization_sources=trusted_sources,
        device_tool=tool,
    )
    explanation = explain_energy_comfort(
        outcome.assessment, workflow=outcome.workflow,
        eligibility=outcome.eligibility,
    )
    actual = {
        "eligible": outcome.eligibility.eligible,
        "expected_reason_present": (
            expected_reason in outcome.eligibility.reasons if expected_reason else True
        ),
        "execution_status": explanation.execution_status,
        "dispatch_calls": tool.dispatch_calls,
        "read_calls": tool.read_calls,
    }
    expected = {
        "eligible": expected_eligible,
        "expected_reason_present": True,
        "execution_status": "NOT_EXECUTED",
        "dispatch_calls": 0,
        "read_calls": 0,
    }
    return {
        "case_id": case_id,
        "input": {
            "event": event.to_dict(),
            "policy": {
                "observed_device_id": policy.observed_device_id,
                "shutdown_basis": policy.shutdown_basis,
                "control_authorized": policy.control_authorized,
                "authorization_source": policy.authorization_source,
                "safety_policy_passed": policy.safety_policy_passed,
                "unknown_safety_conditions": list(policy.unknown_safety_conditions),
                "conflicting_safety_conditions": list(policy.conflicting_safety_conditions),
            },
            "trusted_authorization_sources": sorted(trusted_sources),
        },
        "expected": expected,
        "actual": actual,
        "decision": outcome.assessment.to_dict(),
        "trace": [item.outcome for item in outcome.workflow.trace],
        "explanation": explanation.to_dict(),
        "test_result": "PASS" if actual == expected else "FAIL",
    }


def _invalid_input_case() -> dict[str, Any]:
    event = make_energy_comfort_event(_context(22.0, True))
    bad_temperature = SensorReading(
        "simulated-indoor-temperature", "indoor_temperature", 72.0, "F", event.timestamp,
    )
    event = replace(event, readings=(bad_temperature, *event.readings[1:]))
    tool = _RejectDeviceUse()
    error = None
    try:
        monitor_energy_comfort_workflow(event, device_tool=tool)
    except ValueError as exc:
        error = str(exc)
    actual = {
        "rejected": error is not None,
        "error_mentions_unit": error is not None and "unit C" in error,
        "dispatch_calls": tool.dispatch_calls,
        "read_calls": tool.read_calls,
    }
    expected = {
        "rejected": True, "error_mentions_unit": True,
        "dispatch_calls": 0, "read_calls": 0,
    }
    return {
        "case_id": "invalid_temperature_unit",
        "input": event.to_dict(),
        "expected": expected,
        "actual": actual,
        "decision": None,
        "trace": [],
        "test_result": "PASS" if actual == expected else "FAIL",
    }


def run_uc05_acceptance_evidence() -> dict[str, Any]:
    """Run implemented UC-05 cases and label unimplemented execution evidence Pending."""

    trusted = frozenset({"fictional-reviewed-policy"})
    approved = LightShutdownPolicyInput(
        observed_device_id="observed-light",
        shutdown_basis=EXPLICIT_LIGHT_SHUTDOWN_BASIS,
        control_authorized=True,
        authorization_source="fictional-reviewed-policy",
        safety_policy_passed=True,
    )
    cases = [
        _assessment_case("no_adjustment", _context(22.0, True), "NO_ADJUSTMENT"),
        _assessment_case("temperature_lower_boundary", _context(20.0, True), "NO_ADJUSTMENT"),
        _assessment_case("temperature_upper_boundary", _context(24.0, True), "NO_ADJUSTMENT"),
        _assessment_case("adjustment_needed", _context(27.0, True), "ADJUSTMENT_NEEDED"),
        _assessment_case("occupancy_unknown", _context(22.0, None), "INSUFFICIENT_DATA"),
        _invalid_input_case(),
        _eligibility_case(
            "default_authorization_denied",
            LightShutdownPolicyInput(observed_device_id="observed-light"),
            trusted, False, "control_authorization_unconfirmed",
        ),
        _eligibility_case(
            "untrusted_authorization_denied",
            replace(approved, authorization_source="self-declared"),
            trusted, False, "control_authorization_source_untrusted",
        ),
        _eligibility_case(
            "safety_conflict_denied",
            replace(approved, conflicting_safety_conditions=("security_requires_light",)),
            trusted, False, "conflicting_safety_conditions",
        ),
        _eligibility_case(
            "trusted_eligibility_non_executable", approved, trusted, True, None,
        ),
    ]
    execution_cases = run_test_only_execution_cases()
    return {
        "suite": "UC-05 offline acceptance preparation",
        "coverage_layers": {
            "assessment_and_eligibility": "ASSESSMENT_ONLY",
            "execution_fixture": "TEST_ONLY_SIMULATION",
            "formal_energy_comfort_control": "PENDING",
        },
        "cases": cases,
        "test_only_execution_cases": execution_cases,
        "shared_framework_execution_coverage": [
            "test_three_agent_path_verifies_simulated_state",
            "test_review_gate_prevents_dispatch",
            "test_offline_device_does_not_report_success",
            "test_readback_mismatch_is_unverified",
            "test_readback_failure_retains_dispatch_acceptance",
            "test_first_device_failure_skips_later_device",
        ],
        "summary": {
            "passed": sum(case["test_result"] == "PASS" for case in cases),
            "failed": sum(case["test_result"] == "FAIL" for case in cases),
            "test_only_execution_passed": sum(
                case["test_result"] == "PASS" for case in execution_cases
            ),
        },
        "pending": [
            "M2-approved device ID and command schema",
            "Executable POLICY authorization and cross-domain safety interface",
            "Formal Energy & Comfort device dispatch and independent readback acceptance evidence",
            "Failure recovery, timeout, and bounded replanning evidence",
            "Post-action temperature, power, and energy-savings verification",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(run_uc05_acceptance_evidence(), indent=2))
