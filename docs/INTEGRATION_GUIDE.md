# Integrating a domain into the shared workflow

Start from the latest `main` after this framework has been reviewed and merged. Install dependencies from `requirements.txt`, then run `python -m simulation.framework_demo` and `python -m unittest discover -s tests -v` from the repository root. The demo is entirely simulated and does not require an API key.

## Scope of the current contract

The `DomainHandler.assess(event)` contract handles **sensor-event assessment**. The optional `GoalHandler.supports_goal(goal)` and `plan_goal(event, goal)` methods handle **direct user goals**. The coordinator selects the path at runtime; direct goals skip MonitoringAgent. Both paths can return several ordered `ActionRequest` values. All steps are checked before dispatch, each step is independently verified, and later steps are skipped after a failure. `WorkflowResult.action_results` and `outcome` show the result; `action_result` remains a first-action compatibility field.

The original offline interpreter in `simulation/goals.py` recognises only the exact fictional phrase "Good night" (or "我要睡觉了"). The implemented Smart Home Control path instead uses `services.smart_home_goals.SmartHomeGoalInterpreter`, which supports bilingual home-mode rules and optional structured campus proposals. It returns an event ID, domain, intent, parameters and evidence. `SmartHomeControlHandler` validates every untrusted proposal before returning a `GoalPlan`. Unknown or ambiguous goals return `clarification_question`; the coordinator then returns `CLARIFICATION_REQUIRED` without dispatching a device.

## Minimal handler

```python
from models import Event, MonitoringDecision, RiskAssessment

class MyDomainHandler:
    domain = "my_domain"

    def supports(self, event: Event) -> bool:
        return event.event_type == "my_event_type"

    def assess(self, event: Event) -> MonitoringDecision:
        # Replace with your tested domain rules. Do not execute a device here.
        return MonitoringDecision(RiskAssessment(
            event_id=event.event_id,
            domain=self.domain,
            risk_level="LOW",
            rationale="No action is needed under this example rule.",
            evidence="example input",
        ))
```

Register it once where the application is assembled:

```python
from agents.graph import SmartHomeWorkflow
from simulation.devices import SimulatedDeviceTool

workflow = SmartHomeWorkflow([MyDomainHandler()], SimulatedDeviceTool({}))
result = workflow.run(event)
print(result.to_dict())
```

Do not create a second coordinator, monitoring agent, or automation agent in your domain. Add an action request only when domain policy permits it and the target simulated device/expected readback are defined. An unsafe or uncertain outcome should set `requires_human_review=True`, which blocks dispatch in this baseline.

## Pausing for a resident reply

If your domain must ask the resident before acting (Elderly Safety MEDIUM falls), implement the three `ConfirmationHandler` methods in addition to `supports`/`assess`, and return `requires_human_review=True` from `assess`. `workflow.run(event)` then returns `outcome == "AWAITING_CONFIRMATION"` with the question in `result.pending_confirmation`; call `workflow.resume(result, reply)` with the resident's text, or `None` on timeout. See `domains/elderly_safety/handler.py` and `simulation/elderly_demo.py --reply ...`.

## Direct goals and multiple devices

Use `simulation.events.make_user_goal_event(text)` to create a simulated user request. Register a goal-capable domain handler and an interpreter with `SmartHomeWorkflow(handlers, device_tool, goal_interpreter=...)`. See `DemoNightModeHandler` and `run_goal_demo()` in `simulation/framework_demo.py` for a complete, offline two-device example. Real model output supplies a **proposal**, not device authorization. `plan_goal` must enforce the domain's allowed devices, actions and limits, then return `GoalPlan(assessment, action_requests=(...))`. Every action must include its expected returned state. A later action requiring human approval blocks the whole plan before the first command.

`NotificationRequest.message` should describe the detected condition or intended action; it must not claim that a device action succeeded before readback. The UI should use `WorkflowResult.outcome` and each `ActionResult` to report actual complete, partial or failed execution.

## How Jinjing's existing Pet Care code connects

`domains/pet_care/monitoring.py` already returns `PetAssessment`. A small adapter in that domain can call `assess_pet_event(event, proposal_provider)`, then map its `event_id`, `risk_level`, `rationale`, `evidence`, `policy_override`, and `fallback_used` to `RiskAssessment(domain="pet_care", ...)`. Return `MonitoringDecision(assessment=...)`; current Pet Care has no automatic feeder action and should not invent one. The adapter's `supports` should claim only `pet_bowl_level` and `pet_inactivity`. Keep the existing Pet Care tests and add one graph integration test once that branch is synchronized. No Pet Care source is copied into this framework branch.

## Ownership and merge sequence

| Owner | First integration point | Keep in owner branch |
| --- | --- | --- |
| Yuanbo Zhang | Review/extend `agents/graph.py`, add elderly-safety handler | Elderly thresholds and response rules |
| Yang Yang | Implement `DeviceTool` adapter and campus `GoalInterpreter` | Device actions, readback, model errors/timeouts |
| Jinjing Huang | Keep `Event`/sensor contracts and add Pet Care handler | Pet monitoring and fictional pet scenarios |
| Yan Li (Flora) | Implement `NotificationService` adapter and security handler | Contacts, security rules, delivery outcomes |
| Tianzhuo Li | Implement energy/comfort handler and context | Temperature, preference and energy policy |

The team should choose a UI integration owner. For either path, the UI calls `workflow.run(event)` and displays `WorkflowResult`; it does not duplicate rule logic. Each owner adds tests for their normal and failure paths and a fictional demo event. Merge the framework first, then synchronize named branches from `main`, integrate one domain at a time, and resolve contract changes through reviewed PRs. Keep Jira task dates and evidence aligned with actual work.

## Stage 2 deploy rehearsal

Before Canvas submission, copy the submitted source into a clean directory, install from the dependency file, set the API key only in local environment variables when real model access is needed, run tests, then launch the final UI from that downloaded source. The current baseline CLI confirms only framework wiring; it is not the finished Week 13 demonstration.
