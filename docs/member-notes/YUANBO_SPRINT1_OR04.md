# Yuanbo Zhang: Sprint 1 multi-level emergency escalation (SCRUM-25, optional OR-04)

UC-01 step 9 and extension 6. All contacts are **fictional and simulated**;
no real person is contacted.

```powershell
python -m unittest tests.test_elderly_escalation -v
python -m simulation.elderly_demo --scenario high_floor --ack                    # primary caregiver acknowledges
python -m simulation.elderly_demo --scenario high_floor --ack-timeouts 1 --ack   # secondary contact acknowledges
python -m simulation.elderly_demo --scenario high_floor --ack-timeouts 2         # operator informed, event open
python -m simulation.elderly_demo --scenario medium_wait --timeout --ack-timeouts 1 --ack
streamlit run app.py                                                             # Elderly Safety -> acknowledgement panel
```

## Policy

| Level | Contact (fictional) | Wait for acknowledgement |
| --- | --- | --- |
| 1 | primary caregiver (`fictional-primary-caregiver`) | 60 s |
| 2 | secondary contact (`fictional-family-member`) | 60 s |
| after 2 | Human Operator (`fictional-human-operator`) informed | event stays open until the operator closes it |

- Level 1 is the alert the shared workflow already sent (HIGH fall, or MEDIUM escalated after the resident's reply).
- A send that returns `FAILED` / `UNAVAILABLE` (or an adapter exception) moves to the next level immediately, without waiting.
- A sent or simulated alert is **never** treated as acknowledged. Only an explicit acknowledgement counts: `NotificationResult.acknowledged=True` from a real adapter, or the "acknowledged (simulated)" button / `--ack` flag.
- The graph runs no timers; the UI or simulation decides when 60 s have passed.

## Implementation

| File | Content |
| --- | --- |
| `domains/elderly_safety/escalation.py` | Immutable `EscalationState` / `ContactAttempt`; `start`, `acknowledge`, `advance` (timeout or failed send), `operator_close`. Statuses `AWAITING_ACK`, `RESOLVED`, `ESCALATION_FAILED`, `CLOSED_BY_OPERATOR`. |
| `domains/elderly_safety/integration.py` | `start_escalation`, `acknowledge_alert`, `acknowledgement_timeout`, `operator_close_event`; each step appends an `elderly_escalation` record to `data/runtime/elderly_safety.jsonl`. |
| `agents/graph.py` | One additive method, `SmartHomeWorkflow.notify(request)`, so follow-up alerts also go through `HomeCoordinatorAgent` (validation and failure reporting identical to the graph's notify node). |
| `ui/elderly_safety.py` | Acknowledgement panel: contact table, "acknowledged (simulated)", "No acknowledgement (60 s)", operator note and close. |
| `simulation/elderly_demo.py` | `--ack-timeouts N` and `--ack`. |
| `tests/test_elderly_escalation.py`, `tests/test_elderly_ui.py` | 12 escalation tests; 3 more page tests. |

## Campus model (UC-01 steps 3 and 6)

`services/elderly_llm.py` calls campus-qwen for the fall risk proposal and the
reply interpretation, reusing `CampusProxyConfig` from `services/campus_proxy.py`.
Only `FallContext.for_llm()` (room category, timing, sensor values) and the
reply text with its attempt number are sent (NFR-03). Rules keep the final
say: a proposal may confirm or raise the risk, never lower it; a model may not
turn an obvious help request into "safe"; timeouts, network errors and
non-JSON output use the documented fallback.

Enable it with the page's "AI options → Use campus AI when available" toggle or
`python -m simulation.elderly_demo ... --use-campus-llm`. Without a key the
page says so and runs rules only.

Default tests patch the HTTP call (`tests/test_elderly_llm.py`, 10 tests).
The live test is opt-in and must be run on the campus network / USYD VPN:

```powershell
$env:ELEC5620_API_KEY = "<your key>"
$env:ELEC5620_RUN_REAL_PROXY = "1"
python -m unittest tests.test_elderly_llm -v
```

Record the live result (date, model verdicts, whether rules overrode) in Jira;
never paste the key.

## Not done yet

- A real notification adapter that reports delivery and acknowledgement (Yan Li's `NotificationService`); the flow already reads `acknowledged` from it.
- Contact list configuration from settings instead of the fixed fictional list.
