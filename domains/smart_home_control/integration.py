"""Assemble, run and record the Smart Home Control workflow."""

from __future__ import annotations

import json
from pathlib import Path

from agents.graph import SmartHomeWorkflow
from models import Event, WorkflowResult
from services.smart_home_goals import GoalProposalProvider, SmartHomeGoalInterpreter
from simulation.devices import SimulatedDeviceTool

from .handler import SmartHomeControlHandler


DEFAULT_RECORD_PATH = Path("data/runtime/smart_home_control.jsonl")


def run_smart_home_control(
    event: Event,
    *,
    device_tool: SimulatedDeviceTool,
    proposal_provider: GoalProposalProvider | None = None,
    record_path: Path | None = DEFAULT_RECORD_PATH,
) -> WorkflowResult:
    """Run UC-02 through the shared agents and optionally append audit evidence."""

    workflow = SmartHomeWorkflow(
        [SmartHomeControlHandler()],
        device_tool,
        goal_interpreter=SmartHomeGoalInterpreter(proposal_provider),
    )
    result = workflow.run(event)
    if record_path is not None:
        record_path.parent.mkdir(parents=True, exist_ok=True)
        with record_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")
    return result
