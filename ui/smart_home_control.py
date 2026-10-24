"""Resident-facing Smart Home Control page for AR-02 / UC-02."""

from __future__ import annotations

from html import escape
import os

import streamlit as st

from domains.smart_home_control import (
    DEFAULT_RECORD_PATH,
    HomeModeState,
    default_device_states,
    resume_smart_home_confirmation,
    run_smart_home_control,
)
from services.campus_proxy import CampusProxyConfig, propose_smart_home_goal
from simulation.devices import SimulatedDeviceTool
from simulation.events import make_user_goal_event


SCENARIOS = {
    "Good night": "I'm going to sleep. Please prepare the home for the night.",
    "Leaving home": "I'm leaving home now. Put the house into away mode.",
    "Relax mode": "I want to relax and watch a movie.",
    "Sensitive action": "Unlock the front door.",
    "Custom request": "",
}
FAULTS = {
    "No simulated fault": None,
    "Air conditioner offline": "living-room-ac",
    "Bedroom light offline": "bedroom-light",
}
OUTCOME_LABELS = {
    "COMPLETE": "Requested state verified",
    "PARTIAL": "Some actions could not be completed",
    "FAILED": "No approved plan was completed",
    "AWAITING_CONFIRMATION": "Confirmation is required before execution",
    "CLARIFICATION_REQUIRED": "More information is required",
    "ASSESSED": "Request assessed without device action",
}


def _clear_result() -> None:
    st.session_state.pop("smart_home_result", None)


def _scenario_changed() -> None:
    st.session_state.smart_home_text = SCENARIOS[st.session_state.smart_home_scenario]
    _clear_result()


def _reset_demo() -> None:
    st.session_state.smart_home_scenario = "Good night"
    st.session_state.smart_home_text = SCENARIOS["Good night"]
    st.session_state.smart_home_fault = "No simulated fault"
    st.session_state.smart_home_use_ai = False
    st.session_state.smart_home_mode_state = HomeModeState()
    _clear_result()


def _state_rows(states: dict[str, dict]) -> list[dict[str, str]]:
    return [
        {"Device": device_id, "Observed state": ", ".join(f"{key}={value}" for key, value in state.items())}
        for device_id, state in states.items()
    ]


def _run_request(text: str, use_ai: bool, fault_name: str) -> None:
    mode_state = st.session_state.get("smart_home_mode_state")
    if not isinstance(mode_state, HomeModeState):
        mode_state = HomeModeState()
        st.session_state.smart_home_mode_state = mode_state
    device_tool = SimulatedDeviceTool(default_device_states())
    offline_device = FAULTS[fault_name]
    if offline_device:
        device_tool.offline.add(offline_device)

    provider = None
    ai_configured = False
    if use_ai and os.getenv("ELEC5620_API_KEY", "").strip():
        config = CampusProxyConfig.from_environment()
        provider = lambda event: propose_smart_home_goal(event, config)
        ai_configured = True

    result = run_smart_home_control(
        make_user_goal_event(text),
        device_tool=device_tool,
        proposal_provider=provider,
        mode_state=mode_state,
        record_path=DEFAULT_RECORD_PATH,
    )
    st.session_state.smart_home_result = {
        "workflow": result,
        "device_tool": device_tool,
        "mode_state": mode_state,
        "states": device_tool.states,
        "fault": fault_name,
        "requested_ai": use_ai,
        "ai_configured": ai_configured,
    }


def _respond_to_sensitive_action(approved: bool) -> None:
    saved = st.session_state.get("smart_home_result")
    if not isinstance(saved, dict):
        raise ValueError("No Smart Home Control result is awaiting confirmation")
    result = resume_smart_home_confirmation(
        saved["workflow"],
        approved=approved,
        device_tool=saved["device_tool"],
        mode_state=saved["mode_state"],
        record_path=DEFAULT_RECORD_PATH,
    )
    saved["workflow"] = result
    saved["states"] = saved["device_tool"].states


def render_smart_home_control() -> None:
    st.markdown(
        '<div class="page-heading"><h1>Smart Home Control</h1>'
        '<p>Describe a desired home state, then review the plan and independently verified device results.</p></div>',
        unsafe_allow_html=True,
    )

    controls, outcome = st.columns([1, 1.35], gap="medium")
    with controls:
        with st.container(border=True, key="smart-home-controls"):
            st.markdown(
                '<div class="panel-heading"><h2>Run a home command</h2>'
                '<span class="small-badge">SIMULATED DEVICES</span></div>',
                unsafe_allow_html=True,
            )
            mode_state = st.session_state.get("smart_home_mode_state")
            current_mode = mode_state.current_mode if isinstance(mode_state, HomeModeState) else "HOME"
            st.caption(f"Current HomeMode: {current_mode}")
            selected = st.selectbox(
                "Scenario",
                list(SCENARIOS),
                key="smart_home_scenario",
                on_change=_scenario_changed,
            )
            if "smart_home_text" not in st.session_state:
                st.session_state.smart_home_text = SCENARIOS[selected]
            text = st.text_area(
                "Natural-language request",
                key="smart_home_text",
                height=96,
                on_change=_clear_result,
            )
            fault_name = st.selectbox(
                "Failure simulation",
                list(FAULTS),
                key="smart_home_fault",
                on_change=_clear_result,
            )
            with st.expander("AI options"):
                use_ai = st.toggle(
                    "Use campus AI when available",
                    key="smart_home_use_ai",
                    value=False,
                    on_change=_clear_result,
                )
                if use_ai and not os.getenv("ELEC5620_API_KEY", "").strip():
                    st.caption("No API key is configured. The safe bilingual rule fallback will be used.")
            run, reset = st.columns([1.6, 1], gap="small")
            with run:
                submitted = st.button(
                    "Run command →",
                    key="run-smart-home-command",
                    type="primary",
                    disabled=not text.strip(),
                    width="stretch",
                )
            with reset:
                st.button("Reset demo", key="reset-smart-home", on_click=_reset_demo, width="stretch")
            if submitted:
                try:
                    with st.spinner("Interpreting, planning and verifying…"):
                        _run_request(text, use_ai, fault_name)
                    st.rerun()
                except OSError:
                    _clear_result()
                    st.error("The command completed but its local audit record could not be saved.")
                except Exception as exc:
                    _clear_result()
                    st.error(f"The request failed safely before completion: {type(exc).__name__}.")

    with outcome:
        with st.container(border=True, key="smart-home-result"):
            st.markdown('<div class="panel-heading"><h2>Verified result</h2></div>', unsafe_allow_html=True)
            saved = st.session_state.get("smart_home_result")
            if not isinstance(saved, dict):
                st.markdown(
                    '<div class="result-placeholder"><span class="waiting-dot"></span>'
                    '<h3>Ready for a command</h3><p>Choose a scenario or enter a request, then run it.</p></div>',
                    unsafe_allow_html=True,
                )
            else:
                result = saved["workflow"]
                outcome_name = result.outcome
                css = "low" if outcome_name == "COMPLETE" else "medium" if outcome_name in ("PARTIAL", "CLARIFICATION_REQUIRED", "AWAITING_CONFIRMATION") else "high"
                st.markdown(
                    f'<div class="result-banner risk-{css}"><span class="risk-label">{escape(outcome_name)}</span>'
                    f'<h3>{escape(OUTCOME_LABELS.get(outcome_name, outcome_name))}</h3>'
                    f'<p>{escape(result.assessment.rationale)}</p></div>',
                    unsafe_allow_html=True,
                )
                if result.goal:
                    st.caption(f"Interpreted intent: {result.goal.intent} · {result.goal.evidence}")
                if result.goal and result.goal.clarification_question:
                    st.warning(result.goal.clarification_question)
                if result.pending_confirmation is not None:
                    st.warning(result.pending_confirmation.question)
                    approve, decline = st.columns(2, gap="small")
                    with approve:
                        if st.button("Approve unlock", key="approve-smart-home-sensitive", type="primary", width="stretch"):
                            _respond_to_sensitive_action(True)
                            st.rerun()
                    with decline:
                        if st.button("Keep door locked", key="decline-smart-home-sensitive", width="stretch"):
                            _respond_to_sensitive_action(False)
                            st.rerun()
                elif result.assessment.requires_human_review:
                    st.warning("Sensitive action remains blocked; no device command was sent.")
                if saved["requested_ai"] and not saved["ai_configured"]:
                    st.info("Campus AI was requested but no key was available; the deterministic fallback handled this command.")

                if result.action_results:
                    rows = []
                    for action in result.action_results:
                        rows.append({
                            "Device": action.device_id,
                            "Accepted": action.accepted,
                            "Verified": action.verified,
                            "Observed state": ", ".join(f"{key}={value}" for key, value in action.returned_state.items()) or "—",
                            "Error": action.error or "—",
                        })
                    st.dataframe(rows, hide_index=True, width="stretch")
                else:
                    st.caption("No device command was dispatched.")
                st.caption(f"Failure simulation: {saved['fault']}")
                with st.expander("Current simulated device states"):
                    st.dataframe(_state_rows(saved["states"]), hide_index=True, width="stretch")
                with st.expander("Agent trace and audit evidence"):
                    st.json(result.to_dict())

    st.markdown('<div class="section-line"><h2>Demo device inventory</h2><span>Fresh state is used for each command</span></div>', unsafe_allow_html=True)
    st.dataframe(_state_rows(default_device_states()), hide_index=True, width="stretch")
    st.caption("All actions on this page are simulated. The command, plan, readback and result are saved locally as audit evidence.")
