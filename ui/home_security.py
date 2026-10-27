"""UC-04 Home Security page using the shared workflow and simulated devices."""

from __future__ import annotations

from collections import deque
import json
import os

import streamlit as st

from domains.home_security.integration import monitor_security_workflow, resume_security_workflow
from domains.home_security.monitoring import READING_TYPES
from domains.home_security.external_warnings import HOUSEHOLD_AREA, WARNING_EVENT_TYPE
from simulation.external_warning_scenarios import WARNING_SCENARIOS, make_warning_scenario
from simulation.security_demo import DEFAULT_RECORD_PATH
from simulation.security_scenarios import SCENARIOS, make_security_observation


SENSOR_LABELS = {
    "smoke_alarm": "Smoke alarm",
    "gas_alarm": "Gas alarm",
    "water_leak": "Water leak",
    "door_open": "Door open",
    "motion_detected": "Motion detected",
    "appliance_overheat_alarm": "Appliance overheat alarm",
    "appliance_unexpected_run": "Appliance running unexpectedly",
    "window_open": "Window open",
    "smart_lock_access_anomaly": "Smart-lock access anomaly",
}

CONFIRMATION_LABELS = {"help": "approved", "safe": "rejected", "timeout": "timeout", "unclear": "unclear"}


def _warning_text(value: str) -> str:
    """Shorten warning prose only for display; keep the audit unchanged."""
    shortened = value.replace("SIMULATED ", "")
    return shortened[0].upper() + shortened[1:] if value.startswith("SIMULATED ") and shortened else shortened


def _display_workflow(workflow) -> dict:
    """Translate confirmation terms for this page without changing audit data."""
    displayed = workflow.to_dict()
    for reply in displayed["confirmation_replies"]:
        reply["verdict"] = CONFIRMATION_LABELS.get(reply["verdict"], reply["verdict"])
    assessment = displayed["assessment"]
    for internal, label in CONFIRMATION_LABELS.items():
        assessment["rationale"] = assessment["rationale"].replace(
            f"Homeowner confirmation: {internal}.", f"Homeowner confirmation: {label}.",
        )
        assessment["evidence"] = assessment["evidence"].replace(
            f"confirmation_verdict={internal}", f"confirmation_verdict={label}",
        )
        for entry in displayed["trace"]:
            if entry["outcome"] in (f"resident_reply:{internal}", f"escalated:{internal}"):
                entry["outcome"] = entry["outcome"].replace(f":{internal}", f":{label}")
    if workflow.event.event_type == WARNING_EVENT_TYPE:
        assessment["rationale"] = _warning_text(assessment["rationale"])
    return displayed


def _load_preset() -> None:
    _, readings, mode, activity, authorised, lock, valve = SCENARIOS[st.session_state.security_scenario]
    for kind in READING_TYPES:
        st.session_state[f"security_{kind}"] = bool(readings.get(kind, 0))
    st.session_state.security_mode = mode
    st.session_state.security_activity = activity
    st.session_state.security_authorized = authorised
    st.session_state.security_lock = lock
    st.session_state.security_valve = valve
    st.session_state.security_failure = st.session_state.security_scenario == "device_failure"
    st.session_state.pop("security_result", None)


def _clear_result() -> None:
    st.session_state.pop("security_result", None)


def _clear_warning_result() -> None:
    st.session_state.pop("security_warning_result", None)


def _recent_records(limit: int = 10) -> list[dict]:
    if not DEFAULT_RECORD_PATH.exists():
        return []
    try:
        with DEFAULT_RECORD_PATH.open(encoding="utf-8") as stream:
            lines = deque(stream, maxlen=limit)
        return [json.loads(line) for line in reversed(lines)]
    except (OSError, ValueError):
        return []


def render_home_security() -> None:
    st.title("Home Security")
    st.caption("UC-04 · Fictional sensors, simulated notifications and devices, local audit")

    if "security_scenario" not in st.session_state:
        st.session_state.security_scenario = "normal"
        _load_preset()

    controls, outcome = st.columns([1, 1.2], gap="medium")
    with controls:
        st.subheader("Simulated observation")
        st.selectbox(
            "Scenario", tuple(SCENARIOS), format_func=lambda name: SCENARIOS[name][0],
            key="security_scenario", on_change=_load_preset,
        )
        st.caption("Change any input to test the risk rules.")
        readings = {
            kind: int(st.checkbox(SENSOR_LABELS[kind], key=f"security_{kind}", on_change=_clear_result))
            for kind in READING_TYPES
        }
        mode = st.selectbox("Home Mode", ("HOME", "AWAY"), key="security_mode", on_change=_clear_result)
        activity = st.selectbox("Recent activity", ("EXPECTED", "NONE"), key="security_activity", on_change=_clear_result)
        authorised = st.checkbox("Authorized entry", key="security_authorized", on_change=_clear_result)
        lock = st.selectbox("Front door lock", ("locked", "unlocked"), key="security_lock", on_change=_clear_result)
        valve = st.selectbox("Water valve", ("closed", "open"), key="security_valve", on_change=_clear_result)
        failure = st.checkbox("Simulate response devices offline", key="security_failure", on_change=_clear_result)
        with st.expander("AI option"):
            use_ai = st.toggle("Request campus LLM advice", key="security_use_ai", on_change=_clear_result)
            configured = bool(os.getenv("ELEC5620_API_KEY", "").strip())
            if use_ai and not configured:
                st.info("Set ELEC5620_API_KEY locally to enable the campus LLM.")

        if st.button("Assess observation", key="security_run", type="primary", disabled=use_ai and not configured):
            event = make_security_observation(
                readings, home_mode=mode, recent_activity=activity,
                authorized_entry=authorised, front_door_lock=lock, water_valve=valve,
            )
            provider = None
            if use_ai:
                from domains.home_security.llm import propose_security_risk
                from services.campus_proxy import CampusProxyConfig

                config = CampusProxyConfig.from_environment()
                provider = lambda observation: propose_security_risk(observation, config)
            try:
                result = monitor_security_workflow(
                    event, record_path=DEFAULT_RECORD_PATH, proposal_provider=provider,
                    offline_devices=("appliance", "gas_valve", "water_valve", "security_lights", "siren") if failure else (),
                )
                st.session_state.security_result = result
            except OSError:
                st.error("Assessment could not be saved locally. Check the record path.")

    with outcome:
        st.subheader("Assessment")
        result = st.session_state.get("security_result")
        if result is None:
            st.info("Choose a scenario and assess it to see the actual workflow result.")
        else:
            assessment = result.assessment
            st.metric("Risk level", assessment.risk_level)
            st.write(f"Workflow outcome: **{result.workflow.outcome}**")
            st.write(assessment.rationale)
            st.caption(f"Workflow time: {result.classification_ms:.1f} ms")
            st.caption(f"Campus LLM: {assessment.llm_status}")
            if assessment.model_rationale:
                st.write(f"LLM explanation: {assessment.model_rationale}")
            if assessment.fallback_used:
                st.warning("LLM advice was unavailable, invalid or conflicted with fixed rules; the rule result was kept.")
            pending = result.workflow.pending_confirmation
            if pending:
                st.warning(pending.question)
                st.caption(f"Attempt {pending.attempt}/{pending.max_attempts}; timeout {pending.timeout_seconds} s. The timeout button simulates expiry.")
                approve, reject, timeout = st.columns(3)
                selected = None
                if approve.button("Approve", key="security_approve"):
                    selected = "APPROVE"
                if reject.button("Reject", key="security_reject"):
                    selected = "REJECT"
                if timeout.button("No reply / timeout", key="security_timeout"):
                    selected = "TIMEOUT"
                if selected is not None:
                    try:
                        result = resume_security_workflow(
                            result, None if selected == "TIMEOUT" else selected,
                            record_path=DEFAULT_RECORD_PATH,
                        )
                        st.session_state.security_result = result
                        st.rerun()
                    except OSError:
                        st.error("Confirmation result could not be saved locally.")
            if result.workflow.confirmation_replies:
                st.write("Confirmation:", ", ".join(
                    CONFIRMATION_LABELS.get(item.verdict, item.verdict)
                    for item in result.workflow.confirmation_replies
                ))
            if result.notification_history:
                st.write("Simulated owner notifications:")
                st.dataframe(result.notification_history, hide_index=True, width="stretch")
            if result.workflow.action_results:
                st.write("Simulated device actions:")
                st.dataframe([
                    {"Device": action.device_id, "Accepted": action.accepted,
                     "State verified": action.verified, "Attempts": action.attempts,
                     "Observed state": str(action.returned_state),
                     "Result": "SUCCESS" if action.success else "FAILURE",
                     "Error": action.error or ""}
                    for action in result.workflow.action_results
                ], hide_index=True, width="stretch")
            if result.workflow.outcome in ("FAILED", "PARTIAL"):
                st.error("One or more responses failed or could not be verified. See action results and audit trace.")
            st.caption("Each workflow stage is recorded in the local audit log. All device and notification results are simulated.")
            with st.expander("Evidence and shared agent trace"):
                st.write(assessment.evidence)
                st.json(_display_workflow(result.workflow))

    st.divider()
    st.subheader("External Warning · SIMULATED")
    st.caption(
        f"Fictional warning feed and household area {HOUSEHOLD_AREA}. "
        "No government API or real device is connected."
    )
    warning_controls, warning_outcome = st.columns([1, 1.2], gap="medium")
    with warning_controls:
        st.selectbox(
            "Warning scenario", tuple(WARNING_SCENARIOS),
            format_func=lambda name: WARNING_SCENARIOS[name][0].removesuffix(" · SIMULATED"),
            key="security_warning_scenario", on_change=_clear_warning_result,
        )
        warning_use_ai = st.toggle(
            "Request campus LLM advice for warning", key="security_warning_use_ai",
            on_change=_clear_warning_result,
        )
        if warning_use_ai and not configured:
            st.info("Set ELEC5620_API_KEY locally to enable optional campus advice.")
        if st.button(
            "Assess external warning", key="security_warning_run",
            disabled=warning_use_ai and not configured,
        ):
            warning_event = make_warning_scenario(st.session_state.security_warning_scenario)
            warning_provider = None
            if warning_use_ai:
                from domains.home_security.llm import propose_external_warning_risk
                from services.campus_proxy import CampusProxyConfig

                config = CampusProxyConfig.from_environment()
                warning_provider = lambda observation: propose_external_warning_risk(observation, config)
            try:
                st.session_state.security_warning_result = monitor_security_workflow(
                    warning_event, record_path=DEFAULT_RECORD_PATH,
                    proposal_provider=warning_provider,
                )
            except OSError:
                st.error("External warning result could not be saved locally.")
    with warning_outcome:
        warning_result = st.session_state.get("security_warning_result")
        if warning_result is None:
            st.info("Choose a warning and assess it to see source validation and response.")
        else:
            warning = warning_result.assessment
            st.metric("Warning risk", warning.risk_level)
            st.write(f"Validity: **{'VALID' if warning.valid else 'INVALID'}** · "
                     f"Household relevance: **{'YES' if warning.relevant else 'NO'}**")
            st.write(f"Workflow outcome: **{warning_result.workflow.outcome}**")
            st.write(_warning_text(warning.rationale))
            st.caption(f"Campus LLM: {warning.llm_status}")
            if warning.model_rationale:
                st.write(f"LLM explanation: {_warning_text(warning.model_rationale)}")
            if warning.fallback_used:
                st.warning("LLM advice was unavailable or conflicted with the fixed warning rules.")
            if warning_result.notification_history:
                st.write("Owner notifications:")
                st.dataframe([
                    {**item, "message": _warning_text(item["message"]),
                     "status": "Recorded locally" if item["status"] == "SIMULATED" else item["status"]}
                    for item in warning_result.notification_history
                ], hide_index=True, width="stretch")
            else:
                st.caption("No owner notification was sent for this warning.")
            if warning_result.workflow.action_results:
                st.write("Emergency mode action:")
                st.dataframe([
                    {"Device": item.device_id, "Accepted": item.accepted,
                     "Verified": item.verified, "Observed state": str(item.returned_state),
                     "Result": "SUCCESS" if item.success else "FAILURE"}
                    for item in warning_result.workflow.action_results
                ], hide_index=True, width="stretch")
            with st.expander("Warning details and audit trace"):
                st.json(warning_result.workflow.event.context.get("warning"))
                st.json(_display_workflow(warning_result.workflow))

    records = _recent_records()
    if records:
        st.subheader("Recent local workflow records")
        st.dataframe([
            {"Time (UTC)": item.get("received_at"),
             "Risk": item.get("assessment", {}).get("risk_level"),
             "Outcome": item.get("workflow", {}).get("outcome"),
             "Reason": _warning_text(item.get("assessment", {}).get("rationale", ""))
             if item.get("record_type") == "external_warning_workflow"
             else item.get("assessment", {}).get("rationale")}
            for item in records
        ], hide_index=True, width="stretch")
