# Shared Python contracts (baseline 2)

## Explanation request route (UC-06)

`models.ExplanationRequest(request_id, event_id, source_sha256, question, style="detailed")` identifies a specific stored decision stage. `HomeCoordinatorAgent.explain(request, record=..., proposal_provider=...)` returns `ExplanationResult` with source-referenced facts, evidence/AI status and review status. It is read-only and has no device dependency. `services.explanations.submit_explanation` persists the request/result; `review_explanation` appends an explicit local operator approval/rejection. Model callbacks receive anonymous fact categories and may return only `{"fact_ids": [...]}`; they cannot supply prose or human approval. See [EXPLANATIONS.md](EXPLANATIONS.md) for privacy, missing/conflicting records, simpler responses and historical stages.

These are the implemented interfaces in `models/`, `domains/base.py`, `tools/device.py`, `services/goals.py`, and `services/notifications.py`. Changes to public fields need a coordinated PR because every domain imports them.

SCRUM-22 adds a backward-compatible candidate module at `models/context.py`: `HomeEnvironment`, `UserPreference`, `EnergyProfile`, `HomeMode`, `DeviceObservation` and aggregate `HomeContext`. It does not change existing Event or workflow constructor fields. For `energy_comfort_observation`, temperature and occupancy are readings; preference, energy policy input, mode, devices and the matching simulation marker are stored under `Event.context["energy_comfort"]`. Unknown values remain `None`. This candidate has local implementation coverage but still requires M2/M4 and framework-owner review; no team approval is implied.

## Input and ownership

`Event(event_id, event_type, source, timestamp, context, simulated, readings)` has a timezone-aware ISO 8601 timestamp. `SensorReading(sensor_id, reading_type, value, unit, observed_at)` holds one observation. Event IDs must be preserved in every later message. `simulation.events.make_sensor_event(...)` creates a fresh simulated sensor event; `make_user_goal_event(text)` creates a direct simulated user request with `event_type="user_goal"` and `context["text"]`.

A domain exports a handler with `domain: str`, `supports(event) -> bool` and `assess(event) -> MonitoringDecision` for sensor events. A direct-goal handler additionally provides `supports_goal(goal) -> bool` and `plan_goal(event, goal) -> GoalPlan`. Exactly one handler must support an event or structured goal. Zero or multiple matches raise an error before any action. Register handlers with `SmartHomeWorkflow([handler_a, ...], device_tool, notifier=None, goal_interpreter=None)` and call `run(event)`.

`GoalInterpreter.interpret(event) -> GoalInterpretation(event_id, domain, intent, parameters, evidence, clarification_question)` is a shared service boundary. The coordinator uses it for user goals and validates the event ID and unique owning domain. If a clarification question is present, it returns that question without contacting a domain handler or device. Otherwise, `GoalPlan(assessment, action_requests, notification_request, pending_confirmation)` is returned by domain policy through DeviceAutomationAgent's planning step; MonitoringAgent is skipped. A goal plan may stop with a pending confirmation before dispatch. A model's interpretation is untrusted and cannot itself authorize an action.

## Monitoring decision

`MonitoringDecision` contains a required `RiskAssessment`, an optional legacy singular `action_request`, optional additional `action_requests`, and an optional `NotificationRequest`. `decision.actions` combines the action fields in execution order. New code may use `action_requests` alone.

- `RiskAssessment`: `event_id`, `domain`, `risk_level` (`LOW`/`MEDIUM`/`HIGH`), `rationale`, `evidence`, `policy_override`, `fallback_used`, `requires_human_review`.
- `ActionRequest`: `event_id`, `device_id`, `action`, `parameters`, nonempty `expected_state`, `authorization` (`POLICY`/`HUMAN`), `simulated`, plus optional `continue_on_failure` and bounded `max_attempts` execution-policy fields. Both policy fields default to the original stop-after-one-attempt behaviour.
- `NotificationRequest`: `event_id`, `recipient_ref`, `message`, `simulated`.

The domain must validate any LLM proposal against its deterministic policy before returning a decision. A string in `authorization` is metadata, not proof that a human approved anything. `requires_human_review=True` or `authorization="HUMAN"` prevents dispatch unless a domain-specific confirmation flow records an explicit decision and creates a new validated plan. Do not send physical-device actions until a separately reviewed authorization and device adapter exist.

## Execution result

`DeviceTool.dispatch(request) -> DispatchResult(accepted, error)` and `read_state(device_id) -> dict` are separate calls. `DeviceAutomationAgent` checks **all** action IDs, simulation flags and review requirements before any dispatch, then sends commands in order. It compares each `expected_state` key to the independently returned state. The default policy skips later commands after a failed step; a domain may explicitly request bounded retry and continuation for independent safe actions.

`ActionResult` records `accepted`, `verified`, `returned_state`, `error`, `simulated`, and `attempts`; `success` is true only if accepted **and** verified. A failed readback after accepted dispatch remains `accepted=True, verified=False`.

`NotificationService.send(request) -> NotificationResult` reports `SIMULATED`, `SENT`, `FAILED`, or `UNAVAILABLE` plus `acknowledged`. No adapter means `UNAVAILABLE`. Sending is not the same as recipient acknowledgement.

`WorkflowResult.to_dict()` supplies serializable event, assessment, `action_results`, first-action compatibility field `action_result`, optional `goal`, notification outcome, overall `outcome` (`ASSESSED`, `COMPLETE`, `PARTIAL`, `FAILED`, `CLARIFICATION_REQUIRED`, `AWAITING_CONFIRMATION`) and a timestamped agent trace. Smart Home Control and Pet Care persist their own domain evidence; the shared trace remains in-memory unless the integration records it.

## Resident confirmation (optional, additive)

A domain may also implement `ConfirmationHandler` (`domains/base.py`): `confirmation_question(event, assessment, attempt) -> PendingConfirmation`, `interpret_reply(event, attempt, reply) -> ConfirmationReply` and `escalate(event, assessment, replies) -> MonitoringDecision`. When such a handler returns `requires_human_review=True`, the graph stops after assessment with `WorkflowResult.pending_confirmation` set and `outcome == "AWAITING_CONFIRMATION"`; nothing is dispatched or sent. The UI or simulation calls `SmartHomeWorkflow.resume(result, reply)`; `reply=None` means the timeout expired. A `safe` verdict ends the event; `unclear` asks again up to `max_attempts`; `help`, a second `unclear` or a timeout call `escalate`, whose decision runs through the normal execute and notify steps. Silence is never treated as safe. `confirmation_replies` records every attempt. Domains without this protocol are unaffected (`requires_human_review` keeps blocking dispatch as before). The graph does not run timers; the caller decides when a timeout has passed.

## Current limits

The executable prototype uses deterministic safety rules and in-memory simulated devices. Smart Home Control has a Streamlit UI, a bilingual rule fallback, optional structured campus-model proposals and local JSONL audit evidence. The campus call still requires the university network/VPN and a local key. The prototype does not send real notifications or operate physical devices; those integrations must preserve these contracts and report their actual outcomes.
