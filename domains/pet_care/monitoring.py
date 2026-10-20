"""Sprint 0 pet observation rules; no notification or feeder control occurs here."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping

from models import Event

RISK_LEVELS = ("LOW", "MEDIUM", "HIGH")
EMPTY_BOWL_PERCENT = 10
UNUSUAL_INACTIVITY_MINUTES = 60
HIGH_INACTIVITY_MINUTES = 120


@dataclass(frozen=True)
class PetAssessment:
    event_id: str
    risk_level: str
    rationale: str
    policy_override: bool
    fallback_used: bool
    evidence: str
    feeding_requested: bool = False
    model_rationale: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _numeric_reading(event: Event, reading_type: str, unit: str) -> float | None:
    matches = [item for item in event.readings if item.reading_type == reading_type]
    if len(matches) != 1 or matches[0].unit != unit:
        return None
    value = matches[0].value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _rule_assessment(event: Event) -> tuple[str, str, str]:
    if event.event_type == "pet_bowl_level":
        value = _numeric_reading(event, "food_level_percent", "%")
        if value is None or not 0 <= value <= 100:
            return "MEDIUM", "Food level is unavailable or invalid; the bowl needs review.", "missing_or_invalid_food_level"
        if value <= EMPTY_BOWL_PERCENT:
            return "MEDIUM", f"Food level is {value:g}%, at or below the {EMPTY_BOWL_PERCENT}% review threshold.", "food_level_percent"
        return "LOW", f"Food level is {value:g}%, above the review threshold.", "food_level_percent"

    if event.event_type == "pet_inactivity":
        value = _numeric_reading(event, "inactive_minutes", "min")
        if value is None or value < 0:
            return "MEDIUM", "Inactivity duration is unavailable or invalid; the pet needs review.", "missing_or_invalid_inactivity"
        if value >= HIGH_INACTIVITY_MINUTES:
            return "HIGH", f"No activity was observed for {value:g} minutes.", "inactive_minutes"
        if value >= UNUSUAL_INACTIVITY_MINUTES:
            return "MEDIUM", f"No activity was observed for {value:g} minutes.", "inactive_minutes"
        return "LOW", f"Inactivity lasted {value:g} minutes, below the review threshold.", "inactive_minutes"

    raise ValueError(f"unsupported pet event type: {event.event_type}")


def assess_pet_event(
    event: Event,
    proposal_provider: Callable[[Event], Mapping[str, Any]] | None = None,
) -> PetAssessment:
    """Assess one pet event with fixed rules and an optional untrusted LLM proposal.

    Proposals may confirm the rule-based level. Missing, malformed or conflicting
    proposals fall back to the rule result; they never authorise feeding.
    """

    rule_level, rationale, evidence = _rule_assessment(event)
    fallback_used = proposal_provider is None
    policy_override = False
    model_rationale = None
    if proposal_provider is not None:
        try:
            proposal = proposal_provider(event)
            proposed_level = proposal.get("risk_level")
            proposed_reason = proposal.get("rationale")
            valid = proposed_level in RISK_LEVELS and isinstance(proposed_reason, str) and bool(proposed_reason.strip())
            if not valid:
                fallback_used = True
            elif proposed_level != rule_level:
                policy_override = True
                fallback_used = True
            else:
                model_rationale = proposed_reason.strip()
        except Exception:  # A failed external proposal must not stop monitoring.
            fallback_used = True

    return PetAssessment(
        event_id=event.event_id,
        risk_level=rule_level,
        rationale=rationale,
        policy_override=policy_override,
        fallback_used=fallback_used,
        evidence=evidence,
        model_rationale=model_rationale,
    )
