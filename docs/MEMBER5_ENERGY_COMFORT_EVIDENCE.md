# Member 5 Energy & Comfort delivery evidence

Owner: Tianzhuo Li. Scope: AR-05 / UC-05, MR-08, MR-09, OR-05, SCRUM-16/22/32/33/38.

This record describes repository evidence on **`main@2d035f6`**. It does not claim course marks, Canvas upload, or physical-device operation.

## Formal acceptance and demo (SCRUM-38 / UC-05)

| Artifact | Path |
| --- | --- |
| Scenario acceptance report | [docs/acceptance/ENERGY_COMFORT_ACCEPTANCE.md](acceptance/ENERGY_COMFORT_ACCEPTANCE.md) |
| 2-minute Streamlit demo script | [docs/demos/UC05_ENERGY_COMFORT_DEMO.md](demos/UC05_ENERGY_COMFORT_DEMO.md) |
| Canvas contribution draft (SCRUM-43) | [docs/MEMBER5_CONTRIBUTION_STATEMENT.md](MEMBER5_CONTRIBUTION_STATEMENT.md) |
| Offline runner | `python -m simulation.energy_comfort_acceptance` → `data/runtime/energy_comfort_acceptance_run.json` (git-ignored) |

## Traceability

| Requirement | Implemented evidence | Current boundary |
| --- | --- | --- |
| SCRUM-22 / shared context | `models/context.py`; validation in `tests/test_energy_comfort.py` | M2/M4 naming still team confirmation |
| MR-08 / SCRUM-16 | `monitoring.py`, `integration.py`, Streamlit assessment | Assessment-only button; no auto dispatch |
| MR-09 / SCRUM-32 | `control.py`, `SafetyState`, `post_action.py`; tests `test_scrum32_acceptance`, `test_release_controls`, `test_cross_domain_safety` | **Device readback PASS** when tested; **environment UNKNOWN_NOT_MEASURED**; **FORMAL_CONTROL_PENDING** |
| OR-05 / SCRUM-33 | `explanations.py`; Energy audit + `selected_plan` for shared Decision explanations (PR #21) | Does not invent savings or post-action temperature |
| UC-05 / SCRUM-38 | Acceptance report + runner + UI tests | Environment verification **not PASS** without independent sensor feed |

UI modes: **`ASSESSMENT_ONLY`**, **`EXPLICIT_SIMULATION`**, **`FORMAL_CONTROL_PENDING`** (see `ui/energy_comfort.py`).

## Team integration hand-off

Candidate context types and `energy_comfort_observation` readings are documented in [domains/energy_comfort/README.md](../domains/energy_comfort/README.md). Formal `ActionRequest` creation via `evaluate_formal_control_attempt` stays at zero until `ACTIVE_FORMAL_CONTROL_CONTRACT` in `control_readiness.py` is approved by the team.

Protected devices: Elderly `ROOM_LIGHTS` + Home Security `INITIAL_DEVICE_STATES` deny-list.

## Reproducible evidence (31 October 2026)

From checkout `2d035f6`, Windows, Python 3.12.4:

- `python -m simulation.energy_comfort_acceptance` → **11/11** offline cases + **2/2** test-only fixture cases PASS.
- Targeted tests: `test_energy_comfort_acceptance`, `test_scrum32_acceptance`, `test_cross_domain_safety`, `test_energy_comfort_ui` — all PASS.
- Full suite on `2d035f6`: **315 OK (2 skipped)** (recorded before this doc update; not re-run for doc-only commit).

No campus key or real device required for the above.

Key merges: PR **#13** (domain), **#17** (integrated control + safety), **#22** (post-action + UI semantics on integrated `main`).
