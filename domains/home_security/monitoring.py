"""SCRUM-15 security monitoring: fixed policy with an optional LLM proposal."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping

from models import Event

EVENT_TYPE = "security_observation"
CORE_READING_TYPES = (
    "smoke_alarm", "gas_alarm", "water_leak", "door_open", "motion_detected",
)
READING_TYPES = CORE_READING_TYPES + (
    "appliance_overheat_alarm", "appliance_unexpected_run",
    "window_open", "smart_lock_access_anomaly",
)
RISK_LEVELS = ("LOW", "MEDIUM", "HIGH")
ProposalProvider = Callable[[Event], Mapping[str, Any]]


@dataclass(frozen=True)
class SecurityAssessment:
    event_id: str
    risk_level: str
    rationale: str
    evidence: str
    requires_human_review: bool = False
    policy_override: bool = False
    fallback_used: bool = False
    llm_status: str = "NOT_REQUESTED"
    model_rationale: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validated_readings(event: Event) -> tuple[dict[str, int | None], list[str]]:
    """Only one binary, state-unit reading is accepted for each sensor type."""
    values: dict[str, int | None] = {}
    invalid: list[str] = []
    for kind in READING_TYPES:
        matches = [reading for reading in event.readings if reading.reading_type == kind]
        if not matches and kind not in CORE_READING_TYPES:
            values[kind] = None  # Older five-sensor events remain valid.
            continue
        if len(matches) != 1 or matches[0].unit != "state":
            values[kind] = None
            invalid.append(kind)
            continue
        value = matches[0].value
        if isinstance(value, bool):
            values[kind] = int(value)
        elif isinstance(value, (int, float)) and value in (0, 1):
            values[kind] = int(value)
        else:
            values[kind] = None
            invalid.append(kind)
    return values, invalid


def _context(event: Event) -> tuple[str, str, bool | None, str, str]:
    data = event.context
    mode = data.get("home_mode")
    mode = mode if mode in ("HOME", "AWAY") else "UNKNOWN"
    recent = data.get("recent_activity")
    recent = recent if recent in ("EXPECTED", "NONE") else "UNKNOWN"
    authorised = data.get("authorized_entry")
    authorised = authorised if isinstance(authorised, bool) else None
    devices = data.get("device_status")
    devices = devices if isinstance(devices, dict) else {}
    lock = devices.get("front_door_lock")
    lock = lock if lock in ("locked", "unlocked") else "unknown"
    valve = devices.get("water_valve")
    valve = valve if valve in ("open", "closed") else "unknown"
    return mode, recent, authorised, lock, valve


def _rule_assessment(event: Event) -> SecurityAssessment:
    if event.event_type != EVENT_TYPE or not event.simulated:
        raise ValueError("SCRUM-15 accepts simulated security observations only")

    values, invalid = validated_readings(event)
    mode, recent, authorised, lock, valve = _context(event)
    smoke, gas, water, door, motion, overheat, unexpected_run, window, lock_access = (
        values[kind] for kind in READING_TYPES
    )
    findings: list[tuple[str, str]] = []
    if smoke == 1 or gas == 1:
        findings.append(("HIGH", "A smoke or gas alarm is triggered; fixed safety policy requires HIGH risk."))
    if overheat == 1:
        findings.append(("HIGH", "The simulated appliance overheat alarm is active."))
    if water == 1:
        if valve == "open":
            findings.append(("HIGH", "A water leak is detected while the simulated water valve is open."))
        else:
            findings.append(("MEDIUM", "A water leak is detected; its source needs checking."))

    unexplained_away = mode == "AWAY" and authorised is False and recent == "NONE"
    if unexplained_away and motion == 1 and (door == 1 or window == 1 or lock_access == 1):
        findings.append(("HIGH", "Opening or lock-access anomaly coincides with motion in Away Mode."))
    if unexplained_away and lock_access == 1 and door == 1:
        findings.append(("HIGH", "A lock-access anomaly coincides with an open door in Away Mode."))
    if lock_access == 1:
        findings.append(("MEDIUM", "The simulated smart lock reports an abnormal access attempt."))
    if unexpected_run == 1:
        findings.append(("MEDIUM", "The simulated appliance reports unexpected operation."))
    if door == 1 and lock == "locked":
        findings.append(("MEDIUM", "The door reports open while the lock reports locked."))
    if door == 1 or window == 1 or motion == 1:
        if authorised is True or recent == "EXPECTED":
            findings.append(("LOW", "Door, window or motion activity matches authorised or expected activity."))
        else:
            findings.append(("MEDIUM", "Door, window or motion activity has no confirmed authorised explanation."))

    level = max((item[0] for item in findings), key=RISK_LEVELS.index, default="LOW")
    rationale = " ".join(reason for risk, reason in findings if risk == level)
    if not rationale:
        rationale = "No simulated hazard or intrusion sensor is triggered."
    if invalid:
        if level == "LOW":
            level = "MEDIUM"
        rationale += " Missing or invalid sensor data requires review."

    # Only MEDIUM pauses for a homeowner decision. HIGH follows the fixed,
    # pre-approved emergency policy immediately; a notification still follows.
    review = level == "MEDIUM"

    evidence = (
        f"binary_readings={values}; home_mode={mode}; recent_activity={recent}; "
        f"authorized_entry={authorised}; front_door_lock={lock}; water_valve={valve}; "
        f"missing_or_invalid={invalid}"
    )
    return SecurityAssessment(event.event_id, level, rationale, evidence, review)


def assess_security_event(
    event: Event, proposal_provider: ProposalProvider | None = None,
) -> SecurityAssessment:
    """Keep the fixed result; use a matching LLM proposal only as an explanation."""
    rule = _rule_assessment(event)
    if proposal_provider is None:
        return rule

    status = "INVALID"
    model_rationale = None
    override = False
    try:
        proposal = proposal_provider(event)
        if isinstance(proposal, Mapping):
            level = proposal.get("risk_level")
            reason = proposal.get("rationale")
            if level in RISK_LEVELS and isinstance(reason, str) and reason.strip():
                if level == rule.risk_level:
                    status = "ACCEPTED"
                    model_rationale = reason.strip()[:500]
                else:
                    status = "CONFLICT"
                    override = True
    except TimeoutError:
        status = "TIMEOUT"
    except (ValueError, KeyError, TypeError):
        status = "INVALID"
    except Exception:
        status = "ERROR"

    return SecurityAssessment(
        event_id=rule.event_id,
        risk_level=rule.risk_level,
        rationale=rule.rationale,
        evidence=rule.evidence,
        requires_human_review=rule.requires_human_review,
        policy_override=override,
        fallback_used=status != "ACCEPTED",
        llm_status=status,
        model_rationale=model_rationale,
    )
