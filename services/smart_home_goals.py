"""Natural-language interpretation for Smart Home Control user goals."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from models import Event, GoalInterpretation


GoalProposalProvider = Callable[[Event], Mapping[str, Any]]
SUPPORTED_INTENTS = frozenset({"night_mode", "away_mode", "relax_mode", "unlock_door"})
ALLOWED_PARAMETER_KEYS = frozenset({"temperature_c"})


def interpret_smart_home_goal_by_rules(event: Event, *, evidence_prefix: str = "") -> GoalInterpretation:
    """Small bilingual fallback used when campus AI is disabled or unavailable."""

    text = str(event.context.get("text", "")).strip().casefold()
    evidence = (evidence_prefix + "Deterministic bilingual rule match").strip()

    if any(phrase in text for phrase in ("unlock", "open the front door", "打开门锁", "解锁", "开门")):
        return GoalInterpretation(event.event_id, "smart_home_control", "unlock_door", evidence=evidence)
    if any(phrase in text for phrase in ("good night", "going to sleep", "go to sleep", "bedtime", "晚安", "睡觉", "睡眠模式")):
        return GoalInterpretation(event.event_id, "smart_home_control", "night_mode", evidence=evidence)
    if any(phrase in text for phrase in ("leaving home", "going out", "away mode", "leave the house", "出门", "离家")):
        return GoalInterpretation(event.event_id, "smart_home_control", "away_mode", evidence=evidence)
    if any(phrase in text for phrase in ("relax", "movie mode", "watch a movie", "放松", "电影模式", "看电影")):
        return GoalInterpretation(event.event_id, "smart_home_control", "relax_mode", evidence=evidence)
    return GoalInterpretation(
        event_id=event.event_id,
        domain="smart_home_control",
        intent="clarify",
        evidence=(evidence_prefix + "No supported home mode matched").strip(),
        clarification_question=(
            "Please clarify the home state you want. Supported examples are: "
            "'Good night', 'I'm leaving home', or 'Relax mode'."
        ),
    )


class SmartHomeGoalInterpreter:
    """Use a structured AI proposal when valid, otherwise fail safely to rules."""

    def __init__(self, proposal_provider: GoalProposalProvider | None = None) -> None:
        self.proposal_provider = proposal_provider

    def interpret(self, event: Event) -> GoalInterpretation:
        if event.event_type != "user_goal":
            raise ValueError("goal interpreter requires a user_goal event")
        if self.proposal_provider is None:
            return interpret_smart_home_goal_by_rules(event)
        try:
            proposal = self.proposal_provider(event)
            return self._validate(event, proposal)
        except Exception as exc:
            return interpret_smart_home_goal_by_rules(
                event,
                evidence_prefix=f"Campus AI fallback ({type(exc).__name__}); ",
            )

    @staticmethod
    def _validate(event: Event, proposal: Mapping[str, Any]) -> GoalInterpretation:
        if not isinstance(proposal, Mapping):
            raise ValueError("goal proposal must be an object")
        domain = proposal.get("domain")
        intent = proposal.get("intent")
        parameters = proposal.get("parameters", {})
        clarification = proposal.get("clarification_question")

        if domain != "smart_home_control":
            raise ValueError("goal proposal has the wrong domain")
        if intent == "clarify":
            if not isinstance(clarification, str) or not clarification.strip():
                raise ValueError("clarification proposal needs a question")
            return GoalInterpretation(
                event.event_id,
                domain,
                intent,
                evidence="Campus Qwen structured proposal; no device action authorised",
                clarification_question=clarification.strip(),
            )
        if intent not in SUPPORTED_INTENTS:
            raise ValueError("goal proposal has an unsupported intent")
        if not isinstance(parameters, Mapping):
            raise ValueError("goal parameters must be an object")
        unknown = set(parameters) - ALLOWED_PARAMETER_KEYS
        if unknown:
            raise ValueError("goal proposal contains unsupported parameters")
        validated = dict(parameters)
        if "temperature_c" in validated:
            value = validated["temperature_c"]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 18 <= float(value) <= 28:
                raise ValueError("temperature_c is outside the permitted range")
        return GoalInterpretation(
            event_id=event.event_id,
            domain=domain,
            intent=intent,
            parameters=validated,
            evidence="Campus Qwen structured proposal; domain policy validation still required",
        )
