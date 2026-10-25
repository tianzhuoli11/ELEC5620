"""Resident-facing Elderly Safety page for AR-01 / UC-01.

Choose a simulated fall scenario, run it through the shared agents, answer
the resident confirmation (or let it time out), review the verified light
action and caregiver alert, then simulate the caregiver acknowledging or
not (multi-level escalation, OR-04). Nothing here operates a real device or
contacts a real person.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from domains.elderly_safety import default_devices
from domains.elderly_safety.confirmation import CONFIRMATION_TIMEOUT_S
from domains.elderly_safety.escalation import ACK_TIMEOUT_S
from domains.elderly_safety.integration import (
    DEFAULT_RECORD_PATH,
    acknowledge_alert,
    acknowledgement_timeout,
    build_workflow,
    operator_close_event,
    resume_elderly_safety,
    run_elderly_safety,
    start_escalation,
)
from simulation.devices import SimulatedDeviceTool
from simulation.elderly_scenarios import make_fall_scenario


SCENARIOS = {
    "Fall, still on the floor (90 s)": "high_floor",
    "Fall, then not moving (30 s)": "medium_wait",
    "Dropped something, standing again": "low_dropped_object",
    "Fall, inactivity sensor missing": "medium_missing_duration",
    "Brief stillness at night": "medium_night_uplift",
}
FAULTS = {
    "No simulated fault": False,
    "All room lights offline": True,
}
QUICK_REPLIES = {
    "I'm fine": "I'm fine, I just sat down.",
    "Help": "Help, I can't get up.",
    "Unclear": "hmm",
    "No (to 2nd question)": "no",
    "Yes (to 2nd question)": "yes",
}
ESCALATION_LABELS = {
    "AWAITING_ACK": "Waiting for acknowledgement",
    "RESOLVED": "Alert acknowledged — event resolved",
    "ESCALATION_FAILED": "No contact acknowledged — Human Operator informed, event open",
    "CLOSED_BY_OPERATOR": "Closed by the Human Operator",
}
OUTCOME_LABELS = {
    "COMPLETE": "Caregiver alerted and room light verified",
    "PARTIAL": "Help was needed but not every step completed",
    "FAILED": "Help was needed and the response failed",
    "AWAITING_CONFIRMATION": "Waiting for the resident to reply",
    "ASSESSED": "No alert needed",
}


def _clear_result() -> None:
    st.session_state.pop("elderly_result", None)


def _reset_demo() -> None:
    st.session_state.elderly_scenario = next(iter(SCENARIOS))
    st.session_state.elderly_fault = "No simulated fault"
    st.session_state.elderly_reply = ""
    _clear_result()


def _state_rows(states: dict[str, dict]) -> list[dict[str, str]]:
    return [
        {"Device": device_id, "Observed state": ", ".join(f"{k}={v}" for k, v in state.items())}
        for device_id, state in states.items()
    ]


def _run_scenario(scenario_label: str, fault_name: str) -> None:
    device_tool = SimulatedDeviceTool(default_devices())
    if FAULTS[fault_name]:
        device_tool.offline.update(device_tool.states)
    workflow, handler = build_workflow(device_tool=device_tool)
    event = make_fall_scenario(SCENARIOS[scenario_label])
    result = run_elderly_safety(event, workflow=workflow, handler=handler, record_path=DEFAULT_RECORD_PATH)
    st.session_state.elderly_result = {
        "workflow": result,
        "engine": workflow,
        "handler": handler,
        "device_tool": device_tool,
        "scenario": scenario_label,
        "fault": fault_name,
        "escalation": start_escalation(result, workflow=workflow, record_path=DEFAULT_RECORD_PATH),
    }


def _respond(reply: str | None) -> None:
    saved = st.session_state.get("elderly_result")
    if not isinstance(saved, dict) or saved["workflow"].pending_confirmation is None:
        raise ValueError("No Elderly Safety event is awaiting a reply")
    saved["workflow"] = resume_elderly_safety(
        saved["workflow"], reply,
        workflow=saved["engine"], handler=saved["handler"], record_path=DEFAULT_RECORD_PATH,
    )
    saved["escalation"] = start_escalation(saved["workflow"], workflow=saved["engine"], record_path=DEFAULT_RECORD_PATH)
    st.session_state.elderly_reply = ""


def _escalation_step(step: str) -> None:
    saved = st.session_state.get("elderly_result")
    state = saved.get("escalation") if isinstance(saved, dict) else None
    if state is None:
        raise ValueError("No caregiver alert is being tracked")
    if step == "ack":
        saved["escalation"] = acknowledge_alert(state, record_path=DEFAULT_RECORD_PATH)
    elif step == "timeout":
        saved["escalation"] = acknowledgement_timeout(state, workflow=saved["engine"], record_path=DEFAULT_RECORD_PATH)
    elif step == "close":
        note = st.session_state.get("elderly_operator_note", "").strip()
        saved["escalation"] = operator_close_event(state, note, record_path=DEFAULT_RECORD_PATH)
        st.session_state.elderly_operator_note = ""
    else:
        raise ValueError(step)


def _escalation_panel(state) -> None:
    st.markdown('<div class="panel-heading"><h2>Caregiver acknowledgement</h2>'
                '<span class="small-badge">SIMULATED CONTACTS</span></div>', unsafe_allow_html=True)
    label = ESCALATION_LABELS.get(state.status, state.status)
    (st.success if state.status in ("RESOLVED", "CLOSED_BY_OPERATOR")
     else st.error if state.status == "ESCALATION_FAILED" else st.info)(f"{state.status}: {label}")
    st.dataframe(
        [{"Level": a.level, "Contact": a.role, "Send": a.send_status,
          "Acknowledged": a.acknowledged, "Outcome": a.outcome} for a in state.attempts],
        hide_index=True, width="stretch",
    )
    if state.status == "AWAITING_ACK":
        current = state.current
        st.caption(f"Waiting up to {state.ack_timeout_seconds} s for the {current.role} to acknowledge.")
        ack, timeout = st.columns(2, gap="small")
        with ack:
            st.button(f"{current.role.capitalize()} acknowledged (simulated)", key="elderly-ack",
                      type="primary", on_click=_escalation_step, args=("ack",), width="stretch")
        with timeout:
            st.button(f"No acknowledgement ({state.ack_timeout_seconds} s)", key="elderly-ack-timeout",
                      on_click=_escalation_step, args=("timeout",), width="stretch")
    elif state.status == "ESCALATION_FAILED":
        st.text_input("Operator note", key="elderly_operator_note", placeholder="What the operator did")
        st.button("Operator closes event", key="elderly-operator-close", type="primary",
                  on_click=_escalation_step, args=("close",), width="stretch")


def _banner(result) -> None:
    name = result.outcome
    css = {"ASSESSED": "low", "AWAITING_CONFIRMATION": "medium", "COMPLETE": "medium", "PARTIAL": "high", "FAILED": "high"}.get(name, "high")
    st.markdown(
        f'<div class="result-banner risk-{css}"><span class="risk-label">{escape(name)} · '
        f'{escape(result.assessment.risk_level)} RISK</span>'
        f'<h3>{escape(OUTCOME_LABELS.get(name, name))}</h3>'
        f'<p>{escape(result.assessment.rationale)}</p></div>',
        unsafe_allow_html=True,
    )


def _send_typed_reply() -> None:
    _respond(st.session_state.get("elderly_reply", "").strip() or None)


def _confirmation_panel(result) -> None:
    pending = result.pending_confirmation
    st.warning(f"Asked the resident ({pending.attempt}/{pending.max_attempts}): **{pending.question}**")
    st.caption(f"The resident has {pending.timeout_seconds} s to reply. Use the timeout button to simulate silence.")
    st.text_input("Resident reply", key="elderly_reply", placeholder="Type what the resident says…")
    send, timeout = st.columns([1.4, 1], gap="small")
    with send:
        # Callbacks run before the page re-renders, so the reply box can be cleared safely.
        st.button("Send reply →", key="send-elderly-reply", type="primary", on_click=_send_typed_reply,
                  disabled=not st.session_state.get("elderly_reply", "").strip(), width="stretch")
    with timeout:
        st.button(f"No reply ({pending.timeout_seconds} s)", key="elderly-timeout", on_click=_respond,
                  args=(None,), width="stretch")
    st.caption("Quick replies")
    columns = st.columns(len(QUICK_REPLIES), gap="small")
    for column, (label, text) in zip(columns, QUICK_REPLIES.items()):
        with column:
            st.button(label, key=f"quick-{label}", on_click=_respond, args=(text,), width="stretch")


def render_elderly_safety() -> None:
    st.markdown(
        '<div class="page-heading"><h1>Elderly Safety</h1>'
        '<p>Simulate a suspected fall, confirm with the resident, and review the caregiver alert and verified room light.</p></div>',
        unsafe_allow_html=True,
    )

    controls, outcome = st.columns([1, 1.35], gap="medium")
    with controls:
        with st.container(border=True, key="elderly-controls"):
            st.markdown(
                '<div class="panel-heading"><h2>Simulate a fall</h2>'
                '<span class="small-badge">SIMULATED SENSORS</span></div>',
                unsafe_allow_html=True,
            )
            scenario = st.selectbox("Scenario", list(SCENARIOS), key="elderly_scenario", on_change=_clear_result)
            fault = st.selectbox("Failure simulation", list(FAULTS), key="elderly_fault", on_change=_clear_result)
            st.caption(
                "No model is called on this page, so the documented rule-based MEDIUM fallback applies: "
                "a low rule result still asks the resident."
            )
            run, reset = st.columns([1.6, 1], gap="small")
            with run:
                submitted = st.button("Run scenario →", key="run-elderly-scenario", type="primary", width="stretch")
            with reset:
                st.button("Reset demo", key="reset-elderly", on_click=_reset_demo, width="stretch")
            if submitted:
                try:
                    with st.spinner("Assessing the fall…"):
                        _run_scenario(scenario, fault)
                    st.rerun()
                except OSError:
                    _clear_result()
                    st.error("The scenario ran but its local audit record could not be saved.")
                except Exception as exc:
                    _clear_result()
                    st.error(f"The scenario failed safely before completion: {type(exc).__name__}.")

    with outcome:
        with st.container(border=True, key="elderly-result"):
            st.markdown('<div class="panel-heading"><h2>Response</h2></div>', unsafe_allow_html=True)
            saved = st.session_state.get("elderly_result")
            if not isinstance(saved, dict):
                st.markdown(
                    '<div class="result-placeholder"><span class="waiting-dot"></span>'
                    '<h3>Ready for a scenario</h3><p>Choose a fall scenario, then run it.</p></div>',
                    unsafe_allow_html=True,
                )
            else:
                result = saved["workflow"]
                _banner(result)
                fall = saved["handler"].fall_assessment
                if fall is not None:
                    st.caption(
                        f"Initial assessment: {fall.risk_level} · source {fall.evidence_source}"
                        f"{' · fallback' if fall.fallback_used else ''}"
                        f"{' · rules overrode model' if fall.policy_override else ''}"
                        f" · {fall.classification_ms:.2f} ms"
                    )
                if result.pending_confirmation is not None:
                    _confirmation_panel(result)

                if result.confirmation_replies:
                    st.dataframe(
                        [{"Attempt": r.attempt, "Reply": r.reply if r.reply is not None else "— (timeout)",
                          "Verdict": r.verdict, "Interpreted by": r.interpreted_by} for r in result.confirmation_replies],
                        hide_index=True, width="stretch",
                    )

                if result.notification_result is not None:
                    n = result.notification_result
                    text = f"Caregiver alert: {n.status} · acknowledged={n.acknowledged} · {n.detail}"
                    (st.error if n.status in ("FAILED", "UNAVAILABLE") else st.info)(text)

                escalation_state = saved.get("escalation")
                if escalation_state is not None:
                    _escalation_panel(escalation_state)

                if result.action_results:
                    st.dataframe(
                        [{"Device": a.device_id, "Accepted": a.accepted, "Verified": a.verified,
                          "Observed state": ", ".join(f"{k}={v}" for k, v in a.returned_state.items()) or "—",
                          "Error": a.error or "—"} for a in result.action_results],
                        hide_index=True, width="stretch",
                    )
                elif result.pending_confirmation is None:
                    st.caption("No device command was dispatched.")

                st.caption(f"Scenario: {saved['scenario']} · Failure simulation: {saved['fault']}")
                with st.expander("Current simulated light states"):
                    st.dataframe(_state_rows(saved["device_tool"].states), hide_index=True, width="stretch")
                with st.expander("Agent trace and audit evidence"):
                    st.dataframe(
                        [{"Agent": e.agent, "Step": e.outcome, "Time": e.timestamp} for e in result.trace],
                        hide_index=True, width="stretch",
                    )
                    st.json(result.to_dict())
                    if escalation_state is not None:
                        st.json(escalation_state.to_dict())

    st.markdown(
        f'<div class="section-line"><h2>How this page decides</h2><span>Prototype rules, not medical advice</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "- **HIGH** (impact and still ≥ 60 s, or on the floor ≥ 20 s): alert the caregiver and switch on the room light without asking.\n"
        f"- **MEDIUM**: ask *Are you okay?* and wait {CONFIRMATION_TIMEOUT_S} s. A safe reply closes the event; "
        "an unclear reply gets one follow-up question; help, a second unclear reply or no reply escalates.\n"
        "- **LOW**: record a false alarm only (with a model configured; without one the MEDIUM fallback asks the resident).\n"
        f"- **Escalation**: after an alert, wait {ACK_TIMEOUT_S} s for the primary caregiver, then the secondary contact. "
        "If nobody acknowledges, the Human Operator is informed and the event stays open until the operator closes it. "
        "A failed send moves to the next contact immediately."
    )
    st.caption("All sensors, lights and contacts on this page are simulated. Each run and reply is saved locally as audit evidence.")
