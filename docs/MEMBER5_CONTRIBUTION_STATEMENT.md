# Member 5 contribution statement (SCRUM-43 draft)

**Name:** Tianzhuo Li  
**Role:** Energy & Comfort (Member 5)  
**Repository:** `tianzhuoli11/ELEC5620`  
**Final integrated commit referenced:** `2d035f6` (merge PR #22)  
**Date prepared:** 31 October 2026  

This text is prepared for Canvas submission. It describes verifiable repository work only. It does **not** claim course marks, teammate sign-off, or that this file has already been uploaded to Canvas.

## Summary

I implemented the Energy & Comfort domain (AR-05 / UC-05) on the shared three-agent framework: deterministic context assessment (MR-08), fail-closed eligibility and formal-control readiness (SCRUM-32 / MR-09 preparation), Streamlit assessment and explicitly approved simulated control with cross-domain safety interlocks, post-action environment honesty (`UNKNOWN_NOT_MEASURED`), offline acceptance evidence (SCRUM-38), and evidence-bound explanations (OR-05) integrated with the team’s Decision explanations flow after PR #21.

## Jira items — actual contribution

| Issue | What I delivered (evidence on `main`) |
| --- | --- |
| **SCRUM-16 / MR-08** | Three-state assessment in `domains/energy_comfort/monitoring.py`; shared workflow adapter `integration.py`; shared context in `models/context.py`; tests in `tests/test_energy_comfort.py`. |
| **SCRUM-22** | `energy_comfort_observation` event shape, validation and round-trip tests; domain README and hand-off notes for M2/M4. |
| **SCRUM-32 / MR-09** | Fail-closed `control_policy.py` and `control_readiness.py`; PR #17 simulated control path (`control.py`, `services/safety_state.py`) with PR #22 merge adding `post_action.py`, UI mode labels, and acceptance tests. Device readback and PARTIAL outcomes are tested; room environment is explicitly **not** claimed as measured. |
| **SCRUM-33 / OR-05** | Deterministic `domains/energy_comfort/explanations.py`; Energy audit records include assessment + `selected_plan` for the shared **Decision explanations** page (team coordinator/UI in PR #21 — I owned Energy facts, trade-off wording limits, and Energy UI/audit fields). |
| **SCRUM-38 / UC-05** | `simulation/energy_comfort_acceptance.py`, `docs/acceptance/ENERGY_COMFORT_ACCEPTANCE.md`, UI and integration tests (`test_energy_comfort_ui.py`, `test_scrum32_acceptance.py`, `test_cross_domain_safety.py`). |

## Pull requests and merges (GitHub)

| PR | Role |
| --- | --- |
| **#13** | Merged Energy & Comfort domain into `main`. |
| **#17** | Integrated release fixes; Energy explicit simulated control and live `SafetyState` interlocks (commits `50d1604`, `4e7607e` — co-developed with integration owner). |
| **#22** | Merged SCRUM-32 post-action boundary, UI semantics, conflict resolution with PR #21 explanation audit fields (`2d035f6`). |

## Testing and integration

- Offline: `python -m simulation.energy_comfort_acceptance` (11+2 cases); SCRUM-32 and cross-domain suites cited in the acceptance report.
- UI: Streamlit tests for assessment-only scope, explicit simulation, and cross-page smoke block (`test_energy_comfort_ui.py`).
- Full repository regression was **315 tests OK (2 skipped)** on `2d035f6` before this documentation pass; not re-run for doc-only updates unless code changes.

## Boundaries (stated for assessors)

- **Device readback success ≠ environment improvement.** Post-action room metrics are `UNKNOWN_NOT_MEASURED`.
- **Formal automatic control** remains `FORMAL_CONTROL_PENDING` until team flips `ACTIVE_FORMAL_CONTROL_CONTRACT` (M2/M4).
- No real devices, tariffs, or medical claims.

## Suggested Canvas attachments

1. This file (`docs/MEMBER5_CONTRIBUTION_STATEMENT.md`).
2. `docs/acceptance/ENERGY_COMFORT_ACCEPTANCE.md`.
3. `docs/demos/UC05_ENERGY_COMFORT_DEMO.md`.
4. `docs/MEMBER5_ENERGY_COMFORT_EVIDENCE.md` (traceability index).
5. Generated JSON log: `data/runtime/energy_comfort_acceptance_run.json` (produce locally; not in git).
6. Optional screenshots from the UC-05 demo steps (assessment scope, COMPLETE control, smoke block, UNKNOWN_NOT_MEASURED caption).

## Manual steps still required by me

- Upload the final Canvas archive and this statement when the course submission opens.
- Reconcile Jira SCRUM-38 / SCRUM-43 status with attached evidence (not done in this commit).
- Perform one live Streamlit rehearsal using the demo script on the same machine used for presentation.
