"""Fall assessment: rules first, optional LLM proposal, policy floor, MEDIUM fallback.

UC-01 step 3 and extension 1; SCRUM-12 acceptance criteria. NFR-02: the time
from event receipt to classification (or fallback) is measured.

`FallAssessment` is the domain's full record (like Pet Care's
`PetAssessment`); `handler.py` maps it onto the shared `RiskAssessment`.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping

from models import Event

from domains.elderly_safety.context import FallContext, collect_context
from domains.elderly_safety.policy import RISK_LEVELS, apply_llm_fallback, apply_policy_floor
from domains.elderly_safety.rules import assess_by_rules

DOMAIN = "elderly_safety"

# Receives FallContext.for_llm() (de-identified dict, NFR-03) and returns a
# mapping with `risk_level` and `rationale`, or raises. The services layer
# wraps the real campus-qwen call behind this signature.
FallProposalProvider = Callable[[Mapping[str, Any]], Mapping[str, Any]]

EVIDENCE_SOURCES = ("rules", "llm_confirmed", "llm_fallback")


@dataclass(frozen=True)
class FallAssessment:
    event_id: str
    risk_level: str
    rationale: str
    evidence: str
    evidence_source: str
    policy_override: bool
    fallback_used: bool
    model_rationale: str | None
    requires_confirmation: bool
    classification_ms: float
    context: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _valid_proposal(proposal: Any) -> tuple[str, str] | None:
    if not isinstance(proposal, Mapping):
        return None
    level = proposal.get("risk_level")
    rationale = proposal.get("rationale")
    if level not in RISK_LEVELS or not isinstance(rationale, str) or not rationale.strip():
        return None
    return level, rationale.strip()


def assess_fall(event: Event, proposal_provider: FallProposalProvider | None = None) -> FallAssessment:
    started = time.perf_counter()
    ctx: FallContext = collect_context(event)
    rule = assess_by_rules(ctx)

    level, rationale = rule.risk_level, rule.rationale
    evidence_source, policy_override, fallback_used, model_rationale = "rules", False, False, None

    parsed = None
    if proposal_provider is not None:
        try:
            parsed = _valid_proposal(proposal_provider(ctx.for_llm()))
        except Exception:  # timeout, network, malformed JSON: never stops monitoring
            parsed = None

    if parsed is None:
        level = apply_llm_fallback(rule.risk_level)
        evidence_source, fallback_used = "llm_fallback", True
        if level != rule.risk_level:
            why = "no model configured" if proposal_provider is None else "model unavailable or invalid"
            rationale = f"{rule.rationale} Raised to MEDIUM: {why} (rule-based fallback)."
    else:
        proposed_level, model_rationale = parsed
        level, policy_override = apply_policy_floor(rule.risk_level, proposed_level)
        evidence_source = "llm_confirmed"
        if policy_override:
            rationale = f"{rule.rationale} Model proposed {proposed_level}; rules kept {level}."
        elif level != rule.risk_level:
            rationale = f"{rule.rationale} Model raised the level to {level}: {model_rationale}"

    return FallAssessment(
        event_id=event.event_id,
        risk_level=level,
        rationale=rationale,
        evidence=rule.evidence,
        evidence_source=evidence_source,
        policy_override=policy_override,
        fallback_used=fallback_used,
        model_rationale=model_rationale,
        requires_confirmation=(level == "MEDIUM"),
        classification_ms=(time.perf_counter() - started) * 1000.0,
        context=ctx.to_dict(),
    )
