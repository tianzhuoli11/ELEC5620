"""Original Sprint 0 assessment-only recording; shared workflow lives in integration.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from models import Event

from .monitoring import PetAssessment, assess_pet_event


def monitor_pet_event(
    event: Event,
    *,
    record_path: str | Path,
    proposal_provider: Callable[[Event], Mapping[str, Any]] | None = None,
) -> PetAssessment:
    """Assess and persist an event before returning its result.

    This remains the assessment-only entry point for older tests and fixtures.
    New UI and CLI flows use ``integration.monitor_pet_workflow``.
    Persistence errors are surfaced; callers must not report an unrecorded
    assessment as a completed monitoring flow.
    """

    assessment = assess_pet_event(event, proposal_provider)
    path = Path(record_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "event": event.to_dict(),
        "assessment": assessment.to_dict(),
        "record_type": "pet_monitoring",
    }
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
    return assessment
