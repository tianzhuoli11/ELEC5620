# Energy & Comfort scenario acceptance report (SCRUM-38)

AR-05 / UC-05 / MR-08 / MR-09 (prototype scope). Generated from `python -m simulation.energy_comfort_acceptance` plus mapped repository tests. Assessment and eligibility cases use the real shared workflow without device dispatch. Explicit simulated control, cross-domain safety, device readback and post-action environment boundaries are covered by separate automated tests listed below.

**Simulated sensors and devices only; no real HVAC, lighting or metering was operated. Room temperature, occupancy and whole-home power after control are recorded as `UNKNOWN_NOT_MEASURED` unless an independent probe is supplied.**

| Run | Value |
| --- | --- |
| run_at | 2026-10-31 00:24 AEDT |
| git_commit | 2d035f6 |
| python | 3.12.4 |
| platform | Windows-11-10.0.26200-SP0 |
| streamlit | 1.66.0 |
| offline acceptance cases | **11 / 11 passed** |
| test-only execution fixture | **2 / 2 passed** |
| SCRUM-32 mapped tests (`test_scrum32_acceptance`) | **5 / 5 passed** |
| cross-domain safety tests | **6 / 6 passed** |
| Energy UI integration tests | **7 / 7 passed** |

## Coverage layers (honest labels)

| Layer | Label | Meaning in this prototype |
| --- | --- | --- |
| Assessment / eligibility | `ASSESSMENT_ONLY` | Shared agents assess; no ActionRequest from the assessment button |
| Explicit UI control | `EXPLICIT_SIMULATION` | Approved panel + session `SafetyState` + `run_energy_control` |
| Formal automatic integration | `FORMAL_CONTROL_PENDING` | `ACTIVE_FORMAL_CONTROL_CONTRACT` gates remain false |
| Device readback | **PASS when tested** | `DeviceAutomationAgent` independent readback; `ActionResult.success = accepted and verified` |
| Room environment after action | **NOT PASS** | `post_action_environment.status = UNKNOWN_NOT_MEASURED` (not a comfort/savings claim) |

## Offline acceptance results (`simulation.energy_comfort_acceptance`)

| ID | Case | Requirement | Expected | Actual | Result |
| --- | --- | --- | --- | --- | --- |
| AT-EC01 | Comfort in range (22 °C, occupied) | MR-08 / SCRUM-16 | NO_ADJUSTMENT; ASSESSED; NOT_EXECUTED; 0 dispatch | Matches | PASS |
| AT-EC02 | Lower inclusive boundary (20 °C) | MR-08 | NO_ADJUSTMENT | Matches | PASS |
| AT-EC03 | Upper inclusive boundary (24 °C) | MR-08 | NO_ADJUSTMENT | Matches | PASS |
| AT-EC04 | Too warm (27 °C, occupied) | MR-08 | ADJUSTMENT_NEEDED; still NOT_EXECUTED | Matches | PASS |
| AT-EC05 | Occupancy unknown | MR-08 | INSUFFICIENT_DATA | Matches | PASS |
| AT-EC06 | Invalid temperature unit (°F reading) | Shared validation | Rejected before routing; 0 dispatch | Matches | PASS |
| AT-EC07 | Eligibility: no authorization metadata | MR-09 prep | Not eligible; NOT_EXECUTED | Matches | PASS |
| AT-EC08 | Eligibility: untrusted source label | MR-09 prep | Not eligible | Matches | PASS |
| AT-EC09 | Eligibility: conflicting safety flag | MR-09 prep | Not eligible | Matches | PASS |
| AT-EC10 | Eligibility: trusted demo inputs only | MR-09 prep | Eligible; still NOT_EXECUTED | Matches | PASS |
| AT-EC11 | Formal control attempt despite eligibility | SCRUM-32 contract | eligible=true; ready=false; status=PENDING; 0 ActionRequests | Matches | PASS |

## Test-only execution fixture (not production authorization)

| ID | Case | Expected | Actual | Result |
| --- | --- | --- | --- | --- |
| AT-EC-F01 | Dispatch timeout on fictional device | accepted=false; state unchanged | Matches | PASS |
| AT-EC-F02 | Unsupported action schema | accepted=false; no false success | Matches | PASS |

## SCRUM-32 / MR-09 simulated control (automated, `tests/test_scrum32_acceptance.py`)

| ID | Case | Expected | Result |
| --- | --- | --- | --- |
| AT-EC-S01 | Hot occupied room + clear safety | planned≥1; verified action results | PASS |
| AT-EC-S02 | Formal integration path | 0 ActionRequests | PASS |
| AT-EC-S03 | Blocked safety registry | planned=0; no dispatch | PASS |
| AT-EC-S04 | After verified device actions | post_action UNKNOWN_NOT_MEASURED; source=`no_independent_environment_sensor_feed` | PASS |
| AT-EC-S05 | AC offline | workflow PARTIAL; bounded attempts; no false COMPLETE | PASS |

Additional device readback, negation guard and partial-failure coverage: `tests/test_release_controls.py`, `tests/test_cross_domain_safety.py`, shared framework tests named in the acceptance JSON `shared_framework_execution_coverage` list.

## Commands (reproduce this report)

```powershell
cd <clean ELEC5620 checkout at 2d035f6>
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m simulation.energy_comfort_acceptance > data\runtime\energy_comfort_acceptance_run.json
.venv\Scripts\python -m unittest discover -s tests -p "test_energy_comfort_acceptance.py" -q
.venv\Scripts\python -m unittest discover -s tests -p "test_scrum32_acceptance.py" -q
.venv\Scripts\python -m unittest discover -s tests -p "test_cross_domain_safety.py" -q
.venv\Scripts\python -m unittest discover -s tests -p "test_energy_comfort_ui.py" -q
```

Full machine JSON for this run: `data/runtime/energy_comfort_acceptance_run.json` (git-ignored; attach to Jira SCRUM-38 if required).

## Limits (do not claim in demo or Jira)

- No measured temperature drop, occupancy change or energy savings after control.
- `UNKNOWN_NOT_MEASURED` is an honest **non-PASS** for environment verification, not evidence of improvement.
- Formal Energy dispatch via `evaluate_formal_control_attempt` remains **PENDING** until team-approved M2/M4 contracts are enabled.
- Eligibility worksheet fields on the assessment panel are demo-only; live clearance comes from Elderly Safety and Home Security workflow results in the same Streamlit session.

## Defects

No failing case in this run on `2d035f6`.
