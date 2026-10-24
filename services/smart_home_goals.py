"""Natural-language interpretation for Smart Home Control user goals."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import re
from typing import Any

from models import Event, GoalInterpretation


GoalProposalProvider = Callable[[Event], Mapping[str, Any]]
MODE_INTENTS = frozenset({"night_mode", "away_mode", "relax_mode"})
SUPPORTED_INTENTS = MODE_INTENTS | frozenset({"direct_control", "unlock_door"})
MODE_PARAMETER_KEYS = frozenset({"temperature_c"})
DIRECT_PARAMETER_KEYS = frozenset({
    "light_power", "light_brightness", "curtain_position", "door_locked",
    "ac_power", "ac_mode", "temperature_c",
})
NIGHT_MODE_PHRASES = ("good night", "going to sleep", "go to sleep", "bedtime", "晚安", "睡觉", "睡眠模式")
AWAY_MODE_PHRASES = ("leaving home", "going out", "away mode", "leave the house", "出门", "离家")
RELAX_MODE_PHRASES = ("relax", "movie mode", "watch a movie", "放松", "电影模式", "看电影")
LIGHT_OFF_PHRASES = ("turn off the light", "turn off the bedroom light", "switch off the light", "关灯", "关闭灯", "把灯关")
LIGHT_ON_PHRASES = ("turn on the light", "turn on the bedroom light", "switch on the light", "开灯", "打开灯", "把灯打开")
CURTAIN_CLOSED_PHRASES = ("close the curtain", "close curtain", "shut the curtain", "关窗帘", "关闭窗帘", "拉上窗帘")
CURTAIN_OPEN_PHRASES = ("open the curtain", "open curtain", "打开窗帘", "拉开窗帘")
AC_OFF_PHRASES = ("turn off the air conditioner", "turn off the ac", "switch off the air conditioner", "关空调", "关闭空调")
AC_ON_PHRASES = ("turn on the air conditioner", "turn on the ac", "switch on the air conditioner", "开空调", "打开空调")
NEGATABLE_DIRECT_PHRASES = (
    LIGHT_OFF_PHRASES
    + LIGHT_ON_PHRASES
    + CURTAIN_CLOSED_PHRASES
    + CURTAIN_OPEN_PHRASES
    + AC_OFF_PHRASES
    + AC_ON_PHRASES
    + ("unlock", "open the front door", "open front door", "lock the front door", "lock front door", "打开门锁", "解锁", "开门", "锁门", "锁上门", "把门锁上")
)


def _clarification(event: Event, evidence: str, question: str) -> GoalInterpretation:
    return GoalInterpretation(
        event_id=event.event_id,
        domain="smart_home_control",
        intent="clarify",
        evidence=evidence,
        clarification_question=question,
    )


def _contains(text: str, *phrases: str) -> bool:
    return any(phrase in text for phrase in phrases)


def _contains_negated_phrase(text: str, *phrases: str) -> bool:
    """Detect a supported phrase immediately governed by English or Chinese negation."""

    for phrase in phrases:
        start = 0
        while (index := text.find(phrase, start)) >= 0:
            prefix = text[max(0, index - 32):index]
            if re.search(r"(?:\b(?:do not|don't|dont|never|not to)\s+|(?:不要|别|不许|不能)\s*)$", prefix):
                return True
            start = index + len(phrase)
    return False


def _parse_direct_parameters(text: str) -> tuple[dict[str, Any], str | None]:
    """Extract an allow-listed device-state request without creating device commands."""

    parameters: dict[str, Any] = {}

    if _contains_negated_phrase(text, *NEGATABLE_DIRECT_PHRASES):
        return {}, "The request negates a device action. Please state the desired final device state."

    light_off = _contains(text, *LIGHT_OFF_PHRASES)
    light_on = _contains(text, *LIGHT_ON_PHRASES)
    if light_off and light_on:
        return {}, "The request contains conflicting light states. Please choose on or off."
    if light_off:
        parameters["light_power"] = "off"
    elif light_on:
        parameters["light_power"] = "on"

    light_mentioned = _contains(text, "light", "灯")
    if light_mentioned:
        brightness = re.search(r"(?:brightness|亮度)[^0-9]{0,12}(\d{1,3})", text)
        if brightness:
            value = int(brightness.group(1))
            if not 1 <= value <= 100:
                return {}, "Light brightness must be between 1 and 100 percent."
            parameters["light_brightness"] = value
            parameters.setdefault("light_power", "on")

    curtain_closed = _contains(text, *CURTAIN_CLOSED_PHRASES)
    curtain_open = _contains(text, *CURTAIN_OPEN_PHRASES)
    if curtain_closed and curtain_open:
        return {}, "The request contains conflicting curtain states. Please choose open or closed."
    if curtain_closed:
        parameters["curtain_position"] = "closed"
    elif curtain_open:
        parameters["curtain_position"] = "open"

    unlock = bool(re.search(r"\bunlock\b|\bopen (?:the )?(?:front )?door\b", text)) or _contains(text, "打开门锁", "解锁", "开门")
    lock = bool(re.search(r"\block (?:the )?(?:front )?door\b", text)) or _contains(text, "锁门", "锁上门", "把门锁上")
    if unlock and lock:
        return {}, "The request contains conflicting door-lock states. Please choose lock or unlock."
    if unlock:
        parameters["door_locked"] = False
    elif lock:
        parameters["door_locked"] = True

    ac_mentioned = bool(re.search(r"\b(?:air conditioner|air conditioning|ac)\b", text)) or "空调" in text
    if ac_mentioned:
        ac_off = _contains(text, *AC_OFF_PHRASES)
        ac_on = _contains(text, *AC_ON_PHRASES)
        if ac_off and ac_on:
            return {}, "The request contains conflicting air-conditioner power states."
        if ac_off:
            parameters["ac_power"] = "off"
        elif ac_on:
            parameters["ac_power"] = "on"

        temperature = re.search(r"(?:air conditioner|air conditioning|\bac\b|空调)[^0-9]{0,30}(\d{1,3})", text)
        if temperature:
            value = int(temperature.group(1))
            if not 18 <= value <= 28:
                return {}, "Air-conditioner temperature must be between 18 and 28 degrees Celsius."
            parameters["temperature_c"] = value
            parameters.setdefault("ac_power", "on")
        if _contains(text, "sleep mode", "睡眠模式"):
            parameters["ac_mode"] = "sleep"
        elif _contains(text, "eco mode", "节能模式"):
            parameters["ac_mode"] = "eco"
        elif _contains(text, "comfort mode", "舒适模式"):
            parameters["ac_mode"] = "comfort"

    return parameters, None


def validate_smart_home_parameters(intent: str, parameters: Mapping[str, Any]) -> dict[str, Any]:
    """Validate an interpreter proposal before domain planning uses it."""

    if not isinstance(parameters, Mapping):
        raise ValueError("goal parameters must be an object")
    if intent in MODE_INTENTS:
        allowed = MODE_PARAMETER_KEYS
    elif intent == "direct_control":
        allowed = DIRECT_PARAMETER_KEYS
        if not parameters:
            raise ValueError("direct_control requires at least one target state")
    elif intent == "unlock_door":
        allowed = frozenset()
    else:
        raise ValueError("unsupported Smart Home Control intent")
    if set(parameters) - allowed:
        raise ValueError("goal proposal contains unsupported parameters")

    validated = dict(parameters)
    for key in ("light_power", "ac_power"):
        if key in validated:
            value = validated[key]
            if isinstance(value, bool):
                validated[key] = "on" if value else "off"
            elif value not in ("on", "off"):
                raise ValueError(f"{key} must be on or off")
    if "curtain_position" in validated and validated["curtain_position"] not in ("open", "closed"):
        raise ValueError("curtain_position must be open or closed")
    if "door_locked" in validated and not isinstance(validated["door_locked"], bool):
        raise ValueError("door_locked must be a boolean")
    if "ac_mode" in validated and validated["ac_mode"] not in ("sleep", "eco", "comfort"):
        raise ValueError("ac_mode must be sleep, eco or comfort")
    if "light_brightness" in validated:
        value = validated["light_brightness"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 1 <= float(value) <= 100:
            raise ValueError("light_brightness is outside the permitted range")
        validated["light_brightness"] = round(float(value))
    if "temperature_c" in validated:
        value = validated["temperature_c"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 18 <= float(value) <= 28:
            raise ValueError("temperature_c is outside the permitted range")
        validated["temperature_c"] = round(float(value))
    return validated


def interpret_smart_home_goal_by_rules(event: Event, *, evidence_prefix: str = "") -> GoalInterpretation:
    """Small bilingual fallback used when campus AI is disabled or unavailable."""

    text = str(event.context.get("text", "")).strip().casefold()
    evidence = (evidence_prefix + "Deterministic bilingual rule match").strip()

    if _contains_negated_phrase(text, *(NIGHT_MODE_PHRASES + AWAY_MODE_PHRASES + RELAX_MODE_PHRASES)):
        return _clarification(
            event,
            evidence,
            "The request negates a home-mode change. Please state the desired final home mode.",
        )
    if any(phrase in text for phrase in NIGHT_MODE_PHRASES):
        return GoalInterpretation(event.event_id, "smart_home_control", "night_mode", evidence=evidence)
    if any(phrase in text for phrase in AWAY_MODE_PHRASES):
        return GoalInterpretation(event.event_id, "smart_home_control", "away_mode", evidence=evidence)
    if any(phrase in text for phrase in RELAX_MODE_PHRASES):
        return GoalInterpretation(event.event_id, "smart_home_control", "relax_mode", evidence=evidence)
    direct, problem = _parse_direct_parameters(text)
    if problem:
        return _clarification(event, evidence, problem)
    if direct:
        intent = "unlock_door" if direct == {"door_locked": False} else "direct_control"
        parameters = {} if intent == "unlock_door" else direct
        return GoalInterpretation(event.event_id, "smart_home_control", intent, parameters=parameters, evidence=evidence)
    return _clarification(
        event,
        (evidence_prefix + "No supported home mode or device target matched").strip(),
        "Please clarify the device states or home mode you want.",
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
        validated = validate_smart_home_parameters(intent, parameters)
        return GoalInterpretation(
            event_id=event.event_id,
            domain=domain,
            intent=intent,
            parameters=validated,
            evidence="Campus Qwen structured proposal; domain policy validation still required",
        )
