# Yang Yang - Smart Home Control Delivery Evidence

Owner: Yang Yang

Stage 1 trace: AR-02 / UC-02, optional OR-02 / UC-07
Implementation branch: `yang-yang`

## Delivered scope

- Natural-language interpretation for English and Chinese night, away and relax requests.
- Optional `campus-qwen` structured goal proposal with strict schema and allow-list validation.
- Deterministic fallback for missing credentials, timeouts, malformed output and unsafe proposals.
- Policy-controlled multi-device plans for a light, curtain, door lock and air conditioner.
- Ordered dispatch and independent returned-state verification through the shared `DeviceAutomationAgent`.
- Explicit complete, partial, failed and clarification outcomes.
- Exterior-door unlock requests blocked before dispatch pending human approval.
- Streamlit page showing the interpreted intent, plan results, device states and agent trace.
- JSONL audit evidence stored under ignored `data/runtime/`.

## Acceptance scenarios executed on 24 October 2026

| Scenario | Expected result | Observed result |
| --- | --- | --- |
| `good-night` | Four approved actions execute and verify | `COMPLETE`; light off, curtain closed, door locked, AC sleep at 22 C |
| `good-night --offline living-room-ac` | Completed actions remain visible and AC failure is explicit | `PARTIAL`; first three verified, AC reported offline |
| `sensitive` | Exterior-door unlock is not self-authorised | `FAILED` safely; zero device dispatches |
| Ambiguous request | Ask for clarification without device execution | `CLARIFICATION_REQUIRED`; zero dispatches |
| Invalid/malicious AI proposal | Ignore injected device fields and use safe fallback | Safe night-mode plan; door remains locked |
| Model timeout | Continue through deterministic supported-goal fallback | Safe fallback outcome recorded in evidence |

## Verification commands

```powershell
.venv\Scripts\python -m unittest tests.test_smart_home_control tests.test_smart_home_ui -v
.venv\Scripts\python -m simulation.smart_home_demo --scenario good-night
.venv\Scripts\python -m simulation.smart_home_demo --scenario good-night --offline living-room-ac
.venv\Scripts\python -m simulation.smart_home_demo --scenario sensitive
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m streamlit run app.py
```

The automated Smart Home Control suite contains 15 tests. The full regression suite also passes all 112 tests, confirming that this integration does not break the existing project workflows. The offline logic and page tests pass without an API key. The campus request format is tested with a controlled response; a live campus-network smoke test must be recorded separately and must not expose the API key.

## Contribution-statement wording

Implemented AR-02 / UC-02 Smart Home Control: bilingual natural-language goal interpretation, optional validated campus-Qwen integration, policy-controlled multi-device planning, simulated device adapters, independent state verification, failure and safety handling, Streamlit UI, audit records, automated tests and demonstration scenarios. Also integrated the domain with the shared HomeCoordinatorAgent and DeviceAutomationAgent contracts.

## Jira / Agile evidence to attach

- Link each commit and pull request to the team's actual Jira issues.
- Attach the passing test output and screenshots of the three demonstration scenarios.
- Record review feedback and the resulting change before marking the final Jira issue Done.
- Add the final clean-deployment rehearsal date and Canvas-downloaded-source result after the rehearsal is actually performed.
