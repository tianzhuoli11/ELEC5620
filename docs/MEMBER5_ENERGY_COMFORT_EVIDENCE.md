# Member 5 Energy & Comfort delivery evidence

Owner: Tianzhuo Li. Scope: AR-05 / UC-05, MR-08, MR-09 preparation, and optional OR-05.

This record describes repository evidence only. It does not claim Jira completion,
team review, M2/M4 integration, merge to `main`, or physical-device operation.

## Traceability

| Requirement | Implemented evidence | Current boundary |
| --- | --- | --- |
| SCRUM-22 / shared context | `models/context.py`; event round-trip and validation in `tests/test_energy_comfort.py` | Candidate names, namespace and `HomeMode` still need M2/M4 and framework-owner confirmation |
| MR-08 / SCRUM-16 | Deterministic three-state assessment in `domains/energy_comfort/monitoring.py`; shared workflow adapter in `integration.py` | Assessment-only; no claim of whole-home safety or energy optimisation |
| MR-09 / SCRUM-32 | Fail-closed eligibility in `control_policy.py`; formal readiness gate in `control_readiness.py` / `evaluate_formal_control_attempt`; protected Elderly/Security deny-list; shared automation failure-path fixture | Formal control remains PENDING: M2 mapping/schema/authorization and M4 safety-feed contracts are unchecked in `ACTIVE_FORMAL_CONTROL_CONTRACT`; no ActionRequest planner is enabled |
| OR-05 / SCRUM-33 | Evidence-bound deterministic explanations in `explanations.py` | Coordinator/UC-06 explanation request contract and persistent audit remain Pending |
| UC-05 / SCRUM-38 | `simulation.energy_comfort_acceptance` records input, expected, actual, decision, trace and PASS/FAIL | Formal domain execution/readback and post-action observations remain Pending |

The acceptance output separates `ASSESSMENT_ONLY`, `TEST_ONLY_SIMULATION`, and
formal Energy & Comfort control (`PENDING`). Test fixture device identifiers and
schemas are fictional and are not M2-approved contracts.

## Team integration hand-off

Implemented candidate inputs, importable from `models`:

- `HomeEnvironment(temperature_c, occupied)`; `None` means unknown.
- `UserPreference(temperature_min_c, temperature_max_c)`; bounds are inclusive.
- `EnergyProfile(current_power_w, unoccupied_power_limit_w)`; values are watts.
- `HomeMode`, `DeviceObservation`, and aggregate `HomeContext`.
- `energy_comfort_observation` uses `indoor_temperature` (`C`) and `occupancy`
  (`boolean`) readings; other candidate context is under `context["energy_comfort"]`.

M2 must confirm the observation-to-control device ID mapping, command and
`expected_state` schema, and executable authorization source. M4 must confirm how
unknown or conflicting security/safety conditions are supplied. Until both are
resolved, Energy & Comfort produces no executable `ActionRequest`.

Repository evidence for the current blockers:

- Candidate M2 light ID after review: `bedroom-light` (`domains/smart_home_control/devices.py`).
- Protected deny-list derived from Elderly `ROOM_LIGHTS` and Home Security
  `INITIAL_DEVICE_STATES` (includes `bathroom_light`, `security_lights`, `siren`, valves).
- Checked-in gates: `ACTIVE_FORMAL_CONTROL_CONTRACT` in
  `domains/energy_comfort/control_readiness.py` (all false).
- Eligibility may be true for later planning; formal readiness stays `PENDING`
  and `action_requests_created` remains 0.

## Reproducible evidence

On 21 October 2026, a `git archive` of commit `cfc9b3b` was expanded into a clean
temporary directory on Windows. Using Python 3.14.3, a new `.venv` installed
`requirements.txt` successfully. From that clean copy:

- `python -m unittest discover -s tests -v`: 77 passed.
- `python -m simulation.energy_comfort_demo`: exited successfully with all three decisions.
- `python -m simulation.energy_comfort_acceptance`: 10 assessment/eligibility
  cases and 2 test-only execution cases passed; formal control stayed Pending.

No campus key, external model, Streamlit session, or real device was used. The
tracked source contains `.env.example`, but not `.env`, virtual environments,
caches, runtime logs, recognised token patterns, or local absolute paths.

Relevant local commits are `2eaa35c`, `59fdbc5`, `8655a8e`, `3f44771`,
`f93437f`, `3aa6f74`, `19f2c4c`, `fe7b927`, and `cfc9b3b`.
