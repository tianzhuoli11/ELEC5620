# Yang Yang: Sprint 0 Smart Home Control foundation (AR-02 / UC-02)

This records the first working Smart Home Control increment. It was developed on
branch `yang-yang`, committed as `75cd954` (`feat: add smart home control
workflow`), and merged to `main` through PR #6. Devices, notifications and owner
actions in this increment are simulated; no physical home device is controlled.

## Sprint goal

Provide an end-to-end AR-02 / UC-02 demonstration in which a resident's natural-
language request is interpreted, converted into a policy-approved multi-device
plan, executed through the shared automation agent and verified from returned
device state.

## What was implemented

| Area | Sprint 0 delivery |
| --- | --- |
| Goal interpretation | English and Chinese rules for Night, Away and Relax modes, plus an optional structured `campus-qwen` proposal path. |
| Safety boundary | The model proposes an intent only. `SmartHomeControlHandler` validates intent, parameters, devices and expected state before dispatch. |
| Device workflow | Simulated bedroom light, curtain, front-door lock and living-room air conditioner executed through the shared `DeviceAutomationAgent`. |
| Verification | Every action contains `expected_state`; returned state is checked independently before success is reported. |
| Failure handling | Offline devices, mismatched readback, malformed model output, timeouts and ambiguous goals are reported explicitly. |
| Sensitive request | Exterior-door unlock is blocked before dispatch because no approval interaction was connected in Sprint 0. |
| User interface | A Streamlit Smart Home Control page shows the interpreted intent, action results, final simulated states and agent trace. |
| Evidence | Workflow results can be appended to ignored `data/runtime/smart_home_control.jsonl`. |

## AR-02 / UC-02 flow

| UC-02 stage | Sprint 0 implementation |
| --- | --- |
| Resident provides a goal | `simulation.events.make_user_goal_event` and the Smart Home Control page |
| Coordinator interprets and routes it | `SmartHomeGoalInterpreter` -> `HomeCoordinatorAgent` |
| Domain validates the proposed goal | `SmartHomeControlHandler.plan_goal` |
| Devices execute the plan | Shared `DeviceAutomationAgent` and `SimulatedDeviceTool` |
| System verifies and reports results | Per-device readback plus `COMPLETE`, `PARTIAL`, `FAILED` or `CLARIFICATION_REQUIRED` outcome |

## Demonstration and test evidence

From the repository root:

```powershell
.venv\Scripts\python -m simulation.smart_home_demo --scenario good-night
.venv\Scripts\python -m simulation.smart_home_demo --scenario good-night --offline living-room-ac
.venv\Scripts\python -m simulation.smart_home_demo --scenario sensitive
.venv\Scripts\python -m unittest tests.test_smart_home_control tests.test_smart_home_ui -v
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m streamlit run app.py
```

At the Sprint 0 delivery point, 15 Smart Home Control tests and all 112 project
tests passed. The deterministic path and UI tests required no API key. Campus AI
request formatting was tested with controlled responses; a real university-
network call was not claimed.

## Items carried into Sprint 1

- Support the report's free-form, multi-device command rather than only fixed modes.
- Retry a failed action and continue later independent safe actions.
- Add an explicit approve/decline interaction for sensitive unlock requests.
- Introduce typed `SmartDevice` / `DeviceContext` models.
- Persist the verified `HomeMode` for later monitoring context.
- Rehearse deployment from the Canvas-submitted source and attach real Jira and Sprint Review evidence when those activities occur.
