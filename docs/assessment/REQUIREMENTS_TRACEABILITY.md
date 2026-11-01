# Stage 1 to Stage 2 traceability

Source: Group 11 Stage 1 report, sections 2, 3 and 5. Status describes the current prototype, in which sensors, devices and notifications are simulated.

| Requirement | Prototype evidence | Acceptance evidence | Status / limits |
| --- | --- | --- | --- |
| MR-01 natural-language interaction | `services/smart_home_goals.py`, shared goal route | `test_smart_home_control.py`, `test_release_controls.py` | Implemented for bounded supported goals; negation/ambiguity asks for clarification |
| MR-02 three reusable agents | `agents/coordinator.py`, `monitoring.py`, `automation.py`, `graph.py` | `test_framework.py`, domain integration tests | Implemented through LangGraph; domains are not five separate agents |
| MR-03 household monitoring | Elderly, Pet, Home Security monitoring handlers | `test_elderly_safety.py`, `test_pet_monitoring.py`, `test_home_security.py` | Implemented with fictional sensor input |
| MR-04 device control | Shared automation, M2 device inventory | `test_smart_home_control.py`, failure/readback tests | Simulated devices only |
| MR-05 important-event notifications | Shared notification interface and simulated service | Pet/security/elderly failure and acknowledgement tests | Simulated delivery; no real recipient contacted |
| MR-06 agent delegation | Shared sensor and direct-goal graph paths | `test_framework.py`, agent trace assertions | Implemented; direct goals intentionally skip monitoring |
| MR-07 event/action records | Domain JSONL audit writers | Domain integration/page tests read actual temporary records | Implemented locally; separate domain histories, not one unified production audit service |
| MR-08 energy context assessment | `models/context.py`, energy assessment/integration | `test_energy_comfort.py`, assessment UI tests | Implemented; unknown values stay unknown |
| MR-09 permitted plan, execution, verification, safety priority | `domains/energy_comfort/control.py`, `services/safety_state.py` | `test_release_controls.py`, `test_cross_domain_safety.py`, cross-page UI test | Implemented bounded simulated AC/curtain/light plans, fresh safety evidence and per-command checks. Physical effects and general replanning are outside the prototype |
| AR-01 / UC-01 fall response | Elderly page, confirmation, escalation | [ELDERLY_SAFETY_ACCEPTANCE.md](../acceptance/ELDERLY_SAFETY_ACCEPTANCE.md) (18 cases), reply evaluation in AI_EVALUATION.md | Implemented simulated fall, safe/help/unclear replies and failures |
| AR-02 / UC-02 multi-device command | Smart Home page, interpreter and plan | 10-case `smart_home_acceptance` runner, generated acceptance report, unit/workflow/page tests | Implemented bounded bilingual goals, confirmation and verified state; simulated devices |
| AR-03 / UC-03 pet monitoring and feeding | Pet page, monitoring, optional feeder | [PET_CARE_ACCEPTANCE.md](../acceptance/PET_CARE_ACCEPTANCE.md), Pet Sprint 2 tests | Core runs with optional feeder disabled/unavailable |
| AR-04 / UC-04 security response | Home Security page and domain policy | [HOME_SECURITY_ACCEPTANCE.md](../acceptance/HOME_SECURITY_ACCEPTANCE.md), Home Security and external-warning tests | Simulated LOW/MEDIUM/HIGH response with approval and timeout semantics |
| AR-05 / UC-05 energy/comfort | Energy page and approved control panel | [ENERGY_COMFORT_ACCEPTANCE.md](../acceptance/ENERGY_COMFORT_ACCEPTANCE.md), Energy assessment/control/cross-domain tests | Bounded plan implemented and verified. Outside the prototype scope: physical environment sensors, measured savings and alternative-plan search |
| OR-01 intelligent feeding | `domains/pet_care/feeder.py` | `test_pet_sprint2.py` | Implemented simulated, explicit portion/flag; no physical feeder |
| OR-02 / UC-07 home modes | Smart Home modes and simulated state | Mode and multi-device tests | Partial: mode commands and mode state implemented; each page keeps its own mode rather than one synchronised mode |
| OR-03 / UC-06 important AI explanations | Model rationale, recorded trace, energy explanation helper | Campus prompt/validation and energy explanation tests | Implemented bounded local flow: shared coordinator request route, source-version checks, optional AI card organization, operator review, simpler responses and persistent request/history; see EXPLANATIONS.md |
| OR-04 multilevel escalation | Elderly escalation module/page | `test_elderly_escalation.py`, acceptance report | Implemented with simulated contacts/acknowledgements |
| OR-05 comfort/energy/safety explanation | `domains/energy_comfort/explanations.py`, Energy UI | `test_energy_comfort_explanations.py` | Implemented for recorded prototype evidence: context, selected strategy, safety priority, verified outcomes, missing effects, user request and persistent reviewed history |
| OR-06 external warnings | Warning source/area/time validation and security response | `test_external_warnings.py`, Home Security page tests | Implemented fictional trusted-feed simulation; no government warning subscription |
| NFR-01 safety | Parameter allowlists, sensitive confirmation, safety interlocks | Forgery/negation/protected-device/cross-domain tests | Passed tested cases; no real-home safety certification |
| NFR-02 classification performance | Elderly/security classification timing, AI evaluation | `docs/assessment/AI_EVALUATION.md` and raw fictional measurements | Measured. Elderly rule-path limit 1000 ms, checked by acceptance case AT-E17; live AI calls take seconds and are reported as such |
| NFR-03 privacy | De-identified prompts, local credentials, ignored runtime logs | LLM payload/privacy tests | Tested for predefined fictional private fields; no raw camera integration |
| NFR-04 reliability | Failure reporting, fallback and independent readback | Shared/device/domain fault tests and AI fault evaluation | Passed defined failures; injected timeout is distinct from real network timeout |
| NFR-05 usability | Supported-goal interpretation or clarification | Smart Home/page tests and curated live evaluation | Tested sample coverage, not unrestricted language understanding |
| NFR-06 factual explanations | Evidence-bound explanations and uncertainty labels | Energy explanation tests | Evidence-bound explanation flow implemented and tested; missing measurements remain explicitly unknown |

## Changes from the Stage 1 deployment design

Stage 1 section 11 described a phone app, a home server, a database server and a smart-home gateway, and noted that "for the Stage 2 prototype, the home server, database and gateway can run on a single machine, with sensors and devices simulated." The prototype follows that note. These are the differences from the full design, recorded as Stage 1 section 12.2 asks:

| Stage 1 design | Stage 2 prototype | Reason | Interface kept for later |
| --- | --- | --- | --- |
| `SmartHomeApp` on a phone, HTTPS and WebSocket push | Streamlit web dashboard on the same machine, one page per domain | Single-machine demonstration; one shared UI for five domains | Business logic is independent of Streamlit (`domains/`, `agents/`) |
| `dbServer` for events, assessments, actions and configuration | Append-only JSONL audit files in `data/runtime/` (git-ignored) | Stage 1 allows a single machine; local records keep resident data off any server | Each domain writes structured records that a database could store |
| `SmartHomeGateway` with Zigbee/Wi-Fi and MQTT over TLS | `SimulatedDeviceTool` with independent read-back, offline and mismatch faults | No physical devices; the device contract is the same | `tools/device.py` `DeviceTool` interface |
| `NotificationService` (external cloud) | Simulated notifications that are recorded, never sent | No real person is contacted in a demonstration | `services/notifications.py` interface |
| External `LLMProvider` | Course campus-qwen proxy; any OpenAI-compatible endpoint through `ELEC5620_BASE_URL` / `ELEC5620_MODEL` | Course-provided model; the Elderly reply evaluation used another provider after one member's course key was rejected (see AI_EVALUATION.md) | `services/campus_proxy.py`, `services/elderly_llm.py` |
| Real timers (30 s resident reply, 60 s acknowledgement) | Timeouts triggered by buttons on the page | A full escalation would otherwise take 2.5 minutes of waiting in the demonstration | The 30 s and 60 s values are part of the escalation state and tests |

## Demonstration use

Show one success and one failure/safety path for each person's actual contribution. For Energy success, obtain fresh clear Home Security and Elderly assessments immediately beforehand. Demonstrate hazardous security/external warnings after the energy success, then show the automatic block. Devices are simulated and energy savings are not measured.
