"""Assemble, run and record the Smart Home Control workflow."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock

from agents.graph import SmartHomeWorkflow
from models import AuditEntry, Event, WorkflowResult
from services.smart_home_goals import GoalProposalProvider, SmartHomeGoalInterpreter
from simulation.devices import SimulatedDeviceTool

from .handler import SmartHomeControlHandler
from .modes import HomeModeState


DEFAULT_RECORD_PATH = Path("data/runtime/smart_home_control.jsonl")
_CONSUMED_CONFIRMATIONS: set[str] = set()
_CONFIRMATION_LOCK = Lock()


def _append_record(result: WorkflowResult, record_path: Path | None) -> None:
    if record_path is None:
        return
    record_path.parent.mkdir(parents=True, exist_ok=True)
    with record_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")


def _claim_confirmation(result: WorkflowResult) -> None:
    """Consume one sensitive-action confirmation exactly once per process."""

    pending = result.pending_confirmation
    if pending is None:
        raise ValueError("Smart Home Control result is not awaiting confirmation")
    if pending.event_id != result.event.event_id or result.goal is None or result.goal.event_id != result.event.event_id:
        raise ValueError("confirmation result has inconsistent event IDs")
    with _CONFIRMATION_LOCK:
        if pending.event_id in _CONSUMED_CONFIRMATIONS:
            raise ValueError("Smart Home Control confirmation has already been handled")
        _CONSUMED_CONFIRMATIONS.add(pending.event_id)


def run_smart_home_control(
    event: Event,
    *,
    device_tool: SimulatedDeviceTool,
    proposal_provider: GoalProposalProvider | None = None,
    mode_state: HomeModeState | None = None,
    record_path: Path | None = DEFAULT_RECORD_PATH,
) -> WorkflowResult:
    """Run UC-02 through the shared agents and optionally append audit evidence."""

    if mode_state is not None:
        event = mode_state.enrich_event(event)
    workflow = SmartHomeWorkflow(
        [SmartHomeControlHandler()],
        device_tool,
        goal_interpreter=SmartHomeGoalInterpreter(proposal_provider),
    )
    result = workflow.run(event)
    if mode_state is not None:
        mode_state.update_from_result(result)
    _append_record(result, record_path)
    return result


def resume_smart_home_confirmation(
    result: WorkflowResult,
    *,
    approved: bool,
    device_tool: SimulatedDeviceTool,
    mode_state: HomeModeState | None = None,
    record_path: Path | None = DEFAULT_RECORD_PATH,
) -> WorkflowResult:
    """Resume one paused sensitive goal from an explicit UI approval decision."""

    if result.pending_confirmation is None or result.goal is None:
        raise ValueError("Smart Home Control result is not awaiting confirmation")
    if result.goal.domain != "smart_home_control":
        raise ValueError("confirmation result belongs to another domain")
    _claim_confirmation(result)

    resumed_event = result.event
    if mode_state is not None:
        resumed_event = mode_state.enrich_event(resumed_event)
    original_goal = result.goal

    class ConfirmedGoalInterpreter:
        def interpret(self, event: Event):
            return replace(
                original_goal,
                event_id=event.event_id,
                evidence=f"{original_goal.evidence}; explicit in-app confirmation decision",
            )

    workflow = SmartHomeWorkflow(
        [SmartHomeControlHandler(
            confirmation_decision="approved" if approved else "declined",
            confirmed_event_id=result.event.event_id,
        )],
        device_tool,
        goal_interpreter=ConfirmedGoalInterpreter(),
    )
    resumed = workflow.run(resumed_event)
    if mode_state is not None:
        mode_state.update_from_result(resumed)
    decision_entry = AuditEntry(
        event_id=result.event.event_id,
        agent="HomeCoordinatorAgent",
        outcome="sensitive_action_approved" if approved else "sensitive_action_declined",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    combined = replace(resumed, trace=result.trace + (decision_entry,) + resumed.trace)
    _append_record(combined, record_path)
    return combined
