"""Risk-level policy helpers for Elderly Safety.

Kept domain-local for now; proposed for `models/` once the team agrees
(they are generic and Pet Care applies the same idea).
"""

from __future__ import annotations

RISK_LEVELS = ("LOW", "MEDIUM", "HIGH")


def risk_rank(level: str) -> int:
    try:
        return RISK_LEVELS.index(level)
    except ValueError as exc:
        raise ValueError(f"unknown risk level: {level!r}") from exc


def apply_policy_floor(rule_level: str, proposed_level: str | None) -> tuple[str, bool]:
    """Rules are a floor: a model proposal may confirm or raise, never lower.

    Returns (final_level, policy_override); override is True when a lower
    proposal was rejected.
    """
    risk_rank(rule_level)
    if proposed_level is None or proposed_level not in RISK_LEVELS:
        return rule_level, False
    if risk_rank(proposed_level) < risk_rank(rule_level):
        return rule_level, True
    return proposed_level, False


def apply_llm_fallback(rule_level: str) -> str:
    """Documented MEDIUM fallback when the model is unavailable or invalid
    (UC-01 extension 1, SCRUM-12): LOW -> MEDIUM, MEDIUM/HIGH kept."""
    return RISK_LEVELS[max(risk_rank(rule_level), risk_rank("MEDIUM"))]
