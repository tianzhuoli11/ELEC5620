"""Session-local safety evidence derived from completed domain workflows."""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from threading import RLock

from models import WorkflowResult

REQUIRED_DOMAINS = ("elderly_safety", "home_security")
MAX_AGE_SECONDS = 300


@dataclass(frozen=True)
class SafetySignal:
    domain: str
    event_id: str
    state: str
    observed_at: datetime
    expires_at: datetime
    detail: str


class SafetyState:
    """Missing, stale, pending or unsafe evidence blocks comfort control.

    Independent warning IDs remain active until their validated expiry; an
    unrelated LOW warning cannot clear a previous emergency warning.
    """
    def __init__(self):
        self._signals = {}
        self._lock = RLock()

    def invalidate(self, domain):
        with self._lock:
            self._signals.pop(domain, None)

    def observe(self, result: WorkflowResult):
        if not isinstance(result, WorkflowResult) or result.domain not in REQUIRED_DOMAINS:
            raise ValueError("Safety evidence must be an Elderly Safety or Home Security workflow")
        event = result.event
        if result.assessment.event_id != event.event_id or result.assessment.domain != result.domain:
            raise ValueError("Safety assessment must belong to the same domain and event")
        if event.event_type == "simulated_external_warning":
            # Reuse the domain validator; never trust a supplied risk label alone.
            from domains.home_security.external_warnings import assess_external_warning
            warning = assess_external_warning(event)
            if not warning.valid or not warning.relevant:
                return
            raw = event.context["warning"]
            key = "external:" + raw["warning_id"]
            expiry = datetime.fromisoformat(raw["expires_at"].replace("Z", "+00:00"))
            state, detail = "BLOCKED", "Active relevant external warning"
        else:
            key = result.domain
            expiry = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00")) + timedelta(seconds=MAX_AGE_SECONDS)
            safe_reply = bool(result.confirmation_replies and result.confirmation_replies[-1].verdict == "safe")
            clear = (result.outcome == "ASSESSED" and result.pending_confirmation is None
                     and (result.assessment.risk_level == "LOW" or (result.domain == "elderly_safety" and safe_reply)))
            state = "CLEAR" if clear and event.simulated is True else "BLOCKED"
            detail = "Fresh domain assessment found no active hazard" if state == "CLEAR" else "Hazard, pending confirmation or unresolved response"
        observed = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
        if observed.tzinfo is None or expiry.tzinfo is None:
            raise ValueError("Safety timestamps require a time zone")
        signal = SafetySignal(result.domain, event.event_id, state, observed, expiry, detail)
        with self._lock:
            previous = self._signals.get(key)
            if previous is None or observed >= previous.observed_at:
                self._signals[key] = signal

    def snapshot(self, *, now=None):
        now = now or datetime.now(timezone.utc)
        reasons = []
        with self._lock:
            signals = dict(self._signals)
        for domain in REQUIRED_DOMAINS:
            signal = signals.get(domain)
            if signal is None:
                reasons.append(domain + ": no current assessment")
            elif signal.observed_at > now or signal.expires_at <= now:
                reasons.append(domain + ": stale or future-dated evidence")
            elif signal.state != "CLEAR":
                reasons.append(domain + ": " + signal.detail)
        for key, signal in signals.items():
            if key.startswith("external:") and signal.expires_at > now:
                reasons.append(key + ": active external warning")
        return {"clear": not reasons, "reasons": reasons,
                "signals": [{**asdict(s), "observed_at": s.observed_at.isoformat(), "expires_at": s.expires_at.isoformat()} for s in signals.values()]}
