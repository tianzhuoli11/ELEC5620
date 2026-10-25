"""Run and resume Elderly Safety through the shared graph, with a local audit record.

Same pattern as Smart Home Control: the UI calls these functions and never
touches rules, devices or notifications directly. Every run, resume and
escalation step appends a record to a git-ignored JSONL file.
"""

from __future__ import annotations

import json
from pathlib import Path

from agents.graph import SmartHomeWorkflow
from models import Event, WorkflowResult
from services.notifications import NotificationService
from simulation.notifications import SimulatedNotificationService
from tools.device import DeviceTool

from . import escalation
from .assessment import FallProposalProvider
from .confirmation import ReplyInterpreter
from .handler import ElderlySafetyHandler

DEFAULT_RECORD_PATH = Path("data/runtime/elderly_safety.jsonl")


def _append_record(result: WorkflowResult, handler: ElderlySafetyHandler, record_path: Path | None) -> None:
    if record_path is None:
        return
    record = {"record_type": "elderly_safety", "workflow": result.to_dict()}
    if handler.fall_assessment is not None:
        record["fall_assessment"] = handler.fall_assessment.to_dict()
    path = Path(record_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")


def build_workflow(
    *,
    device_tool: DeviceTool,
    notifier: NotificationService | None = None,
    proposal_provider: FallProposalProvider | None = None,
    reply_interpreter: ReplyInterpreter | None = None,
) -> tuple[SmartHomeWorkflow, ElderlySafetyHandler]:
    handler = ElderlySafetyHandler(proposal_provider, reply_interpreter)
    workflow = SmartHomeWorkflow(
        [handler], device_tool,
        notifier=notifier if notifier is not None else SimulatedNotificationService(),
    )
    return workflow, handler


def run_elderly_safety(
    event: Event,
    *,
    workflow: SmartHomeWorkflow,
    handler: ElderlySafetyHandler,
    record_path: Path | None = DEFAULT_RECORD_PATH,
) -> WorkflowResult:
    result = workflow.run(event)
    _append_record(result, handler, record_path)
    return result


def resume_elderly_safety(
    result: WorkflowResult,
    reply: str | None,
    *,
    workflow: SmartHomeWorkflow,
    handler: ElderlySafetyHandler,
    record_path: Path | None = DEFAULT_RECORD_PATH,
) -> WorkflowResult:
    """``reply=None`` records that the 30 s confirmation timeout expired."""
    resumed = workflow.resume(result, reply)
    _append_record(resumed, handler, record_path)
    return resumed



# --- Multi-level escalation (OR-04, SCRUM-25) ---------------------------------

def _append_escalation(state: escalation.EscalationState, record_path: Path | None) -> None:
    if record_path is None:
        return
    path = Path(record_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        record = {"record_type": "elderly_escalation", "escalation": state.to_dict()}
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")


def _skip_failed_sends(state: escalation.EscalationState, workflow: SmartHomeWorkflow) -> escalation.EscalationState:
    """A contact whose alert could not be sent is skipped without waiting."""
    while escalation.needs_next_level_now(state):
        state = escalation.advance(state, workflow.notify)
    return state


def start_escalation(
    result: WorkflowResult,
    *,
    workflow: SmartHomeWorkflow,
    record_path: Path | None = DEFAULT_RECORD_PATH,
) -> escalation.EscalationState | None:
    """Begin acknowledgement tracking once the level-1 caregiver alert was sent."""
    state = escalation.start(result)
    if state is None:
        return None
    state = _skip_failed_sends(state, workflow)
    _append_escalation(state, record_path)
    return state


def acknowledge_alert(
    state: escalation.EscalationState,
    *,
    record_path: Path | None = DEFAULT_RECORD_PATH,
) -> escalation.EscalationState:
    state = escalation.acknowledge(state)
    _append_escalation(state, record_path)
    return state


def acknowledgement_timeout(
    state: escalation.EscalationState,
    *,
    workflow: SmartHomeWorkflow,
    record_path: Path | None = DEFAULT_RECORD_PATH,
) -> escalation.EscalationState:
    """The current contact did not acknowledge within ACK_TIMEOUT_S."""
    state = _skip_failed_sends(escalation.advance(state, workflow.notify), workflow)
    _append_escalation(state, record_path)
    return state


def operator_close_event(
    state: escalation.EscalationState,
    note: str = "",
    *,
    record_path: Path | None = DEFAULT_RECORD_PATH,
) -> escalation.EscalationState:
    state = escalation.operator_close(state, note)
    _append_escalation(state, record_path)
    return state
