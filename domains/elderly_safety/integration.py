"""Run and resume Elderly Safety through the shared graph, with a local audit record.

Same pattern as Smart Home Control: the UI calls these two functions and
never touches rules, devices or notifications directly. Every run and every
resume appends the full `WorkflowResult` to a git-ignored JSONL file.
"""

from __future__ import annotations

import json
from pathlib import Path

from agents.graph import SmartHomeWorkflow
from models import Event, WorkflowResult
from services.notifications import NotificationService
from simulation.notifications import SimulatedNotificationService
from tools.device import DeviceTool

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

