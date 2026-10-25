"""Coordinator-selected sensor and user-goal paths for shared domains."""

from __future__ import annotations

from datetime import datetime, timezone
from operator import add
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from domains.base import DomainHandler, DomainRegistry, supports_confirmation
from models import (
    ActionRequest, ActionResult, AuditEntry, ConfirmationReply, Event, GoalInterpretation,
    NotificationRequest, NotificationResult, PendingConfirmation, RiskAssessment, WorkflowResult,
)
from services.goals import GoalInterpreter
from services.notifications import NotificationService
from tools.device import DeviceTool

from .automation import DeviceAutomationAgent
from .coordinator import HomeCoordinatorAgent
from .monitoring import MonitoringAgent


class WorkflowState(TypedDict, total=False):
    event: Event
    domain: str
    route_kind: str
    goal: GoalInterpretation | None
    assessment: RiskAssessment
    action_requests: tuple[ActionRequest, ...]
    action_results: tuple[ActionResult, ...]
    notification_request: NotificationRequest | None
    notification_result: NotificationResult | None
    trace: Annotated[list[AuditEntry], add]
    # Resident confirmation (UC-01 steps 5-6). Set by the pause/confirm nodes.
    pending_confirmation: PendingConfirmation | None
    confirmation_replies: tuple[ConfirmationReply, ...]
    resume_reply: str | None
    resuming: bool
    confirm_next: str


def _audit(event_id: str, agent: str, outcome: str) -> AuditEntry:
    return AuditEntry(event_id, agent, outcome, datetime.now(timezone.utc).isoformat())


class SmartHomeWorkflow:
    """Construct once, then call ``run`` for each UI or simulated event."""

    def __init__(
        self,
        handlers: list[DomainHandler],
        device_tool: DeviceTool,
        notifier: NotificationService | None = None,
        goal_interpreter: GoalInterpreter | None = None,
    ) -> None:
        registry = DomainRegistry(handlers)
        coordinator = HomeCoordinatorAgent(registry, notifier, goal_interpreter)
        self._coordinator = coordinator
        monitoring = MonitoringAgent(registry)
        automation = DeviceAutomationAgent(device_tool)

        def route(state: WorkflowState) -> dict:
            event = state["event"]
            if state.get("resuming"):
                return {"route_kind": "confirm",
                        "trace": [_audit(event.event_id, "HomeCoordinatorAgent", "resumed_confirmation")]}
            if event.event_type == "user_goal":
                goal = coordinator.route_goal(event)
                return {
                    "domain": goal.domain,
                    "route_kind": "clarify" if goal.clarification_question else "goal",
                    "goal": goal,
                    "trace": [_audit(
                        event.event_id, "HomeCoordinatorAgent",
                        "clarification_required" if goal.clarification_question else f"routed_goal:{goal.domain}:{goal.intent}",
                    )],
                }
            domain = coordinator.route(event)
            return {
                "domain": domain, "route_kind": "sensor",
                "trace": [_audit(event.event_id, "HomeCoordinatorAgent", f"routed_sensor:{domain}")],
            }

        def assess(state: WorkflowState) -> dict:
            event = state["event"]
            decision = monitoring.assess(event, state["domain"])
            return {
                "assessment": decision.assessment,
                "action_requests": decision.actions,
                "notification_request": decision.notification_request,
                "trace": [_audit(event.event_id, "MonitoringAgent", f"assessed:{decision.assessment.risk_level}")],
            }

        def needs_confirmation(state: WorkflowState) -> bool:
            handler = registry.resolve(state["event"])
            return bool(state["assessment"].requires_human_review) and supports_confirmation(handler)

        def pause(state: WorkflowState) -> dict:
            """Ask the resident and stop; ``resume`` continues the same event."""
            event = state["event"]
            attempt = len(state.get("confirmation_replies", ())) + 1
            pending = coordinator.ask_resident(event, state["assessment"], registry.resolve(event), attempt)
            return {
                "pending_confirmation": pending,
                "trace": [_audit(event.event_id, "HomeCoordinatorAgent", f"awaiting_confirmation:{attempt}")],
            }

        def confirm(state: WorkflowState) -> dict:
            """Interpret the reply; close, ask once more, or escalate."""
            event = state["event"]
            handler = registry.resolve(event)
            pending = state["pending_confirmation"]
            reply = coordinator.interpret_reply(event, handler, pending.attempt, state.get("resume_reply"))
            replies = tuple(state.get("confirmation_replies", ())) + (reply,)
            update = {
                "confirmation_replies": replies,
                "pending_confirmation": None,
                "resuming": False,
                "trace": [_audit(event.event_id, "HomeCoordinatorAgent", f"resident_reply:{reply.verdict}")],
            }
            if reply.verdict == "safe":
                update["confirm_next"] = "finish"
                return update
            if reply.verdict == "unclear" and pending.attempt < pending.max_attempts:
                update["confirm_next"] = "pause"
                return update
            decision = coordinator.escalate(event, state["assessment"], handler, replies)
            update.update({
                "assessment": decision.assessment,
                "action_requests": decision.actions,
                "notification_request": decision.notification_request,
                "confirm_next": "execute" if decision.actions else "notify",
                "trace": update["trace"] + [_audit(event.event_id, "HomeCoordinatorAgent", f"escalated:{reply.verdict}")],
            })
            return update

        def plan_goal(state: WorkflowState) -> dict:
            event = state["event"]
            goal = state["goal"]
            handler = registry.resolve_goal(goal)
            plan = automation.plan_goal(event, goal, handler)
            trace = [_audit(event.event_id, "DeviceAutomationAgent", f"planned:{len(plan.action_requests)}")]
            if plan.pending_confirmation is not None:
                trace.append(_audit(event.event_id, "HomeCoordinatorAgent", "awaiting_goal_confirmation"))
            return {
                "assessment": plan.assessment,
                "action_requests": plan.action_requests,
                "notification_request": plan.notification_request,
                "pending_confirmation": plan.pending_confirmation,
                "trace": trace,
            }

        def clarify(state: WorkflowState) -> dict:
            event = state["event"]
            goal = state["goal"]
            return {
                "assessment": RiskAssessment(
                    event_id=event.event_id, domain=goal.domain, risk_level="LOW",
                    rationale=goal.clarification_question, evidence=goal.evidence,
                ),
                "action_requests": (),
            }

        def execute(state: WorkflowState) -> dict:
            event = state["event"]
            results = automation.execute_plan(event, state["assessment"], state["action_requests"])
            trace = [
                _audit(event.event_id, "DeviceAutomationAgent", f"{result.device_id}:{'verified' if result.success else 'unverified'}")
                for result in results
            ]
            return {"action_results": results, "trace": trace}

        def notify(state: WorkflowState) -> dict:
            request = state.get("notification_request")
            if request is None:
                return {}
            result = coordinator.notify(request)
            return {
                "notification_result": result,
                "trace": [_audit(state["event"].event_id, "HomeCoordinatorAgent", f"notification:{result.status}")],
            }

        def finish(state: WorkflowState) -> dict:
            return {"trace": [_audit(state["event"].event_id, "HomeCoordinatorAgent", "result_ready")]}

        graph = StateGraph(WorkflowState)
        graph.add_node("route", route)
        graph.add_node("assess", assess)
        graph.add_node("plan_goal", plan_goal)
        graph.add_node("clarify", clarify)
        graph.add_node("execute", execute)
        graph.add_node("notify", notify)
        graph.add_node("finish", finish)
        graph.add_node("pause", pause)
        graph.add_node("confirm", confirm)
        graph.add_edge(START, "route")
        graph.add_conditional_edges(
            "route", lambda state: state["route_kind"],
            {"sensor": "assess", "goal": "plan_goal", "clarify": "clarify", "confirm": "confirm"},
        )
        graph.add_conditional_edges(
            "assess",
            lambda state: "pause" if needs_confirmation(state) else "execute" if state.get("action_requests") else "notify",
            {"pause": "pause", "execute": "execute", "notify": "notify"},
        )
        graph.add_edge("pause", END)
        graph.add_conditional_edges(
            "confirm", lambda state: state["confirm_next"],
            {"finish": "finish", "pause": "pause", "execute": "execute", "notify": "notify"},
        )
        graph.add_conditional_edges(
            "plan_goal",
            lambda state: "finish" if state.get("pending_confirmation") else "execute" if state.get("action_requests") else "notify",
            {"finish": "finish", "execute": "execute", "notify": "notify"},
        )
        graph.add_edge("execute", "notify")
        graph.add_edge("notify", "finish")
        graph.add_edge("clarify", "finish")
        graph.add_edge("finish", END)
        self.graph = graph.compile()

    def run(self, event: Event) -> WorkflowResult:
        return self._result(self.graph.invoke({"event": event, "trace": []}))

    def resume(self, result: WorkflowResult, reply: str | None) -> WorkflowResult:
        """Continue a workflow that is awaiting resident confirmation.

        ``reply`` is the resident's text; ``None`` means the confirmation
        timeout expired without a reply. Returns a new result; the earlier
        trace and replies are carried forward.
        """
        if result.pending_confirmation is None:
            raise ValueError("workflow is not awaiting confirmation")
        state = self.graph.invoke({
            "event": result.event, "domain": result.domain, "route_kind": "confirm",
            "assessment": result.assessment, "action_requests": (),
            "pending_confirmation": result.pending_confirmation,
            "confirmation_replies": result.confirmation_replies,
            "resume_reply": reply, "resuming": True,
            "trace": list(result.trace),
        })
        return self._result(state)

    def notify(self, request: NotificationRequest) -> NotificationResult:
        """Send a follow-up notification through HomeCoordinatorAgent.

        Used by escalation flows (e.g. Elderly Safety OR-04) that contact the
        next level after an acknowledgement timeout. Same validation and
        failure reporting as the graph's notify node; never raises for an
        adapter failure.
        """
        return self._coordinator.notify(request)

    @staticmethod
    def _result(state: WorkflowState) -> WorkflowResult:
        results = state.get("action_results", ())
        return WorkflowResult(
            event=state["event"], domain=state["domain"], assessment=state["assessment"],
            action_result=results[0] if results else None,
            notification_result=state.get("notification_result"),
            trace=tuple(state["trace"]),
            action_results=results,
            goal=state.get("goal"),
            pending_confirmation=state.get("pending_confirmation"),
            confirmation_replies=tuple(state.get("confirmation_replies", ())),
        )
