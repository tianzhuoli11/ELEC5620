# Energy and Comfort

Update (29 October): the separate `control.run_energy_control` API and **Run a simulated adjustment** panel now execute explicitly approved plans through the shared agents and existing simulated device inventory. See [control review and demonstration steps](../../docs/INTEGRATED_CONTROL_REVIEW.md). The historical assessment/readiness APIs below remain non-executable; their unchecked approval flags do not govern the separate explicit simulation path. The simulation now automatically derives safety clearance from fresh same-session Elderly Safety and Home Security results, with active external warnings also blocking execution.

Owner: Tianzhuo Li. Requirements: AR-05 / UC-05; optional OR-05, with UC-06 integration.

Stage 1 implements SCRUM-22's provisional shared context and SCRUM-16's deterministic assessment slice. The Streamlit page in `ui/energy_comfort.py` runs that assessment through the shared workflow, shows fail-closed eligibility and deterministic explanations, and records local assessment evidence. It does not control a device, send a notification, call an LLM, or claim formal Energy & Comfort device control. Formal control remains pending.

Put shared HomeEnvironment, UserPreference, EnergyProfile and HomeMode types in `models/`. Reuse `tools/` and `services/`. Safety overrides comfort and energy goals; missing facts remain unknown. Put tests in `tests/` and views in `ui/`.

## Input mapping

`energy_comfort_observation` events place `indoor_temperature` (`C`) and `occupancy` (`boolean`) observations in `Event.readings`. `Event.context["energy_comfort"]` contains the preference, optional energy profile, optional HomeMode, observed devices and a simulation marker. Temperature and occupancy are rejected in the context dictionary so they cannot silently conflict with readings. `simulation.energy_comfort_demo.make_energy_comfort_event` creates a correctly shaped simulated event.

The candidate shared types are `HomeEnvironment`, `UserPreference`, `EnergyProfile`, `HomeMode`, `DeviceObservation` and `HomeContext` in `models/context.py`. `None` means unknown; it is never interpreted as zero, unoccupied, offline or normal. Watts and degrees Celsius are explicit in field names. These additions are backward-compatible with the existing Event and workflow constructors, but remain subject to M2/M4 and framework-owner review; no approval is claimed here.

## Deterministic policy

- For a known occupied home, both ends of `UserPreference` are inclusive. A temperature inside or on the boundary is `NO_ADJUSTMENT` for the observed temperature-comfort target only; it says nothing about other rooms, energy waste or safety. A value outside is `ADJUSTMENT_NEEDED` for further comfort assessment.
- Missing occupancy prevents selecting a policy. Missing occupied temperature or either preference bound is `INSUFFICIENT_DATA`.
- A known unoccupied home does not use the occupied comfort range. The fictional energy rule compares observed whole-home watts with an explicit unoccupied watt limit. At or below the limit is `NO_ADJUSTMENT` for this one configured rule only, not proof that the whole home has no energy waste. Above it is `ADJUSTMENT_NEEDED` for further investigation only when an available device is explicitly observed with `power="on"`; otherwise evidence is insufficient.
- A powered-device observation is only a candidate clue. It does not prove that device caused the excess, that it can be safely switched off, or that control would save a particular amount. A controllable-device allowlist, device-level power attribution and safety policy are deferred to the next stage.
- These values are user/configuration inputs for a simulated policy, not official safety, medical, tariff or HVAC standards.

`EnergyComfortHandler` maps `NO_ADJUSTMENT` to shared risk `LOW`; `ADJUSTMENT_NEEDED` and `INSUFFICIENT_DATA` map to `MEDIUM` so neither is mislabeled as a high safety risk. The shared graph does not dispatch or notify based on `MEDIUM`; it only follows explicit action and notification requests, and this handler returns neither. Downstream Energy & Comfort code reads the three-way value structurally from `EnergyComfortWorkflowOutcome.assessment.decision`; it must not distinguish the states by parsing rationale text. A consumer holding only the generic `WorkflowResult` cannot recover this domain enum without parsing its string evidence, so adding a generic structured domain-result field remains a team-level contract decision. `ASSESSED` means the assessment ran, not that an `INSUFFICIENT_DATA` case achieved the user's goal. `WorkflowResult.trace` is in-memory execution evidence, not persistent history.

Run the offline example from the repository root after installing existing dependencies:

```powershell
.venv\Scripts\python -m simulation.energy_comfort_demo
```

## Reviewable evidence and current limits

A minimal simulated payload uses observations in `readings` and policy context in
the provisional namespace:

```json
{
  "event_type": "energy_comfort_observation",
  "simulated": true,
  "readings": [
    {"reading_type": "indoor_temperature", "value": 22.0, "unit": "C"},
    {"reading_type": "occupancy", "value": true, "unit": "boolean"}
  ],
  "context": {
    "energy_comfort": {
      "preference": {"temperature_min_c": 20.0, "temperature_max_c": 24.0},
      "energy": null,
      "home_mode": "HOME",
      "devices": [],
      "simulated": true
    }
  }
}
```

The executable offline examples produce `NO_ADJUSTMENT`, `ADJUSTMENT_NEEDED`,
and `INSUFFICIENT_DATA`; unknown occupancy remains missing rather than becoming
`false`. `tests.test_energy_comfort.SharedContextTests` imports the candidate
types through `models`, verifies the serialized namespace, and round-trips that
payload through `context_from_event`. This is a local simulated consumer, not
evidence that M2 or M4 has integrated the contract.

`evaluate_light_shutdown_candidate` now composes assessment with fail-closed,
non-executable eligibility. `explain_energy_comfort` explains only supplied
assessment, workflow, eligibility and verified-result evidence. The UC-05
preparation runner can be invoked with:

```powershell
.venv\Scripts\python -m simulation.energy_comfort_acceptance
```

`run_energy_control` (PR #17 **EXPLICIT_SIMULATION** path) verifies device readback and
records post-action room environment as **`UNKNOWN_NOT_MEASURED`** via
`post_action.assess_post_action_environment` unless an independent probe is wired.
Formal automatic integration remains **`FORMAL_CONTROL_PENDING`** while
`ACTIVE_FORMAL_CONTROL_CONTRACT` gates are false.

`evaluate_formal_control_attempt` applies the checked-in
`ACTIVE_FORMAL_CONTROL_CONTRACT` gates after eligibility. Today every gate is
false, so formal control status stays `PENDING`, zero `ActionRequest` values are
created, and Elderly/Security protective devices remain on an explicit deny-list.

The current `HomeCoordinatorAgent` has no UC-06 explanation-request route: it
routes sensor events and user goals and coordinates notifications. Adding a
shared explanation request/response contract therefore remains a framework-owner
decision. Until then, domain callers can pass an actual
`EnergyComfortAssessment`, optional `WorkflowResult`, and optional eligibility
result directly to `explain_energy_comfort`; missing workflow evidence returns
`UNKNOWN`, not an execution claim.

## Offline reproduction

Use the repository's existing dependencies; Energy & Comfort adds no package or
configuration variable and does not require `.env`, a campus key, network access,
Streamlit, or an external model:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m unittest tests.test_energy_comfort tests.test_energy_comfort_explanations tests.test_energy_comfort_execution_fixture tests.test_energy_comfort_acceptance -v
.venv\Scripts\python -m simulation.energy_comfort_demo
.venv\Scripts\python -m simulation.energy_comfort_acceptance
```

The acceptance output separates `ASSESSMENT_ONLY`, `TEST_ONLY_SIMULATION`, and
formal Energy & Comfort control (`PENDING`). The test-only fixture uses
`fictional-test-light` and an invented schema solely to validate the existing
shared automation failure paths; neither is an M2-approved interface or control
authorization.
