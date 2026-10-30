# Stage 1 to Stage 2 traceability

Source: Group 11 Stage 1 report, sections 2, 3 and 5. Status describes the current prototype, not a claim that every optional feature or real device is implemented. Read with the actual test results and the demonstration script.

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
| MR-09 permitted plan, execution, verification, safety priority | `domains/energy_comfort/control.py`, `services/safety_state.py` | `test_release_controls.py`, `test_cross_domain_safety.py`, cross-page UI test | Implemented bounded simulated AC/curtain/light plans, fresh safety evidence and per-command checks. Physical effects/general replanning are not claimed |
| AR-01 / UC-01 fall response | Elderly page, confirmation, escalation | 18-case acceptance runner and optional live AI case | Implemented simulated fall, safe/help/unclear replies and failures |
| AR-02 / UC-02 multi-device command | Smart Home page, interpreter and plan | Smart Home unit/workflow/page tests | Implemented bounded bilingual goals, confirmation and verified state |
| AR-03 / UC-03 pet monitoring and feeding | Pet page, monitoring, optional feeder | Pet Sprint 2 acceptance tests | Core runs with optional feeder disabled/unavailable |
| AR-04 / UC-04 security response | Home Security page and domain policy | Home Security and external-warning tests | Simulated LOW/MEDIUM/HIGH response with approval and timeout semantics |
| AR-05 / UC-05 energy/comfort | Energy page and approved control panel | Energy assessment/control/cross-domain tests | Bounded plan implemented. Updated environmental sensors, quantified savings and general alternative-plan search remain incomplete |
| OR-01 intelligent feeding | `domains/pet_care/feeder.py` | `test_pet_sprint2.py` | Implemented simulated, explicit portion/flag; no physical feeder |
| OR-02 / UC-07 home modes | Smart Home modes and simulated state | Mode and multi-device tests | Partial: commands and mode state implemented; not one automatically synchronized mode across all independently editable pages |
| OR-03 / UC-06 important AI explanations | Model rationale, recorded trace, energy explanation helper | Campus prompt/validation and energy explanation tests | Implemented bounded local flow: shared coordinator request route, source-version checks, optional AI card organization, operator review, simpler responses and persistent request/history; see EXPLANATIONS.md |
| OR-04 multilevel escalation | Elderly escalation module/page | `test_elderly_escalation.py`, acceptance report | Implemented with simulated contacts/acknowledgements |
| OR-05 comfort/energy/safety explanation | `domains/energy_comfort/explanations.py`, Energy UI | `test_energy_comfort_explanations.py` | Implemented for recorded prototype evidence: context, selected strategy, safety priority, verified outcomes, missing effects, user request and persistent reviewed history |
| OR-06 external warnings | Warning source/area/time validation and security response | `test_external_warnings.py`, Home Security page tests | Implemented fictional trusted-feed simulation; no government warning subscription |
| NFR-01 safety | Parameter allowlists, sensitive confirmation, safety interlocks | Forgery/negation/protected-device/cross-domain tests | Passed tested cases; no real-home safety certification |
| NFR-02 classification performance | Elderly/security classification timing, AI evaluation | `docs/AI_EVALUATION.md` and raw fictional measurements | Measured; team must approve and document the final demonstration response budget. Do not call live AI subsecond |
| NFR-03 privacy | De-identified prompts, local credentials, ignored runtime logs | LLM payload/privacy tests | Tested for predefined fictional private fields; no raw camera integration |
| NFR-04 reliability | Failure reporting, fallback and independent readback | Shared/device/domain fault tests and AI fault evaluation | Passed defined failures; injected timeout is distinct from real network timeout |
| NFR-05 usability | Supported-goal interpretation or clarification | Smart Home/page tests and curated live evaluation | Tested sample coverage, not unrestricted language understanding |
| NFR-06 factual explanations | Evidence-bound explanations and uncertainty labels | Energy explanation tests | Evidence-bound explanation flow implemented and tested; missing measurements remain explicitly unknown |

## Demonstration use

Show one success and one failure/safety path for each person's actual contribution. For Energy success, obtain fresh clear Home Security and Elderly assessments immediately beforehand. Demonstrate hazardous security/external warnings after the energy success, then show the automatic block. Do not claim physical operation, measured savings or optional explanation routes that are absent.
