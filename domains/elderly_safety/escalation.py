"""Multi-level emergency escalation for falls (OR-04, SCRUM-25; UC-01 step 9, extension 6).

After the first caregiver alert, the event waits for an acknowledgement.

    acknowledged within ACK_TIMEOUT_S          -> RESOLVED
    no acknowledgement, or the send failed     -> contact the next level
    last contact also not acknowledged         -> inform the Human Operator,
                                                  ESCALATION_FAILED; the event
                                                  stays open until the operator
                                                  closes it

All contacts are fictional and labelled simulated. A sent or simulated
notification is never treated as acknowledged; only an explicit
acknowledgement (from the adapter or the simulated button) is.

`EscalationState` is immutable; every step returns a new state. The graph
does not run timers; the UI or simulation decides when a timeout passed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Callable, Literal

from models import NotificationRequest, NotificationResult, WorkflowResult

ACK_TIMEOUT_S = 60

# (level label, fictional recipient reference). Level 1 is the alert the
# shared workflow already sent; later levels are sent by this module.
CONTACT_LEVELS: tuple[tuple[str, str], ...] = (
    ("primary caregiver", "fictional-primary-caregiver"),
    ("secondary contact", "fictional-family-member"),
)
OPERATOR_REF = "fictional-human-operator"

Status = Literal["AWAITING_ACK", "RESOLVED", "ESCALATION_FAILED", "CLOSED_BY_OPERATOR"]
SEND_FAILED = ("FAILED", "UNAVAILABLE")

Notify = Callable[[NotificationRequest], NotificationResult]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ContactAttempt:
    level: int
    role: str
    recipient_ref: str
    send_status: str
    detail: str
    acknowledged: bool = False
    outcome: str = "awaiting_ack"  # awaiting_ack | acknowledged | ack_timeout | send_failed | operator_informed
    sent_at: str = field(default_factory=_now)


@dataclass(frozen=True)
class EscalationState:
    event_id: str
    status: Status
    attempts: tuple[ContactAttempt, ...]
    ack_timeout_seconds: int = ACK_TIMEOUT_S
    log: tuple[str, ...] = ()
    simulated: bool = True

    @property
    def current(self) -> ContactAttempt | None:
        return self.attempts[-1] if self.attempts else None

    @property
    def is_open(self) -> bool:
        return self.status in ("AWAITING_ACK", "ESCALATION_FAILED")

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "is_open": self.is_open}


def _with_last(state: EscalationState, **changes: Any) -> tuple[ContactAttempt, ...]:
    return state.attempts[:-1] + (replace(state.attempts[-1], **changes),)


def start(result: WorkflowResult) -> EscalationState | None:
    """Begin tracking after the workflow sent the level-1 alert.

    Returns None when no caregiver alert was sent (safe reply, LOW event, or
    still awaiting the resident), because there is nothing to acknowledge.
    """
    n = result.notification_result
    if n is None or result.pending_confirmation is not None:
        return None
    role, ref = CONTACT_LEVELS[0]
    first = ContactAttempt(1, role, ref, n.status, n.detail, acknowledged=n.acknowledged,
                           outcome="acknowledged" if n.acknowledged else "awaiting_ack")
    state = EscalationState(result.event.event_id, "RESOLVED" if n.acknowledged else "AWAITING_ACK", (first,),
                            simulated=result.event.simulated, log=(f"level 1 {role}: {n.status}",))
    return state


def needs_next_level_now(state: EscalationState) -> bool:
    """A failed send does not need to wait for the acknowledgement timeout."""
    return state.status == "AWAITING_ACK" and state.current is not None and state.current.send_status in SEND_FAILED


def acknowledge(state: EscalationState) -> EscalationState:
    """The current contact acknowledged the alert."""
    if state.status != "AWAITING_ACK":
        raise ValueError(f"no acknowledgement is expected in status {state.status}")
    if state.current.send_status in SEND_FAILED:
        raise ValueError("a contact whose alert failed to send cannot acknowledge it")
    return replace(
        state, status="RESOLVED",
        attempts=_with_last(state, acknowledged=True, outcome="acknowledged"),
        log=state.log + (f"level {state.current.level} {state.current.role}: acknowledged",),
    )


def _message(level: int, role: str, previous: ContactAttempt) -> str:
    why = "failed to send" if previous.send_status in SEND_FAILED else f"was not acknowledged within {ACK_TIMEOUT_S} s"
    return (f"Possible fall needing help (escalation level {level}, {role}). "
            f"The alert to the {previous.role} {why}.")


def advance(state: EscalationState, notify: Notify) -> EscalationState:
    """Acknowledgement timeout (or failed send) on the current level: move on.

    Sends the next contact's alert through ``notify``. After the last contact,
    informs the Human Operator and keeps the event open.
    """
    if state.status != "AWAITING_ACK":
        raise ValueError(f"cannot escalate in status {state.status}")
    previous = state.current
    closed_outcome = "send_failed" if previous.send_status in SEND_FAILED else "ack_timeout"
    attempts = _with_last(state, outcome=closed_outcome)
    log = state.log + (f"level {previous.level} {previous.role}: {closed_outcome}",)

    next_level = previous.level + 1
    if next_level <= len(CONTACT_LEVELS):
        role, ref = CONTACT_LEVELS[next_level - 1]
        result = notify(NotificationRequest(state.event_id, ref, _message(next_level, role, previous), state.simulated))
        attempt = ContactAttempt(next_level, role, ref, result.status, result.detail, acknowledged=result.acknowledged,
                                 outcome="acknowledged" if result.acknowledged else "awaiting_ack")
        return replace(state, status="RESOLVED" if result.acknowledged else "AWAITING_ACK",
                       attempts=attempts + (attempt,), log=log + (f"level {next_level} {role}: {result.status}",))

    # No more contacts: inform the operator; the event stays open (UC-01 extension 6).
    message = (f"Escalation failed: no configured contact acknowledged a possible fall "
               f"after {len(CONTACT_LEVELS)} levels. Event remains open.")
    result = notify(NotificationRequest(state.event_id, OPERATOR_REF, message, state.simulated))
    operator = ContactAttempt(next_level, "human operator", OPERATOR_REF, result.status, result.detail,
                              acknowledged=False, outcome="operator_informed")
    return replace(state, status="ESCALATION_FAILED", attempts=attempts + (operator,),
                   log=log + (f"human operator informed: {result.status}",))


def operator_close(state: EscalationState, note: str = "") -> EscalationState:
    """Only the Human Operator closes an event whose escalation failed."""
    if state.status != "ESCALATION_FAILED":
        raise ValueError("only a failed escalation is closed by the operator")
    entry = "closed by human operator" + (f": {note}" if note else "")
    return replace(state, status="CLOSED_BY_OPERATOR", log=state.log + (entry,))
