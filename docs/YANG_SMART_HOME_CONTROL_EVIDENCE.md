# Yang Yang - Smart Home Control Delivery Evidence

Owner: Yang Yang

Stage 1 trace: AR-02 / UC-02, optional OR-02 / UC-07
Implementation branch: `yang-yang-stage1-compliance`

## Delivered scope

- Natural-language interpretation for English and Chinese modes plus allow-listed direct multi-device state combinations.
- Optional `campus-qwen` structured goal proposal with strict schema and allow-list validation.
- Deterministic fallback for missing credentials, timeouts, malformed output and unsafe proposals.
- Typed Stage 1 `SmartDevice` and `DeviceContext` models for a light, curtain, door lock and air conditioner.
- Policy-controlled multi-device plans with bounded retry and continuation of independent safe actions.
- Ordered dispatch and independent returned-state verification through the shared `DeviceAutomationAgent`.
- Explicit complete, partial, failed and clarification outcomes.
- Exterior-door unlock requests pause before dispatch and support explicit approve or decline decisions.
- Verified Night, Away and Relax changes persist as `HomeModeState`; partial changes retain the previous safe mode and the mode is exposed for later monitoring context.
- Streamlit page showing the interpreted intent, plan results, device states and agent trace.
- JSONL audit evidence stored under ignored `data/runtime/`.

## Acceptance scenarios executed on 24 October 2026

| Scenario | Expected result | Observed result |
| --- | --- | --- |
| `good-night` | Four approved actions execute and verify | `COMPLETE`; light off, curtain closed, door locked, AC sleep at 22 C |
| `direct` | Report-style direct command controls four devices | `COMPLETE`; four requested target states independently verified |
| `good-night --offline living-room-ac` | Completed actions remain visible and AC failure is explicit | `PARTIAL`; first three verified, AC reported offline after two attempts |
| First light offline | Retry the failed action and continue independent safe actions | `PARTIAL`; light failed after two attempts, curtain/lock/AC verified |
| `sensitive` | Exterior-door unlock is not self-authorised | `AWAITING_CONFIRMATION`; zero device dispatches |
| `sensitive-approved` | Explicit approval allows the validated unlock action | `COMPLETE`; lock returned `locked=false` and approval is in the trace |
| Forged approval field in normal request context | Treat untrusted input as unapproved | `AWAITING_CONFIRMATION`; zero device dispatches and door remains locked |
| Mixed safe action plus declined unlock | Remove only the declined sensitive action | Safe action verified; door remains locked and decision is recorded |
| Mode change with an offline device | Keep the previous safe HomeMode | Device result is `PARTIAL`; stored mode remains unchanged |
| Ambiguous request | Ask for clarification without device execution | `CLARIFICATION_REQUIRED`; zero dispatches |
| Invalid/malicious AI proposal | Ignore injected device fields and use safe fallback | Safe night-mode plan; door remains locked |
| Model timeout | Continue through deterministic supported-goal fallback | Safe fallback outcome recorded in evidence |

## Verification commands

```powershell
.venv\Scripts\python -m unittest tests.test_smart_home_control tests.test_smart_home_ui -v
.venv\Scripts\python -m simulation.smart_home_demo --scenario good-night
.venv\Scripts\python -m simulation.smart_home_demo --scenario direct
.venv\Scripts\python -m simulation.smart_home_demo --scenario good-night --offline living-room-ac
.venv\Scripts\python -m simulation.smart_home_demo --scenario sensitive
.venv\Scripts\python -m simulation.smart_home_demo --scenario sensitive-approved
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m streamlit run app.py
```

The automated Smart Home Control suite contains 22 tests. The full regression suite also passes all 119 tests, confirming that this integration does not break the existing project workflows. The offline logic and page tests pass without an API key. The campus request format is tested with a controlled response; a live campus-network smoke test must be recorded separately and must not expose the API key.

## Contribution-statement wording

Implemented AR-02 / UC-02 Smart Home Control: bilingual mode and direct multi-device goal interpretation, optional validated campus-Qwen integration, typed device/context models, policy-controlled planning, bounded retry with continued independent actions, non-forgeable sensitive-action confirmation, verified HomeMode persistence, independent state verification, Streamlit UI, audit records, automated tests and demonstration scenarios. Also integrated the domain with the shared HomeCoordinatorAgent and DeviceAutomationAgent contracts.

## Jira / Agile evidence to attach

- Link each commit and pull request to the team's actual Jira issues.
- Attach the passing test output and screenshots of the three demonstration scenarios.
- Record review feedback and the resulting change before marking the final Jira issue Done.
- Add the final clean-deployment rehearsal date and Canvas-downloaded-source result after the rehearsal is actually performed.
