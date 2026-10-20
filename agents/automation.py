"""Dispatch an authorised action and verify observed state separately."""

from __future__ import annotations

from models import ActionRequest, ActionResult, Event, GoalInterpretation, GoalPlan, RiskAssessment
from tools.device import DeviceTool


class DeviceAutomationAgent:
    def __init__(self, tool: DeviceTool) -> None:
        self.tool = tool

    def execute(self, event: Event, assessment: RiskAssessment, request: ActionRequest) -> ActionResult:
        def rejected(reason: str, *, accepted: bool = False, state: dict | None = None) -> ActionResult:
            return ActionResult(
                event_id=event.event_id, device_id=request.device_id, action=request.action,
                accepted=accepted, verified=False, returned_state=state or {},
                error=reason, simulated=request.simulated,
            )

        if request.event_id != event.event_id:
            return rejected("Action request event ID mismatch")
        if request.simulated != event.simulated:
            return rejected("Action simulation flag does not match the event")
        if assessment.requires_human_review or request.authorization == "HUMAN":
            return rejected("Human review required; approval workflow is not connected")
        try:
            dispatch = self.tool.dispatch(request)
        except Exception as exc:
            return rejected(f"Device dispatch failed: {type(exc).__name__}")
        if not dispatch.accepted:
            return rejected(dispatch.error or "Device command was rejected")
        try:
            observed = self.tool.read_state(request.device_id)
        except Exception as exc:
            return rejected(f"Device state verification failed: {type(exc).__name__}", accepted=True)
        verified = all(observed.get(key) == value for key, value in request.expected_state.items())
        return ActionResult(
            event_id=event.event_id, device_id=request.device_id, action=request.action,
            accepted=True, verified=verified, returned_state=dict(observed),
            error=None if verified else "Returned device state did not match the expected state",
            simulated=request.simulated,
        )

    def plan_goal(self, event: Event, goal: GoalInterpretation, handler: object) -> GoalPlan:
        plan = handler.plan_goal(event, goal)
        if plan.assessment.event_id != event.event_id or plan.assessment.domain != goal.domain:
            raise ValueError("goal plan must preserve the event ID and domain")
        if plan.notification_request and plan.notification_request.event_id != event.event_id:
            raise ValueError("notification request must preserve the event ID")
        return plan

    def execute_plan(
        self, event: Event, assessment: RiskAssessment, requests: tuple[ActionRequest, ...]
    ) -> tuple[ActionResult, ...]:
        """Validate the entire plan before dispatch, then stop after a failed step."""
        if not requests:
            return ()

        reason = None
        if any(request.event_id != event.event_id for request in requests):
            reason = "Action request event ID mismatch"
        elif any(request.simulated != event.simulated for request in requests):
            reason = "Action simulation flag does not match the event"
        elif assessment.requires_human_review or any(request.authorization == "HUMAN" for request in requests):
            reason = "Human review required; approval workflow is not connected"

        if reason:
            return tuple(ActionResult(
                event_id=event.event_id, device_id=request.device_id, action=request.action,
                accepted=False, verified=False, error=reason, simulated=request.simulated,
            ) for request in requests)

        results = []
        failed = False
        for request in requests:
            if failed:
                result = ActionResult(
                    event_id=event.event_id, device_id=request.device_id, action=request.action,
                    accepted=False, verified=False, error="Skipped after a prior action failed",
                    simulated=request.simulated,
                )
            else:
                result = self.execute(event, assessment, request)
                failed = not result.success
            results.append(result)
        return tuple(results)
