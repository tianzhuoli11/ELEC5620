"""Resident confirmation for suspected falls (UC-01 steps 5-6, SCRUM-24).

Questions, the deterministic reply interpreter and an optional model-backed
interpreter hook. The model only ever sees the reply text and the attempt
number (NFR-03); its verdict is validated and falls back to the rules.
"""

from __future__ import annotations

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

# "can't move", "not okay" and "faint" were added after the reply evaluation
# (simulation/elderly_reply_evaluation.py) showed "No, I can't move" being closed as safe.
_HELP = ("help", "can't get up", "cant get up", "cannot get up", "can't move", "cant move", "cannot move", "unable to",
         "not ok", "hurt", "pain", "bleeding", "call", "ambulance", "emergency", "dizzy", "faint", "stuck")
_SAFE = ("i'm ok", "im ok", "i am ok", "i'm fine", "im fine", "i am fine", "i'm okay", "im okay", "i am okay", "ok", "okay", "fine", "all good", "no help", "false alarm", "dropped", "nothing happened")
_YES = ("yes", "yeah", "yep", "please", "do it", "contact", "need")
_NO = ("no", "nope", "don't", "dont", "not needed", "no need", "no thanks")


def interpret_by_rules(attempt: int, reply: str) -> str:
    """Deterministic verdict. Help words win; silence or ambiguity is never 'safe'."""
    text = reply.strip().lower()
    if not text:
        return "unclear"
    if any(word in text for word in _HELP):
        return "help"
    if attempt >= 2:
        if any(text == w or text.startswith(w) for w in _YES):
            return "help"
        if any(text == w or text.startswith(w) for w in _NO):
            return "safe"
        return "unclear"
    if any(text == phrase or text.startswith(phrase) for phrase in _SAFE):
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
