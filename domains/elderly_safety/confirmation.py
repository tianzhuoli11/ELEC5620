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

# Help: any of these anywhere in the reply means help (over-inclusive on purpose:
# a false alert is acceptable, a missed request for help is not).
_HELP = ("help", "can't get up", "cant get up", "cannot get up", "can't move", "cant move", "cannot move",
         "can't stand", "cant stand", "cannot stand", "unable to", "not ok", "hurt", "pain", "bleeding", "blood",
         "broken", "breath", "chest", "hit my head", "call", "ambulance", "emergency", "dizzy", "faint", "stuck")

# Safe: only complete, explicitly listed replies (after normalisation) are safe.
# Partial matches - a safe start, a whitelist of single words, or a list of
# worrying words - were each shown to close the event for ambiguous replies
# ("No idea", "Okay, I am down") during the reply evaluation and the PR #26 review.
_FINE = ("i'm fine", "im fine", "i am fine", "i'm ok", "im ok", "i am ok", "i'm okay", "im okay", "i am okay",
         "i'm alright", "im alright", "i am alright", "fine", "ok", "okay", "alright", "all good")
_FINE_TAILS = ("", "thanks", "thank you", "i just sat down", "just sat down", "i sat down", "i just sat down to rest",
               "just resting", "i'm just resting", "im just resting", "just dropped a cup", "i just dropped a cup",
               "just dropped something", "i just dropped something", "false alarm", "nothing happened")
_NO = ("no", "nope", "no thanks", "no thank you", "not needed", "no need", "don't", "dont", "no it's fine", "no its fine")
_NO_TAILS = ("", "thanks", "thank you", "i'm fine", "im fine", "i am fine", "i'm ok", "i'm okay", "im okay", "i am okay",
             "i'm alright", "my son is already here", "my daughter is already here", "someone is already here")


def _combine(heads: tuple[str, ...], tails: tuple[str, ...]) -> frozenset[str]:
    return frozenset(f"{h} {t}".strip() for h in heads for t in tails)


SAFE_REPLIES = _combine(_FINE, _FINE_TAILS) | {"false alarm", "nothing happened"}
NO_REPLIES = _combine(_NO, _NO_TAILS)
_YES_WORDS = frozenset({"yes", "yeah", "yep", "please", "contact", "need", "come"})


def normalise(reply: str) -> str | None:
    """Lower case, curly quotes straightened, punctuation removed, spaces collapsed.

    Returns None when the reply contains anything the rules cannot read
    (non-English letters, digits, symbols): such a reply is never 'safe'.
    """
    text = reply.strip().lower().replace("\u2019", "'").replace("\u2018", "'")
    if re.search(r"[^a-z' .,!?;:\-\u2026]", text):
        return None
    return " ".join(re.sub(r"[.,!?;:\-\u2026]+", " ", text).split())


def interpret_by_rules(attempt: int, reply: str) -> str:
    """Deterministic verdict. Help words win; silence or ambiguity is never 'safe'.

    'safe' only for a complete reply in SAFE_REPLIES (question 1) or
    NO_REPLIES (question 2); anything not recognised is 'unclear'.
    """
    raw = reply.strip().lower()
    if not raw:
        return "unclear"
    if any(phrase in raw for phrase in _HELP):
        return "help"
    text = normalise(reply)
    if text is None:
        return "unclear"
    if attempt >= 2:
        if text in NO_REPLIES:
            return "safe"
        words = text.split()
        if words and (words[0] in _YES_WORDS or text.startswith("do it")):
            return "help"
        return "unclear"
    return "safe" if text in SAFE_REPLIES else "unclear"


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
