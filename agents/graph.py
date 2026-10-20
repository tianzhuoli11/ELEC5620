"""Coordinator-selected sensor and user-goal paths for shared domains."""

from __future__ import annotations

from datetime import datetime, timezone
from operator import add
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from domains.base import DomainHandler, DomainRegistry
from models import (
    ActionRequest, ActionResult, AuditEntry, Event, GoalInterpretation,
    NotificationRequest, NotificationResult, RiskAssessment, WorkflowResult,
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
        monitoring = MonitoringAgent(registry)
        automation = DeviceAutomationAgent(device_tool)

        def route(state: WorkflowState) -> dict:
            event = state["event"]
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

        def plan_goal(state: WorkflowState) -> dict:
            event = state["event"]
            goal = state["goal"]
            handler = registry.resolve_goal(goal)
            plan = automation.plan_goal(event, goal, handler)
            return {
                "assessment": plan.assessment,
                "action_requests": plan.action_requests,
                "notification_request": plan.notification_request,
                "trace": [_audit(event.event_id, "DeviceAutomationAgent", f"planned:{len(plan.action_requests)}")],
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
        graph.add_edge(START, "route")
        graph.add_conditional_edges(
            "route", lambda state: state["route_kind"],
            {"sensor": "assess", "goal": "plan_goal", "clarify": "clarify"},
        )
        graph.add_conditional_edges(
            "assess", lambda state: "execute" if state.get("action_requests") else "notify",
            {"execute": "execute", "notify": "notify"},
        )
        graph.add_conditional_edges(
            "plan_goal", lambda state: "execute" if state.get("action_requests") else "notify",
            {"execute": "execute", "notify": "notify"},
        )
        graph.add_edge("execute", "notify")
        graph.add_edge("notify", "finish")
        graph.add_edge("clarify", "finish")
        graph.add_edge("finish", END)
        self.graph = graph.compile()

    def run(self, event: Event) -> WorkflowResult:
        state = self.graph.invoke({"event": event, "trace": []})
        results = state.get("action_results", ())
        return WorkflowResult(
            event=event, domain=state["domain"], assessment=state["assessment"],
            action_result=results[0] if results else None,
            notification_result=state.get("notification_result"),
            trace=tuple(state["trace"]),
            action_results=results,
            goal=state.get("goal"),
        )
