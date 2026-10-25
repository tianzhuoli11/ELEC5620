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

## Not done yet

- A real notification adapter that reports delivery and acknowledgement (Yan Li's `NotificationService`); the flow already reads `acknowledged` from it.
- Contact list configuration from settings instead of the fixed fictional list.
