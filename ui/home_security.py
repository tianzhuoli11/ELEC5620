"""Small SCRUM-15 Home Security page; monitoring uses the shared workflow."""

from __future__ import annotations

from collections import deque
import json
import os

import streamlit as st

from domains.home_security.integration import monitor_security_workflow
from domains.home_security.monitoring import READING_TYPES
from simulation.security_demo import DEFAULT_RECORD_PATH
from simulation.security_scenarios import SCENARIOS, make_security_observation


SENSOR_LABELS = {
    "smoke_alarm": "Smoke alarm",
    "gas_alarm": "Gas alarm",
    "water_leak": "Water leak",
    "door_open": "Door open",
    "motion_detected": "Motion detected",
}


def _load_preset() -> None:
    _, readings, mode, activity, authorised, lock, valve = SCENARIOS[st.session_state.security_scenario]
    for kind in READING_TYPES:
        st.session_state[f"security_{kind}"] = bool(readings.get(kind, 0))
    st.session_state.security_mode = mode
    st.session_state.security_activity = activity
    st.session_state.security_authorized = authorised
    st.session_state.security_lock = lock
    st.session_state.security_valve = valve
    st.session_state.pop("security_result", None)


def _clear_result() -> None:
    st.session_state.pop("security_result", None)


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
    st.caption("SCRUM-15 · Fictional sensor inputs and local assessment records")

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
            st.write(assessment.rationale)
            st.caption(f"Assessment time: {result.classification_ms:.1f} ms")
            st.caption(f"Campus LLM: {assessment.llm_status}")
            if assessment.model_rationale:
                st.write(f"LLM explanation: {assessment.model_rationale}")
            if assessment.fallback_used:
                st.warning("LLM advice was unavailable, invalid or conflicted with fixed rules; the rule result was kept.")
            if assessment.requires_human_review:
                st.warning("Input or event needs human review. No confirmation workflow runs in SCRUM-15.")
            st.caption("Assessment recorded locally. No owner notification or device action was requested.")
            with st.expander("Evidence and shared agent trace"):
                st.write(assessment.evidence)
                st.json(result.workflow.to_dict())

    records = _recent_records()
    if records:
        st.subheader("Recent local assessments")
        st.dataframe([
            {"Time (UTC)": item.get("received_at"),
             "Risk": item.get("assessment", {}).get("risk_level"),
             "Reason": item.get("assessment", {}).get("rationale")}
            for item in records
        ], hide_index=True, width="stretch")
