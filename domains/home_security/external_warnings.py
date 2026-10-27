"""OR-06: validate fictional external warnings before shared-agent response."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import re
from typing import Any, Mapping

from models import ActionRequest, Event, MonitoringDecision, RiskAssessment

from .monitoring import ProposalProvider, SecurityAssessment, RISK_LEVELS
from .response import notification


WARNING_EVENT_TYPE = "simulated_external_warning"
TRUSTED_SOURCE = "simulated-course-warning-feed"
HOUSEHOLD_AREA = "SYDNEY_INNER_WEST"
AREA_CODES = (HOUSEHOLD_AREA, "BLUE_MOUNTAINS", "NORTHERN_BEACHES")
HAZARD_TYPES = ("EARTHQUAKE", "FLOOD", "SEVERE_STORM", "BUSHFIRE")
SEVERITIES = ("ADVISORY", "WARNING", "EMERGENCY")


@dataclass(frozen=True)
class ExternalWarningAssessment(SecurityAssessment):
    valid: bool = False
    relevant: bool = False
    warning_type: str | None = None
    severity: str | None = None
    source_id: str | None = None
    validation_errors: tuple[str, ...] = ()


def _aware_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def assess_external_warning(
    event: Event, proposal_provider: ProposalProvider | None = None,
    *, now: datetime | None = None,
) -> ExternalWarningAssessment:
    """Classify trust, time validity and exact household-area relevance.

    A text source ID is only a simulation allowlist check, not real-world
    authentication. Invalid warnings never reach the LLM or device policy.
    """
    if event.event_type != WARNING_EVENT_TYPE:
        raise ValueError("not an external warning event")
    payload = event.context.get("warning")
    warning = payload if isinstance(payload, dict) else {}
    errors: list[str] = []
    if not isinstance(payload, dict):
        errors.append("warning payload must be an object")
    if event.simulated is not True or warning.get("simulated") is not True:
        errors.append("warning and event must both be SIMULATED")
    if event.source != TRUSTED_SOURCE or warning.get("source_id") != TRUSTED_SOURCE:
        errors.append("source is outside the simulated trusted-source allowlist")
    warning_id = warning.get("warning_id")
    if not isinstance(warning_id, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", warning_id) is None:
        errors.append("warning_id is missing or invalid")
    hazard = warning.get("hazard_type")
    if hazard not in HAZARD_TYPES:
        errors.append("hazard_type is missing or unsupported")
    severity = warning.get("severity")
    if severity not in SEVERITIES:
        errors.append("severity is missing or unsupported")
    areas = warning.get("areas")
    if not isinstance(areas, list) or not areas or any(not isinstance(area, str) or area not in AREA_CODES for area in areas):
        errors.append("affected areas are missing or invalid")
        areas = []
    issued = _aware_time(warning.get("issued_at"))
    expires = _aware_time(warning.get("expires_at"))
    if issued is None or expires is None:
        errors.append("issued_at and expires_at need time zones")
    else:
        current = now if now is not None else datetime.now(timezone.utc)
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValueError("comparison time needs a time zone")
        if issued > current or expires <= current or expires <= issued:
            errors.append("warning is future-dated, expired or has invalid time order")

    valid = not errors
    relevant = valid and HOUSEHOLD_AREA in areas
    level = "HIGH" if relevant and severity == "EMERGENCY" else "MEDIUM" if relevant else "LOW"
    if not valid:
        rationale = "SIMULATED external warning rejected: " + "; ".join(errors) + "."
    elif not relevant:
        rationale = "Valid SIMULATED external warning does not affect the configured household area."
    else:
        rationale = f"Valid SIMULATED {hazard} {severity} warning affects the configured household area."
    evidence = (
        f"source_id={warning.get('source_id')!r}; warning_id={warning_id!r}; "
        f"hazard_type={hazard!r}; severity={severity!r}; areas={areas!r}; "
        f"household_area={HOUSEHOLD_AREA}; valid={valid}; relevant={relevant}; "
        f"validation_errors={errors!r}"
    )
    rule = ExternalWarningAssessment(
        event_id=event.event_id, risk_level=level, rationale=rationale, evidence=evidence,
        valid=valid, relevant=relevant,
        warning_type=hazard if isinstance(hazard, str) else None,
        severity=severity if isinstance(severity, str) else None,
        source_id=warning.get("source_id") if isinstance(warning.get("source_id"), str) else None,
        validation_errors=tuple(errors),
    )
    if not valid or proposal_provider is None:
        return rule

    # As with household sensors, LLM output is only advisory. It cannot make
    # an irrelevant warning relevant or authorize an emergency action.
    status = "INVALID"
    model_rationale = None
    override = False
    try:
        proposal = proposal_provider(event)
        if isinstance(proposal, Mapping):
            suggested = proposal.get("risk_level")
            reason = proposal.get("rationale")
            if suggested in RISK_LEVELS and isinstance(reason, str) and reason.strip():
                if suggested == level:
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
    return replace(
        rule, policy_override=override, fallback_used=status != "ACCEPTED",
        llm_status=status, model_rationale=model_rationale,
    )


def external_warning_decision(event: Event, warning: ExternalWarningAssessment) -> MonitoringDecision:
    """Notify on relevant warnings; only EMERGENCY enables a simulated mode."""
    assessment = RiskAssessment(
        event_id=warning.event_id, domain="home_security", risk_level=warning.risk_level,
        rationale=warning.rationale, evidence=warning.evidence,
        policy_override=warning.policy_override, fallback_used=warning.fallback_used,
    )
    if not warning.valid or not warning.relevant:
        return MonitoringDecision(assessment=assessment)
    actions = ()
    if warning.risk_level == "HIGH" and warning.severity == "EMERGENCY":
        actions = (ActionRequest(
            event_id=event.event_id, device_id="emergency_mode", action="set_state",
            parameters={"active": True}, expected_state={"active": True},
            authorization="POLICY", simulated=True,
        ),)
    message = (
        f"SIMULATED {warning.warning_type} {warning.severity} warning affects "
        f"{HOUSEHOLD_AREA}; emergency mode requested."
        if actions else
        f"SIMULATED {warning.warning_type} {warning.severity} warning affects {HOUSEHOLD_AREA}; review the alert."
    )
    return MonitoringDecision(
        assessment=assessment, action_requests=actions,
        notification_request=notification(event, message),
    )
