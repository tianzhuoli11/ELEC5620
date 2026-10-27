# Yuanbo Zhang: Sprint 0 elderly fall assessment (SCRUM-12) on the shared workflow

Elderly Safety Core 1 (AR-01 / UC-01) integrated with the shared
`SmartHomeWorkflow` baseline (PR #3, Jinjing). Everything here is **simulated**
and says so; no API key is needed and no model is called by default.

From the repository root, after `pip install -r requirements.txt`:

```powershell
python -m unittest discover -s tests -v
python -m simulation.elderly_demo --list
python -m simulation.elderly_demo --scenario high_floor
python -m simulation.elderly_demo --scenario medium_wait
python -m simulation.elderly_demo --scenario low_dropped_object
python -m simulation.elderly_demo --scenario high_floor --offline
```

`tests/test_elderly_safety.py` needs only the standard library;
`tests/test_elderly_integration.py` runs the graph and needs `langgraph`.

## What is implemented

| File | Content |
| --- | --- |
| `domains/elderly_safety/context.py` | UC-01 step 2 context: impact, inactivity, posture, location, time of day, home mode, recent activity. Missing values stay unknown. `for_llm()` is the only data that may reach the model: room category, no names, address, contacts or IDs (NFR-03). |
| `domains/elderly_safety/rules.py` | Deterministic fall rules; prototype thresholds below. |
| `domains/elderly_safety/policy.py` | `apply_policy_floor` (a model may confirm or raise, never lower) and `apply_llm_fallback` (documented MEDIUM fallback). |
| `domains/elderly_safety/assessment.py` | `assess_fall(event, proposal_provider)` -> `FallAssessment` with evidence source, override / fallback flags, model rationale, classification time (NFR-02). |
| `domains/elderly_safety/handler.py` | `ElderlySafetyHandler` (shared `DomainHandler`): HIGH -> caregiver `NotificationRequest` + room light `ActionRequest` with `expected_state`; MEDIUM -> `requires_human_review=True` (dispatch blocked, resident confirmation pending); LOW -> record only. |
| `simulation/elderly_scenarios.py`, `simulation/elderly_demo.py` | Five labelled simulated scenarios and a trace through the shared graph. |
| `data/samples/elderly_fall_*.json` | Fixtures with purpose and expected result; validated by tests. |
| `services/config.py` | `.env` / shell variable loading for `ELEC5620_*`; the key never appears in `repr` or logs. |
| `tests/test_elderly_safety.py`, `tests/test_elderly_integration.py`, `tests/test_config.py` | 32 tests; 70 with the existing framework and Pet Care tests (`test_ui` needs Streamlit). |

## Fall rules (prototype thresholds, for discussion)

| Condition | Level |
| --- | --- |
| impact and no motion >= 60 s, or on the floor and no motion >= 20 s | HIGH |
| impact and no motion >= 20 s; impact with duration missing; no impact data but no motion >= 60 s | MEDIUM |
| otherwise (upright again, motion within seconds) | LOW |
| LOW at night or in bathroom/stairs (not upright) | raised to MEDIUM |

No model, timeout or invalid output -> `apply_llm_fallback`: LOW becomes
MEDIUM, MEDIUM/HIGH kept, `evidence_source="llm_fallback"`. These are
prototype values, not medical advice; record agreed changes in Jira and here.

## How it maps to UC-01

| UC-01 | Here |
| --- | --- |
| Step 1 trigger: sudden motion then inactivity | `fall_impact` + `seconds_without_motion` readings |
| Step 2 collect context | `context.collect_context` |
| Step 3 model proposal checked against rules | `assess_fall` + `policy.py` |
| Ext. 1 model unavailable -> MEDIUM | `apply_llm_fallback` |
| Ext. 2 low risk -> false alarm | LOW decision, no action |
| Ext. 3 high risk -> skip confirmation | HIGH decision: notification + light, `requires_human_review=False` |
| Steps 5-6 ask resident, interpret reply | **not yet** (SCRUM-24): baseline graph has no pause point; MEDIUM is blocked with `requires_human_review` |
| Step 7 model drafts alert, coordinator checks privacy | **not yet** (SCRUM-24); message is rule text, describes the condition only |
| Step 9 / Ext. 6 caregiver ack timeout -> operator | **not yet** (SCRUM-25) |

## Proposed shared-contract additions (for review, not changed here)

- `RiskAssessment.evidence_source` (`rules` / `llm_confirmed` / `llm_fallback`) and
  `model_rationale`: the UI should show whether the model was involved. Until
  agreed, the source is appended to `evidence` as `[llm_fallback]`.
- `policy.py` helpers are generic; Pet Care applies the same floor idea.
- A confirmation pause/resume path in `agents/graph.py` for MEDIUM events
  (SCRUM-24); I will propose it as a separate PR.

## Not done yet

- Real campus-qwen proposal provider for falls (Yang's shared adapter); rules
  run alone until then and the trace shows `llm_fallback`.
- Resident confirmation, reply interpretation, caregiver acknowledgement
  timeout and escalation (SCRUM-24 / SCRUM-25, Sprint 1).
- Streamlit view for elderly safety (UI owner to be nominated).
- Sprint Review feedback; record it in Jira when it actually happens.
