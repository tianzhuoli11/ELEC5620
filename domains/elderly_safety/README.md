# Elderly Safety

Owner: Yuanbo Zhang. Requirements: AR-01 / UC-01; optional OR-04. Jira: SCRUM-12, SCRUM-24, SCRUM-25, SCRUM-34.

Detects a suspected fall from simulated sensor readings, asks the resident to confirm, alerts a caregiver when help is needed, switches on the light at the fall location, and escalates through further contacts when nobody acknowledges. Everything runs through the shared three-agent workflow. **Sensors, lights and contacts are simulated; no real device is operated and no real person is contacted.**

## Run it

From the repository root, after `pip install -r requirements.txt` (on Windows use `.venv\Scripts\python` as in the root README):

```powershell
python -m streamlit run app.py                                                  # sidebar: Elderly Safety
python -m simulation.elderly_demo --list                                        # scenarios and their rule levels
python -m simulation.elderly_demo --scenario high_floor                         # HIGH: alert + light, no question
python -m simulation.elderly_demo --scenario medium_wait --reply "I'm fine"     # MEDIUM: safe reply closes the event
python -m simulation.elderly_demo --scenario medium_wait --reply "help"         # help: escalate, alert + light
python -m simulation.elderly_demo --scenario medium_wait --reply "hmm" --reply "no"   # unclear: follow-up question
python -m simulation.elderly_demo --scenario medium_wait --timeout              # no reply in 30 s: escalate
python -m simulation.elderly_demo --scenario high_floor --offline               # light offline: FAILED, alert still sent
python -m simulation.elderly_demo --scenario high_floor --ack-timeouts 2        # nobody acknowledges: operator informed
python -m simulation.elderly_acceptance                                         # 18 acceptance cases -> docs/acceptance/
python -m unittest tests.test_elderly_safety tests.test_elderly_integration tests.test_elderly_confirmation tests.test_elderly_escalation tests.test_elderly_llm tests.test_elderly_acceptance -v
```

No API key is needed. Without a model the documented rule-based MEDIUM fallback applies, so a low rule result still asks the resident.

### Optional campus AI

The model proposes a fall risk level and interprets the resident's reply; rules keep the final say (a proposal may confirm or raise risk, never lower it, and an obvious help request is never turned into "safe"). The campus proxy address is on the university's internal network, so connect to the campus network or USYD VPN first.

```powershell
$env:ELEC5620_API_KEY = "<your key>"                                            # never commit or screenshot the key
python -m simulation.elderly_demo --scenario medium_wait --reply "I'm okay, just resting" --use-campus-llm
python -m simulation.elderly_acceptance --use-campus-llm                        # adds live case AT-E19
$env:ELEC5620_RUN_REAL_PROXY = "1"; python -m unittest tests.test_elderly_llm -v
```

In the Streamlit page use **AI options → Use campus AI when available**. Without a key, or when the proxy times out or returns invalid output, the page says so and runs rules only.

## Behaviour

| Situation | Response |
| --- | --- |
| Impact and no motion ≥ 60 s, or on the floor ≥ 20 s | HIGH: caregiver alert and room light, without asking |
| Impact and no motion ≥ 20 s, or a reading missing | MEDIUM: ask "Are you okay? Please reply." and wait 30 s |
| Upright again / motion within seconds | LOW: record a false alarm (MEDIUM without a model) |
| Safe reply | Close the event, nothing sent |
| Unclear reply | Ask "Do you need me to contact your family? Please answer 'yes' or 'no'." once |
| Help, second unclear reply, or no reply in 30 s | Escalate to HIGH: alert and light |
| No acknowledgement within 60 s | Contact the secondary contact; then inform the Human Operator and keep the event open until the operator closes it |

Thresholds are prototype values, not medical advice. The model only receives de-identified data (room category, timing, sensor values; never names, addresses, contacts or event IDs). Each run, reply and escalation step is appended to the git-ignored `data/runtime/elderly_safety.jsonl`.

## Files

| Path | Content |
| --- | --- |
| `context.py`, `rules.py`, `policy.py`, `assessment.py` | Context collection, deterministic rules, policy floor and MEDIUM fallback, `assess_fall` |
| `confirmation.py`, `handler.py` | Resident questions and reply interpretation; `ElderlySafetyHandler` for the shared workflow |
| `escalation.py`, `integration.py` | Multi-level acknowledgement escalation; run / resume / escalate with audit records |
| `services/elderly_llm.py` | Optional campus-qwen calls |
| `ui/elderly_safety.py` | Streamlit page |
| `simulation/elderly_scenarios.py`, `elderly_demo.py`, `elderly_acceptance.py` | Scenarios, CLI demo, acceptance run |
| `data/samples/elderly_fall_*.json` | Labelled fictional fixtures |

Evidence: [Sprint 0](../../docs/YUANBO_SPRINT0.md), [Sprint 1](../../docs/YUANBO_SPRINT1.md), [OR-04 and campus AI](../../docs/YUANBO_SPRINT1_OR04.md), [acceptance report](../../docs/acceptance/ELDERLY_SAFETY_ACCEPTANCE.md).

Reuse `models/`, `agents/`, `services/` and `tools/`; do not duplicate the shared agent framework. Tests belong in `tests/`, fixtures in `data/samples/`, and views in `ui/`.
