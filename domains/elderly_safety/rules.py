"""Deterministic fall-risk rules. These are the safety floor; a model may
confirm or raise the level but never lower it.

Thresholds are prototype values for team discussion (Stage 1 gave none).
They are not medical advice. Record any agreed change in Jira and here.

    HIGH    impact + inactivity >= HIGH_INACTIVITY_S, or posture "floor" with
            inactivity >= MEDIUM_INACTIVITY_S
    MEDIUM  impact with inactivity >= MEDIUM_INACTIVITY_S, or impact with the
            inactivity value missing, or inactivity alone >= HIGH_INACTIVITY_S
    LOW     otherwise (e.g. brief inactivity after an impact: something was
            dropped; resident already upright)

Night time or a bathroom/stairs location raises LOW -> MEDIUM only (a person
should look), never MEDIUM -> HIGH, so escalation stays evidence-based.
"""

from __future__ import annotations

from dataclasses import dataclass

from domains.elderly_safety.context import FallContext

MEDIUM_INACTIVITY_S = 20.0
HIGH_INACTIVITY_S = 60.0
RISKY_ROOMS = ("bathroom", "stairs")


@dataclass(frozen=True)
class RuleResult:
    risk_level: str
    rationale: str
    evidence: str


def assess_by_rules(ctx: FallContext) -> RuleResult:
    impact = ctx.impact_detected
    seconds = ctx.seconds_without_motion
    floor = ctx.posture == "floor"
    upright = ctx.posture == "upright"

    # --- HIGH ----------------------------------------------------------------
    if impact and seconds is not None and seconds >= HIGH_INACTIVITY_S:
        return RuleResult("HIGH", f"Impact detected and no motion for {seconds:g}s (>= {HIGH_INACTIVITY_S:g}s).", "impact+seconds_without_motion")
    if floor and seconds is not None and seconds >= MEDIUM_INACTIVITY_S:
        return RuleResult("HIGH", f"Resident on the floor with no motion for {seconds:g}s.", "posture+seconds_without_motion")

    # --- MEDIUM --------------------------------------------------------------
    if impact and seconds is None:
        return RuleResult("MEDIUM", "Impact detected but inactivity duration is unavailable; needs confirmation.", "impact (missing seconds_without_motion)")
    if impact and seconds >= MEDIUM_INACTIVITY_S:
        return RuleResult("MEDIUM", f"Impact detected and no motion for {seconds:g}s; asking the resident.", "impact+seconds_without_motion")
    if impact is None and seconds is not None and seconds >= HIGH_INACTIVITY_S:
        return RuleResult("MEDIUM", f"No impact data but no motion for {seconds:g}s; needs confirmation.", "seconds_without_motion (missing impact)")

    # --- LOW with contextual uplift -----------------------------------------
    if upright:
        reason, evidence = "Resident is upright again; likely a dropped object or brief stumble.", "posture"
    elif impact:
        reason, evidence = f"Impact followed by motion within {seconds:g}s; likely a dropped object.", "impact+seconds_without_motion"
    else:
        reason, evidence = "No impact and no prolonged inactivity.", "no_trigger"

    risky_time = ctx.time_of_day == "night"
    risky_room = any(room in ctx.location.lower() for room in RISKY_ROOMS)
    if (risky_time or risky_room) and not upright:
        why = "night time" if risky_time else f"{ctx.location} location"
        return RuleResult("MEDIUM", f"{reason} Raised to MEDIUM because of {why}.", evidence + "+context")
    return RuleResult("LOW", reason, evidence)
