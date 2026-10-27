"""Fail-closed Energy & Comfort policy preparation with no device execution."""

from __future__ import annotations

from dataclasses import dataclass

from models import HomeContext

from .monitoring import EnergyComfortAssessment


EXPLICIT_LIGHT_SHUTDOWN_BASIS = "explicit_unoccupied_light_shutdown_request"


@dataclass(frozen=True)
class LightShutdownPolicyInput:
    """Domain-only facts required before a light may become a control candidate.

    These fields deliberately do not claim an M2 device ID, command schema, or
    POLICY authorization.  Their defaults therefore fail closed.
    """

    observed_device_id: str | None = None
    shutdown_basis: str | None = None
    control_authorized: bool | None = None
    authorization_source: str | None = None
    safety_policy_passed: bool | None = None
    unknown_safety_conditions: tuple[str, ...] = ()
    conflicting_safety_conditions: tuple[str, ...] = ()


@dataclass(frozen=True)
class LightShutdownEligibility:
    """Non-executable policy result; this is not an ActionRequest."""

    eligible: bool
    observed_device_id: str | None
    reasons: tuple[str, ...]
    evidence: tuple[str, ...]


def assess_light_shutdown_eligibility(
    assessment: EnergyComfortAssessment,
    context: HomeContext,
    policy_input: LightShutdownPolicyInput | None = None,
    *,
    trusted_authorization_sources: frozenset[str] = frozenset(),
) -> LightShutdownEligibility:
    """Check whether an observed light is eligible for later M2 planning.

    Eligibility never dispatches a command and does not establish a control ID,
    action schema, or authorization.  Missing policy input is an explicit denial.
    """

    supplied = policy_input or LightShutdownPolicyInput()
    reasons: list[str] = []
    evidence: list[str] = []

    if assessment.decision != "ADJUSTMENT_NEEDED":
        reasons.append("assessment_not_adjustment_needed")
    else:
        evidence.append("assessment=ADJUSTMENT_NEEDED")

    if supplied.shutdown_basis != EXPLICIT_LIGHT_SHUTDOWN_BASIS:
        reasons.append("explicit_light_shutdown_basis_missing")
    else:
        evidence.append(f"shutdown_basis={supplied.shutdown_basis}")

    if context.environment.occupied is not False:
        reasons.append(
            "occupancy_unknown" if context.environment.occupied is None else "home_is_occupied"
        )
    else:
        evidence.append("occupied=False")

    device = next(
        (item for item in context.devices if item.device_id == supplied.observed_device_id),
        None,
    )
    if device is None:
        reasons.append("observed_light_not_found")
    else:
        if device.available is not True:
            reasons.append(
                "light_availability_unknown" if device.available is None else "light_unavailable"
            )
        else:
            evidence.append("light_available=True")
        if device.observed_state.get("power") != "on":
            reasons.append("light_not_observed_on")
        else:
            evidence.append("light_power=on")

    if supplied.control_authorized is not True:
        reasons.append("control_authorization_unconfirmed")
    elif not supplied.authorization_source:
        reasons.append("control_authorization_source_missing")
    elif supplied.authorization_source not in trusted_authorization_sources:
        reasons.append("control_authorization_source_untrusted")
    else:
        evidence.append(f"control_authorization_source={supplied.authorization_source}")

    if supplied.safety_policy_passed is not True:
        reasons.append(
            "safety_policy_unknown"
            if supplied.safety_policy_passed is None
            else "safety_policy_rejected"
        )
    else:
        evidence.append("safety_policy_passed=True")

    if supplied.unknown_safety_conditions:
        reasons.append("unknown_safety_conditions")
    if supplied.conflicting_safety_conditions:
        reasons.append("conflicting_safety_conditions")

    return LightShutdownEligibility(
        eligible=not reasons,
        observed_device_id=supplied.observed_device_id,
        reasons=tuple(reasons),
        evidence=tuple(evidence),
    )
