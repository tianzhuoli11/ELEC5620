"""SCRUM-32 formal-control readiness: fail closed until team contracts exist.

This module records what the repository actually provides today and what is
still missing.  It never invents an M2 device mapping or an executable
authorization source, and it never creates an ActionRequest.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from domains.elderly_safety.handler import ROOM_LIGHTS
from domains.home_security.response import INITIAL_DEVICE_STATES
from domains.smart_home_control.devices import BEDROOM_LIGHT, DEVICE_INVENTORY

from .control_policy import LightShutdownEligibility
from .monitoring import EnergyComfortAssessment


# M2 inventory light that could become a future mapping target after review.
# Presence in Smart Home Control inventory is not Energy & Comfort approval.
CANDIDATE_M2_LIGHT_ID = BEDROOM_LIGHT

# Devices owned by Elderly Safety / Home Security protective paths. Energy
# control must never command these off or override their protective state.
PROTECTED_DEVICE_IDS: frozenset[str] = frozenset({
    *ROOM_LIGHTS.values(),
    *INITIAL_DEVICE_STATES.keys(),
})

M2_DEVICE_IDS: frozenset[str] = frozenset(device.device_id for device in DEVICE_INVENTORY)


@dataclass(frozen=True)
class FormalControlContractStatus:
    """Checked-in contract gates. All remain false until teammates approve."""

    m2_observation_to_control_mapping_approved: bool = False
    m2_command_and_expected_state_schema_approved: bool = False
    m2_executable_authorization_source_approved: bool = False
    m4_safety_conflict_feed_approved: bool = False
    approved_control_device_id: str | None = None
    approved_authorization_source: str | None = None


# Single source of truth for the current repository. Do not flip these locally
# to claim formal control; change only after reviewed team agreement.
ACTIVE_FORMAL_CONTROL_CONTRACT = FormalControlContractStatus()


@dataclass(frozen=True)
class FormalControlReadiness:
    """Whether formal simulated Energy control may create an ActionRequest."""

    ready: bool
    status: str
    blockers: tuple[str, ...]
    evidence: tuple[str, ...]
    protected_device_ids: tuple[str, ...]
    candidate_m2_light_id: str
    contract: FormalControlContractStatus

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["contract"] = asdict(self.contract)
        return payload


def assess_formal_control_readiness(
    assessment: EnergyComfortAssessment,
    eligibility: LightShutdownEligibility,
    *,
    contract: FormalControlContractStatus | None = None,
) -> FormalControlReadiness:
    """Gate formal control. Eligibility alone never authorizes dispatch."""

    active = contract or ACTIVE_FORMAL_CONTROL_CONTRACT
    blockers: list[str] = []
    evidence: list[str] = [
        f"assessment_decision={assessment.decision}",
        f"eligibility={eligibility.eligible}",
        f"m2_inventory_light_present={CANDIDATE_M2_LIGHT_ID in M2_DEVICE_IDS}",
        f"protected_device_count={len(PROTECTED_DEVICE_IDS)}",
    ]

    if not eligibility.eligible:
        blockers.append("eligibility_not_met")
    else:
        evidence.append("eligibility_passed_non_executable")

    if not active.m2_observation_to_control_mapping_approved:
        blockers.append("m2_observation_to_control_mapping_unapproved")
    if not active.m2_command_and_expected_state_schema_approved:
        blockers.append("m2_command_schema_unapproved")
    if not active.m2_executable_authorization_source_approved:
        blockers.append("m2_executable_authorization_source_unapproved")
    if not active.m4_safety_conflict_feed_approved:
        blockers.append("m4_safety_conflict_feed_unapproved")
    if not active.approved_control_device_id:
        blockers.append("approved_control_device_id_missing")
    elif active.approved_control_device_id in PROTECTED_DEVICE_IDS:
        blockers.append("approved_control_device_id_is_protected")
    if not active.approved_authorization_source:
        blockers.append("approved_authorization_source_missing")

    if eligibility.observed_device_id and eligibility.observed_device_id in PROTECTED_DEVICE_IDS:
        blockers.append("observed_device_is_protected_by_elderly_or_security")

    ready = not blockers
    return FormalControlReadiness(
        ready=ready,
        status="READY" if ready else "PENDING",
        blockers=tuple(dict.fromkeys(blockers)),
        evidence=tuple(evidence),
        protected_device_ids=tuple(sorted(PROTECTED_DEVICE_IDS)),
        candidate_m2_light_id=CANDIDATE_M2_LIGHT_ID,
        contract=active,
    )
