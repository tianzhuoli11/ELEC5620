"""Optional OR-01 feeder policy and a fictional, single-use device adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from models import ActionRequest, Event
from tools.device import DispatchResult

from .monitoring import EMPTY_BOWL_PERCENT


FEEDER_ID = "pet-feeder"
MAX_PORTION_GRAMS = 50


@dataclass(frozen=True)
class FeedingDecision:
    status: str
    detail: str
    portion_grams: int | None = None


class SimulatedPetFeederTool:
    """One simulated dispense per event; readback is independent of acceptance."""

    def __init__(self, *, available: bool = True, stale_readback: bool = False) -> None:
        self.available = available
        self.stale_readback = stale_readback
        self.dispatch_count = 0
        self._processed_events: set[str] = set()
        self._state: dict[str, Any] = {
            "available": available,
            "last_event_id": None,
            "last_dispensed_g": 0,
            "dispense_count": 0,
        }

    def dispatch(self, request: ActionRequest) -> DispatchResult:
        self.dispatch_count += 1
        if not request.simulated or request.device_id != FEEDER_ID or request.action != "dispense":
            return DispatchResult(False, "Only the simulated pet-feeder dispense action is supported")
        if not self.available:
            return DispatchResult(False, "Simulated pet feeder is unavailable")
        if request.event_id in self._processed_events:
            return DispatchResult(False, "This event has already requested a feed; no repeat dispensing")
        portion = request.parameters.get("portion_grams")
        if (set(request.parameters) != {"portion_grams"} or isinstance(portion, bool)
                or not isinstance(portion, int) or not 1 <= portion <= MAX_PORTION_GRAMS):
            return DispatchResult(False, "Invalid simulated feed portion")
        self._processed_events.add(request.event_id)
        self._state.update({
            "last_event_id": request.event_id,
            "last_dispensed_g": portion,
            "dispense_count": self._state["dispense_count"] + 1,
        })
        return DispatchResult(True)

    def read_state(self, device_id: str) -> dict[str, Any]:
        if device_id != FEEDER_ID:
            raise KeyError("Unknown simulated device")
        if not self.available:
            raise ConnectionError("Simulated pet feeder is unavailable")
        state = dict(self._state)
        if self.stale_readback and state["dispense_count"]:
            state.update(last_event_id=None, last_dispensed_g=0)
        return state


def evaluate_feeding_goal(
    event: Event,
    goal: Mapping[str, Any] | None,
    *,
    enabled: bool,
    feeder: SimulatedPetFeederTool | None,
) -> FeedingDecision:
    """Require an explicit bounded goal, low bowl and available feeder."""

    if goal is None:
        return FeedingDecision("NOT_REQUESTED", "No optional feeding goal was requested")
    if not enabled:
        return FeedingDecision("DISABLED", "Optional feeding is disabled; monitoring and notification continue")
    if not isinstance(goal, Mapping) or set(goal) != {"portion_grams"}:
        return FeedingDecision("REJECTED", "A feeding goal must contain only portion_grams")
    portion = goal["portion_grams"]
    if isinstance(portion, bool) or not isinstance(portion, int) or not 1 <= portion <= MAX_PORTION_GRAMS:
        return FeedingDecision("REJECTED", "A feeding portion must be an integer from 1 to 50 grams")
    if not event.simulated or event.event_type != "pet_bowl_level":
        return FeedingDecision("REJECTED", "Optional feeding requires a simulated bowl-level event")
    readings = [r for r in event.readings if r.reading_type == "food_level_percent" and r.unit == "%"]
    if len(readings) != 1 or isinstance(readings[0].value, bool) or not isinstance(readings[0].value, (int, float)):
        return FeedingDecision("REJECTED", "A valid bowl reading is required before feeding")
    if not 0 <= readings[0].value <= EMPTY_BOWL_PERCENT:
        return FeedingDecision("REJECTED", "The bowl is above the feeding review threshold")
    if feeder is None:
        return FeedingDecision("UNAVAILABLE", "No simulated pet feeder is connected")
    try:
        state = feeder.read_state(FEEDER_ID)
    except (ConnectionError, KeyError):
        return FeedingDecision("UNAVAILABLE", "The simulated pet feeder is unavailable")
    if state.get("available") is not True:
        return FeedingDecision("UNAVAILABLE", "The simulated pet feeder is unavailable")
    return FeedingDecision("READY", "Optional simulated feeding goal passed policy checks", portion)
