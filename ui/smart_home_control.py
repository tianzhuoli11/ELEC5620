"""Resident-facing Smart Home Control page for AR-02 / UC-02."""

from __future__ import annotations

from html import escape
import os
from time import perf_counter

import streamlit as st

from domains.smart_home_control import (
    AWAY_MODE_TEMPERATURE_C,
    DEFAULT_RECORD_PATH,
    HomeModeState,
    NIGHT_MODE_TEMPERATURE_C,
    RELAX_MODE_TEMPERATURE_C,
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
SCENARIO_DETAILS = {
    "Good night": {
        "label": "Core UC-02 example",
        "description": (
            "Turns off the bedroom light, closes the bedroom curtain, locks the front door, "
            f"and sets the air conditioner to sleep mode at {NIGHT_MODE_TEMPERATURE_C} °C. HomeMode changes to NIGHT "
            "only after all returned device states are verified."
        ),
    },
    "Leaving home": {
        "label": "Optional HomeMode demonstration",
        "description": (
            "Secures the home, closes the curtain, and runs the air conditioner in eco mode "
            f"at {AWAY_MODE_TEMPERATURE_C} °C. This energy-saving standby assumes another resident or pet may "
            "remain at home. HomeMode changes to AWAY only after every requested state is verified."
        ),
    },
    "Relax mode": {
        "label": "Additional comfort preset",
        "description": (
            "Sets the bedroom light to 40%, closes the curtain, and runs the air conditioner "
            f"in comfort mode at {RELAX_MODE_TEMPERATURE_C} °C. The front-door lock is not changed."
        ),
    },
    "Sensitive action": {
        "label": "UC-02 sensitive-action path",
        "description": (
            "Requests a front-door unlock. No device command is sent until the resident gives "
            "explicit confirmation; declining keeps the door locked."
        ),
    },
    "Custom request": {
        "label": "Custom natural-language command",
        "description": (
            "Enter a supported home mode or device request. Ambiguous commands ask for "
            "clarification, and unsupported commands do not operate a device."
        ),
    },
}
PRESET_POLICY_NOTE = (
    "Mode defaults are configurable simulated cooling presets: Relax 23 °C, Night 24 °C, and Away Eco 26 °C. "
    "Away does not assume the home is empty; use a custom request when the air conditioner should be off."
)
SCENARIO_INTENTS = {
    "Good night": "night_mode",
    "Leaving home": "away_mode",
    "Relax mode": "relax_mode",
    "Sensitive action": "unlock_door",
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
DEVICE_LABELS = {
    "bedroom-light": "Bedroom light",
    "bedroom-curtain": "Bedroom curtain",
    "front-door-lock": "Front door lock",
    "living-room-ac": "Living-room air conditioner",
}
INTENT_LABELS = {
    "night_mode": "Night mode",
    "away_mode": "Away mode",
    "relax_mode": "Relax mode",
    "unlock_door": "Front-door unlock",
    "direct_control": "Direct device control",
    "clarification_required": "Clarification required",
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
    st.session_state.smart_home_device_tool = SimulatedDeviceTool(default_device_states())
    _clear_result()


def _friendly_state(state: dict) -> str:
    labels = {
        "power": lambda value: f"Power {value}",
        "brightness": lambda value: f"Brightness {value}%",
        "position": lambda value: str(value).capitalize(),
        "locked": lambda value: "Locked" if value else "Unlocked",
        "mode": lambda value: f"{str(value).capitalize()} mode",
        "temperature_c": lambda value: f"{value} °C",
    }
    parts: list[str] = []
    combined_light_state = str(state.get("power", "")).lower() == "off" and "brightness" in state
    if combined_light_state:
        parts.append(f'Power off (saved brightness: {state["brightness"]}%)')
    for key, value in state.items():
        if combined_light_state and key in ("power", "brightness"):
            continue
        parts.append(labels.get(key, lambda item: f"{key}={item}")(value))
    return "; ".join(parts)


def _state_rows(states: dict[str, dict]) -> list[dict[str, str]]:
    return [
        {
            "Device": DEVICE_LABELS.get(device_id, device_id),
            "Observed state": _friendly_state(state),
        }
        for device_id, state in states.items()
    ]


def _effective_scenario(selected: str, text: str) -> str:
    """Treat an edited preset as a custom request, not as evidence for that preset."""

    preset_text = SCENARIOS.get(selected, "")
    if selected != "Custom request" and text.strip() == preset_text.strip():
        return selected
    return "Custom request"


def _result_title(outcome: str, intent: str | None) -> str:
    if outcome == "COMPLETE":
        return {
            "night_mode": "Night mode activated and verified",
            "away_mode": "Away mode activated and verified",
            "relax_mode": "Relax mode activated and verified",
            "unlock_door": "Front door unlock verified",
            "direct_control": "Requested device state verified",
        }.get(intent or "", OUTCOME_LABELS[outcome])
    return OUTCOME_LABELS.get(outcome, outcome)


def _result_summary(result) -> str:
    total = len(result.action_results)
    verified = sum(action.success for action in result.action_results)
    if result.outcome == "COMPLETE" and total:
        return f"{verified} of {total} planned device changes were accepted and verified from returned device states."
    if result.outcome == "PARTIAL":
        return f"{verified} of {total} device changes were verified. Review the incomplete operation below."
    if result.outcome == "FAILED":
        return "No requested device change could be verified as complete."
    if result.outcome == "AWAITING_CONFIRMATION":
        return "The plan contains a sensitive action. No device command has been sent yet."
    if result.outcome == "CLARIFICATION_REQUIRED":
        return "The request was not clear enough to create a safe device plan. No device command was sent."
    return "The request was assessed without dispatching a device command."


def _decision_source(saved: dict, evidence: str) -> str:
    lowered = evidence.lower()
    if saved["requested_ai"] and not saved["ai_configured"]:
        return "Safe rule fallback (campus AI unavailable)"
    if "campus qwen structured proposal" in lowered:
        return "Campus AI proposal + deterministic policy validation"
    if "fallback" in lowered:
        return "Safe deterministic rule fallback"
    return "Deterministic bilingual rules + policy validation"


def _result_rows(result) -> list[dict[str, str]]:
    rows = []
    for action in result.action_results:
        rows.append({
            "Device": DEVICE_LABELS.get(action.device_id, action.device_id),
            "Result": "Verified" if action.success else "Not verified",
            "Observed state": _friendly_state(action.returned_state) if action.returned_state else "No state returned",
            "Issue": action.error or "-",
        })
    return rows


def _result_table_html(result) -> str:
    rows = []
    for row in _result_rows(result):
        status_class = "verified" if row["Result"] == "Verified" else "failed"
        issue = "" if row["Issue"] == "-" else f'<small>{escape(row["Issue"])}</small>'
        rows.append(
            '<div class="device-result-row">'
            f'<strong>{escape(row["Device"])}</strong>'
            f'<span class="device-status {status_class}">{escape(row["Result"])}</span>'
            f'<span class="device-observed">{escape(row["Observed state"])}{issue}</span>'
            '</div>'
        )
    return '<div class="device-results">' + "".join(rows) + '</div>'


def _plain_language_reason(result) -> str:
    intent = result.goal.intent if result.goal else None
    total = len(result.action_results)
    verified = sum(action.success for action in result.action_results)
    intent_text = INTENT_LABELS.get(intent or "", "The request")
    if result.outcome == "COMPLETE" and total:
        return (
            f"{intent_text} produced a permitted {total}-device plan. Each device returned a state "
            "that matched the requested target."
        )
    if result.outcome == "PARTIAL":
        return (
            f"{intent_text} produced a permitted plan. {verified} of {total} returned device states "
            "matched their targets; the remaining operation is identified below."
        )
    if result.outcome == "AWAITING_CONFIRMATION":
        return "Unlocking a door is sensitive, so the system paused before sending any device command."
    if result.outcome == "CLARIFICATION_REQUIRED":
        return "The request did not identify one safe, supported goal, so no device command was sent."
    return "The workflow did not receive enough verified evidence to claim successful device control."


def _device_tool() -> SimulatedDeviceTool:
    tool = st.session_state.get("smart_home_device_tool")
    if not isinstance(tool, SimulatedDeviceTool):
        tool = SimulatedDeviceTool(default_device_states())
        st.session_state.smart_home_device_tool = tool
    return tool


def _run_request(text: str, use_ai: bool, fault_name: str, selected_scenario: str) -> None:
    mode_state = st.session_state.get("smart_home_mode_state")
    if not isinstance(mode_state, HomeModeState):
        mode_state = HomeModeState()
        st.session_state.smart_home_mode_state = mode_state
    device_tool = _device_tool()
    device_tool.offline.clear()
    offline_device = FAULTS[fault_name]
    if offline_device:
        device_tool.offline.add(offline_device)

    provider = None
    ai_configured = False
    if use_ai and os.getenv("ELEC5620_API_KEY", "").strip():
        config = CampusProxyConfig.from_environment()
        provider = lambda event: propose_smart_home_goal(event, config)
        ai_configured = True

    mode_before = mode_state.current_mode
    started = perf_counter()
    result = run_smart_home_control(
        make_user_goal_event(text),
        device_tool=device_tool,
        proposal_provider=provider,
        mode_state=mode_state,
        record_path=DEFAULT_RECORD_PATH,
    )
    elapsed_ms = (perf_counter() - started) * 1000
    st.session_state.smart_home_result = {
        "workflow": result,
        "device_tool": device_tool,
        "mode_state": mode_state,
        "states": device_tool.states,
        "fault": fault_name,
        "requested_ai": use_ai,
        "ai_configured": ai_configured,
        "submitted_scenario": _effective_scenario(selected_scenario, text),
        "submitted_request": text.strip(),
        "mode_before": mode_before,
        "mode_after": mode_state.current_mode,
        "workflow_ms": elapsed_ms,
    }


def _respond_to_sensitive_action(approved: bool) -> None:
    saved = st.session_state.get("smart_home_result")
    if not isinstance(saved, dict):
        raise ValueError("No Smart Home Control result is awaiting confirmation")
    started = perf_counter()
    result = resume_smart_home_confirmation(
        saved["workflow"],
        approved=approved,
        device_tool=saved["device_tool"],
        mode_state=saved["mode_state"],
        record_path=DEFAULT_RECORD_PATH,
    )
    saved["workflow"] = result
    saved["states"] = saved["device_tool"].states
    saved["mode_after"] = saved["mode_state"].current_mode
    saved["workflow_ms"] += (perf_counter() - started) * 1000


def render_smart_home_control() -> None:
    st.markdown(
        '<div class="page-heading"><h1>Smart Home Control</h1>'
        '<p>Give one natural-language goal. The coordinator interprets it, the automation agent applies a safe plan, '
        'and returned device states are independently verified.</p></div>',
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
            st.caption(PRESET_POLICY_NOTE)
            mode_state = st.session_state.get("smart_home_mode_state")
            current_mode = mode_state.current_mode if isinstance(mode_state, HomeModeState) else "HOME"
            st.caption(f"Current HomeMode: {current_mode}")
            selected = st.selectbox(
                "Scenario",
                list(SCENARIOS),
                key="smart_home_scenario",
                on_change=_scenario_changed,
            )
            scenario_detail = SCENARIO_DETAILS[selected]
            st.markdown(
                f'<div class="scenario-brief"><strong>{escape(scenario_detail["label"])}</strong>'
                f'<span>{escape(scenario_detail["description"])}</span></div>',
                unsafe_allow_html=True,
            )
            if "smart_home_text" not in st.session_state:
                st.session_state.smart_home_text = SCENARIOS[selected]
            text = st.text_area(
                "Resident request (editable)",
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
                        _run_request(text, use_ai, fault_name, selected)
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
                actual_intent = result.goal.intent if result.goal else None
                expected_intent = SCENARIO_INTENTS.get(saved["submitted_scenario"])
                intent_mismatch = expected_intent is not None and actual_intent != expected_intent
                css = "high" if intent_mismatch else "low" if outcome_name == "COMPLETE" else "medium" if outcome_name in ("PARTIAL", "CLARIFICATION_REQUIRED", "AWAITING_CONFIRMATION") else "high"
                title = "Scenario/result mismatch detected" if intent_mismatch else _result_title(outcome_name, actual_intent)
                summary = (
                    "The interpreted goal does not match the selected preset, so this result must not be presented as a successful preset demonstration."
                    if intent_mismatch else _result_summary(result)
                )
                st.markdown(
                    f'<div class="result-banner risk-{css}"><span class="risk-label">{escape(outcome_name)}</span>'
                    f'<h3>{escape(title)}</h3>'
                    f'<p>{escape(summary)}</p></div>',
                    unsafe_allow_html=True,
                )
                if intent_mismatch:
                    st.error(
                        f"Safety check: {saved['submitted_scenario']} should resolve to {expected_intent}, "
                        f"but the workflow returned {actual_intent}. Reset the demo before presenting this result."
                    )
                if result.goal:
                    verified = sum(action.success for action in result.action_results)
                    total = len(result.action_results)
                    mode_change = (
                        saved["mode_before"]
                        if saved["mode_before"] == saved["mode_after"]
                        else f'{saved["mode_before"]} -> {saved["mode_after"]}'
                    )
                    source = _decision_source(saved, result.goal.evidence)
                    st.markdown(
                        '<div class="execution-summary">'
                        f'<div><span>Scenario</span><strong>{escape(saved["submitted_scenario"])}</strong></div>'
                        f'<div><span>Interpreted goal</span><strong>{escape(INTENT_LABELS.get(result.goal.intent, result.goal.intent))}</strong></div>'
                        f'<div><span>HomeMode</span><strong>{escape(mode_change)}</strong></div>'
                        f'<div><span>Verified</span><strong>{verified}/{total if total else "-"}</strong></div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                    st.caption(f"Decision source: {source} | Workflow time: {saved['workflow_ms']:.1f} ms")
                    st.markdown(
                        f'<div class="decision-note"><strong>Why this result</strong><span>{escape(_plain_language_reason(result))}</span></div>',
                        unsafe_allow_html=True,
                    )
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
                if any(entry.outcome.startswith("audit_record_failed:") for entry in result.trace):
                    st.warning("The command result is shown, but its local audit record could not be saved.")

                if result.action_results:
                    st.markdown(_result_table_html(result), unsafe_allow_html=True)
                else:
                    st.caption("No device command was dispatched.")
                st.caption(f"Failure simulation used for this run: {saved['fault']}")
                with st.expander("Current simulated device states"):
                    st.dataframe(_state_rows(saved["states"]), hide_index=True, width="stretch")
                with st.expander("Agent trace and audit evidence"):
                    st.json(result.to_dict())

    device_tool = _device_tool()
    st.markdown('<div class="section-line"><h2>Demo device inventory</h2><span>State persists until Reset demo</span></div>', unsafe_allow_html=True)
    st.dataframe(_state_rows(device_tool.states), hide_index=True, width="stretch")
    st.caption("All actions on this page are simulated. Audit evidence is saved locally when storage is available.")
