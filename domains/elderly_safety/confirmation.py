"""Resident confirmation for suspected falls (UC-01 steps 5-6, SCRUM-24).

Questions, the deterministic reply interpreter and an optional model-backed
interpreter hook. The model only ever sees the reply text and the attempt
number (NFR-03); its verdict is validated and falls back to the rules.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Mapping

from models import ConfirmationReply, Event, PendingConfirmation

CONFIRMATION_TIMEOUT_S = 30
MAX_ATTEMPTS = 2

QUESTIONS = {
    1: "Are you okay? Please reply.",
    2: "Do you need me to contact your family? Please answer 'yes' or 'no'.",
}

VERDICTS = ("safe", "help", "unclear")

# Receives {"reply": str, "attempt": int} and returns {"verdict": ..., "rationale": ...} or raises.
ReplyInterpreter = Callable[[Mapping[str, Any]], Mapping[str, Any]]

# Phrases are matched anywhere in the reply; any of them means help.
# "can't move", "not okay" and "faint" were added after the first reply evaluation
# (simulation/elderly_reply_evaluation.py) showed "No, I can't move" being closed as safe;
# "breath", "blood", "broken", "chest" and "hit my head" after the second showed
# "okay, I can't breathe" being closed as safe.
_HELP = ("help", "can't get up", "cant get up", "cannot get up", "can't move", "cant move", "cannot move", "can't stand", "cant stand", "cannot stand", "unable to",
         "not ok", "hurt", "pain", "bleeding", "blood", "broken", "breath", "chest", "hit my head", "call", "ambulance",
         "emergency", "dizzy", "faint", "stuck")
_SAFE = ("i'm ok", "im ok", "i am ok", "i'm fine", "im fine", "i am fine", "i'm okay", "im okay", "i am okay", "ok", "okay", "fine", "all good", "no help", "false alarm", "dropped", "nothing happened")
# After a leading safe/no phrase, the rest of the reply may only contain these words.
# Anything else ("No idea", "No, wait", "okay but I fell") makes the reply unclear:
# a whitelist, because a list of worrying words can never be complete (PR #26 review).
_SAFE_REST_WORDS = frozenset({
    "i", "i'm", "im", "am", "it's", "its", "is", "a", "to", "with", "me", "my", "the",
    "fine", "ok", "okay", "alright", "all", "good", "really", "thanks", "thank", "you",
    "just", "sat", "sit", "down", "rest", "resting", "dropped", "cup", "something",
    "son", "daughter", "husband", "wife", "family", "neighbour", "neighbor", "friend", "nurse", "carer",
    "already", "here",
})
_YES_WORDS = frozenset({"yes", "yeah", "yep", "please", "contact", "need", "come"})
_NO_START = ("no", "nope", "nah", "don't", "dont", "not needed", "no need", "no thanks")


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text)


def _after_phrase(text: str, phrases: tuple[str, ...]) -> str | None:
    """Rest of the reply after a whole-word leading phrase ("no" does not match "not sure"), else None."""
    for phrase in sorted(phrases, key=len, reverse=True):
        if text == phrase or re.match(re.escape(phrase) + r"\b", text):
            return text[len(phrase):]
    return None


def _only_reassurance(rest: str) -> bool:
    return all(w in _SAFE_REST_WORDS for w in _words(rest))


def interpret_by_rules(attempt: int, reply: str) -> str:
    """Deterministic verdict. Help words win; silence or ambiguity is never 'safe'.

    A reply is only 'safe' when it starts with a clear safe/no phrase and the
    rest is only reassurance (see _SAFE_REST_WORDS); anything else is 'unclear'.
    """
    text = reply.strip().lower()
    if not text:
        return "unclear"
    if any(word in text for word in _HELP):
        return "help"
    words = _words(text)
    if attempt >= 2:
        rest = _after_phrase(text, _NO_START)
        if rest is not None:
            return "safe" if _only_reassurance(rest) else "unclear"
        if words and (words[0] in _YES_WORDS or text.startswith("do it")):
            return "help"
        return "unclear"
    rest = _after_phrase(text, _SAFE)
    if rest is not None and _only_reassurance(rest):
        return "safe"
    return "unclear"


def question_for(event: Event, attempt: int) -> PendingConfirmation:
    if attempt not in QUESTIONS:
        raise ValueError(f"no confirmation question for attempt {attempt}")
    return PendingConfirmation(
        event_id=event.event_id,
        question=QUESTIONS[attempt],
        attempt=attempt,
        timeout_seconds=CONFIRMATION_TIMEOUT_S,
        max_attempts=MAX_ATTEMPTS,
    )


def interpret(event: Event, attempt: int, reply: str, interpreter: ReplyInterpreter | None = None) -> ConfirmationReply:
    """Model verdict if valid, otherwise rules. A model may not turn an
    obvious help request into 'safe'."""
    rule_verdict = interpret_by_rules(attempt, reply)
    verdict, by = rule_verdict, "rules"
    if interpreter is not None:
        try:
            proposal = interpreter({"reply": reply, "attempt": attempt})
            proposed = proposal.get("verdict") if isinstance(proposal, Mapping) else None
        except Exception:
            proposed = None
        if proposed in VERDICTS and not (rule_verdict == "help" and proposed == "safe"):
            verdict, by = proposed, "llm"
        else:
            by = "rules (llm fallback)"
    return ConfirmationReply(event.event_id, attempt, reply, verdict, by)
