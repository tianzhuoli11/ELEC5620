# Shared interface draft

These proposed fields consolidate the team plan for agreement before implementation. They do not define an existing runnable API or mandate a Python validation library.

## Event and Sensor

Event: `event_id`, `event_type`, `source`, `timestamp`, `context`; add an explicit `simulated` flag. Use timezone-aware ISO 8601 timestamps and preserve the event ID throughout its lifecycle.

Sensor/readings should identify the sensor, type, value, unit and observation time. Jinjing coordinates validation and each member provides domain examples. Do not independently invent conflicting shared fields.

## RiskAssessment

`event_id`, `risk_level`, `rationale`, `policy_override`. Use `LOW`, `MEDIUM`, `HIGH`. Add evidence source and fallback indicators as agreed; unavailable facts remain unknown.

Validate LLM proposals against deterministic rules. Define and test scenario thresholds in the appropriate domain; a model proposal is not execution authorisation.

## ActionRequest and ActionResult

ActionRequest: `device_id`, `action`, `parameters`, `authorisation`, with `event_id` where needed for tracing.

ActionResult: `success`, `returned_state`, `verified`, `error`. Dispatch does not prove success; clearly report unverified, partial, offline and failed outcomes.

## Notifications and AuditLog

Represent simulated, failed, sent, acknowledged and timeout outcomes only where actually supported. Simulated sending or API acceptance is not recipient acknowledgement.

AuditLog: `event_id`, `agent`, `action`, `outcome`, `timestamp`. Link events, assessments and action results without keys or unnecessary personal data.

## Module boundaries

`ui/` and `simulation/` provide inputs; `agents/` orchestrates; `domains/` evaluates scenario rules; `models/` defines common types; `services/` provides LLM, notification and audit access; `tools/` provides device entry points, with simulated state in `simulation/`.

Business logic must not import the UI. Shared-field/entry-point changes require example payloads in a PR and communication with affected members.
