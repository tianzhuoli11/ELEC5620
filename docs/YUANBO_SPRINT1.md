# Yuanbo Zhang: Sprint 1 resident confirmation and caregiver notification (SCRUM-24)

UC-01 steps 5-6 and extensions 4-5 on the shared workflow. Everything is
**simulated**; no model is called by default and no real person is contacted.

```powershell
python -m unittest discover -s tests -v
python -m simulation.elderly_demo --scenario medium_wait                          # pauses with the first question
python -m simulation.elderly_demo --scenario medium_wait --reply "I'm fine"        # safe -> closed, no alert
python -m simulation.elderly_demo --scenario medium_wait --reply "help"            # help -> caregiver alert + room light
python -m simulation.elderly_demo --scenario medium_wait --reply "hmm" --reply "no"   # unclear -> second question -> safe
python -m simulation.elderly_demo --scenario medium_wait --reply "hmm" --reply "eh"   # unclear twice -> escalate
python -m simulation.elderly_demo --scenario medium_wait --timeout                 # no reply in 30 s -> escalate
```

## Flow

| Step | Where |
| --- | --- |
| MEDIUM assessment pauses the graph | `agents/graph.py` `pause` node; `WorkflowResult.pending_confirmation`, outcome `AWAITING_CONFIRMATION` |
| Question 1: "Are you okay? Please reply." (30 s) | `domains/elderly_safety/confirmation.py` |
| Reply interpreted: safe / help / unclear; `None` = timeout | `HomeCoordinatorAgent.interpret_reply` -> handler rules, optional model hook |
| Unclear once -> question 2: "Do you need me to contact your family? Please answer 'yes' or 'no'." | `max_attempts = 2` |
| Safe -> event closed, nothing sent | outcome `ASSESSED`, `confirmation_replies` recorded |
| Help, unclear twice or timeout -> escalate | `ElderlySafetyHandler.escalate`: assessment raised to HIGH, caregiver `NotificationRequest` + room light `ActionRequest` run through the normal execute/notify nodes |
| Caregiver acknowledgement | `NotificationResult.acknowledged` from the adapter; the simulated adapter reports `False` (nobody was contacted). Acknowledgement timeout and multi-level escalation are SCRUM-25. |

Design rules: silence is never "safe"; a model verdict may not turn an
obvious help request into "safe"; the model only sees the reply text and the
attempt number (NFR-03); the graph runs no timers, the UI/simulation decides
when 30 s have passed and calls `resume(result, None)`.

## Shared changes (additive, existing tests unchanged)

- `models/workflow.py`: `PendingConfirmation`, `ConfirmationReply`; `WorkflowResult.pending_confirmation`, `.confirmation_replies`, outcome `AWAITING_CONFIRMATION`, both in `to_dict()`.
- `domains/base.py`: optional `ConfirmationHandler` protocol and `supports_confirmation()`.
- `agents/coordinator.py`: `ask_resident`, `interpret_reply`, `escalate` (validation of domain output).
- `agents/graph.py`: `pause` and `confirm` nodes, `route_kind == "confirm"`, `SmartHomeWorkflow.resume()`. Domains that do not implement the protocol behave exactly as before.
- `docs/INTERFACES.md`, `docs/INTEGRATION_GUIDE.md`: one section each.

## Tests

`tests/test_elderly_confirmation.py` (20): rule interpreter, model fallback
and privacy, safe / help / unclear-then-safe / unclear-twice / timeout /
notification-failure paths, trace continuity, resume guard, HIGH never
pauses, Pet Care unaffected. Full suite: 88 (+ `test_ui` with Streamlit).

## Streamlit page

`ui/elderly_safety.py`, registered in `ui/domain_views.py` (sidebar: Elderly Safety).
Run `streamlit run app.py`. Choose a scenario and optional "All room lights
offline" fault, run it, then reply by typing, with quick replies, or with
"No reply (30 s)". The page shows the risk banner, initial assessment source,
reply history, caregiver alert status, verified light result and the agent
trace. Each run and reply is appended to `data/runtime/elderly_safety.jsonl`
(git-ignored) through `domains/elderly_safety/integration.py`.
`tests/test_elderly_ui.py` (6 Streamlit AppTest cases) covers registration,
HIGH, safe reply, typed help, unclear then timeout, offline lights.

## Not done yet

- Caregiver acknowledgement timeout, next-level contact, Human Operator notice (SCRUM-25).
- Model-drafted alert text checked by the coordinator (UC-01 step 7); the alert is rule text describing the condition only.
- Real campus-qwen reply interpreter (hook exists: `ElderlySafetyHandler(reply_interpreter=...)`).
