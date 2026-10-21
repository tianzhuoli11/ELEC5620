# Energy and Comfort

Owner: Tianzhuo Li. Requirements: AR-05 / UC-05; optional OR-05, with UC-06 integration.

Stage 1 implements SCRUM-22's provisional shared context and SCRUM-16's deterministic assessment slice. It does not control a device, send a notification, call an LLM, persist audit history or provide a Streamlit page. Local implementation and tests do not mean the work is merged or Jira Done.

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

Its device execution, readback, recovery and post-action environmental cases
remain explicitly Pending until the M2 device and cross-domain safety contracts
are approved. The runner's fictional trusted source exercises eligibility logic
only; it is not a real authorization or team acceptance record.
