# Yang Yang: Sprint 1 Smart Home Control completion and safety hardening

This increment closes the Smart Home Control gaps identified after Sprint 0 and
aligns the implementation more closely with AR-02 / UC-02 and optional OR-02 /
UC-07. The implementation is on branch `yang-yang-stage1-compliance`, commit
`0c47518` (`feat: complete smart home Stage 1 compliance`). At the time this
document was written, that follow-up branch had not yet been pushed or opened as
a new pull request.

## Sprint goal

Extend the first working demonstration into a safer, more complete and
traceable multi-device workflow while preserving compatibility with the other
project domains.

## Changes delivered

| Sprint 0 limitation | Sprint 1 result |
| --- | --- |
| Primarily fixed Night, Away and Relax modes | Added allow-listed direct multi-device commands, including the report-style light, curtain, lock and air-conditioner request. |
| A failed first action stopped later actions | Added per-request bounded retry and opt-in continuation for independent safe Smart Home actions. Other domains retain the original stop-on-failure default. |
| Unlock was blocked with no way to continue | Added an `AWAITING_CONFIRMATION` pause plus explicit Approve and Keep Door Locked controls. |
| Approval state could have been represented as ordinary input data | Confirmation is carried by the trusted resume path, bound to the original event ID; forged request context cannot authorise an unlock. |
| Device inventory used untyped state dictionaries | Added `SmartDevice`, `DeviceContext`, `SmartLight`, `SmartCurtain`, `SmartLock` and `AirConditioner`. |
| Home mode was not retained after execution | Added `HomeModeState`; only a fully verified mode change updates it, while partial execution keeps the previous safe mode. |
| Limited demonstration coverage | Added direct, approved-sensitive and declined-sensitive scenarios plus expanded unit, integration and UI tests. |

## Acceptance evidence

| Scenario | Observed result |
| --- | --- |
| Good night | `COMPLETE`; four device states verified and mode becomes `NIGHT` |
| Report-style direct command | `COMPLETE`; light, curtain, lock and AC target states verified |
| First light offline | Light fails after two attempts; curtain, lock and AC still verify; overall `PARTIAL` |
| AC offline | First three actions remain visible and verified; AC failure is explicit; overall `PARTIAL` |
| Unlock without a decision | `AWAITING_CONFIRMATION`; zero dispatches |
| Approved unlock | `COMPLETE`; returned lock state is `false` and approval is recorded in the trace |
| Declined unlock mixed with a safe action | Unlock is removed, the safe action proceeds and the door remains locked |
| Forged approval field | Still `AWAITING_CONFIRMATION`; zero dispatches and the door remains locked |
| Partial mode change | Stored mode remains at the previous safe value |
| Invalid or timed-out model proposal | Deterministic validated fallback handles the request safely |

## Verification commands

```powershell
.venv\Scripts\python -m unittest tests.test_smart_home_control tests.test_smart_home_ui -v
.venv\Scripts\python -m simulation.smart_home_demo --scenario direct
.venv\Scripts\python -m simulation.smart_home_demo --scenario sensitive
.venv\Scripts\python -m simulation.smart_home_demo --scenario sensitive-approved
.venv\Scripts\python -m simulation.smart_home_demo --scenario sensitive-declined
.venv\Scripts\python -m simulation.smart_home_demo --scenario good-night --offline bedroom-light
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m streamlit run app.py
```

On 24 October 2026, all 22 Smart Home Control tests and all 119 project tests
passed. The direct, approval, decline and retry demonstrations also completed
with their expected outcomes. These tests use fictional local devices and do not
require an API key.

## Contribution statement

Implemented and hardened AR-02 / UC-02 Smart Home Control: bilingual home-mode
and direct multi-device interpretation, optional validated Campus Qwen proposals,
typed device/context models, policy-controlled planning, bounded retry with
continued independent actions, non-forgeable sensitive-action confirmation,
verified HomeMode persistence, state verification, Streamlit UI, audit records,
automated tests and demonstration scenarios. Integrated the domain with the
shared `HomeCoordinatorAgent` and `DeviceAutomationAgent` contracts.

## Evidence still to add after it actually occurs

- The real Jira issue links and status history for both increments.
- Sprint Review feedback and any change made in response to that feedback.
- Screenshots or recordings of the final demonstration scenarios.
- A live Campus Qwen smoke test over the university network/VPN, without exposing the personal key.
- The clean-deployment rehearsal using the exact source downloaded from Canvas.
