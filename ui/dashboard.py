"""Dashboard views; pet decisions stay in the domain layer."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from html import escape
import json
import os
from pathlib import Path

import streamlit as st

from domains.pet_care.records import monitor_pet_event
from simulation.pet_demo import DEFAULT_RECORD_PATH, make_pet_scenario


DOMAINS = (
    ("Pet Care", "🐾", "#fff0e9", "Ready to try"),
    ("Elderly Safety", "♡", "#f2edff", "Awaiting integration"),
    ("Smart Home Control", "⌂", "#eaf4ff", "Awaiting integration"),
    ("Home Security", "◇", "#e9f7ef", "Awaiting integration"),
    ("Energy & Comfort", "ϟ", "#fff3df", "Awaiting integration"),
)
SCENARIOS = {
    "Empty food bowl": ("empty_bowl", "Food level: 0%"),
    "Unusual inactivity": ("unusual_inactivity", "No activity: 150 minutes"),
    "Normal activity": ("normal_activity", "No activity: 5 minutes"),
}


def _open_pet_care() -> None:
    st.session_state.page = "Pet Care"
    st.session_state.navigation = "Pet Care"


def _records(path: Path = DEFAULT_RECORD_PATH, limit: int = 5) -> list[dict]:
    if not path.exists():
        return []
    try:
        with path.open(encoding="utf-8") as stream:
            lines = deque(stream, maxlen=limit)
        return [json.loads(line) for line in reversed(lines) if line.strip()]
    except (OSError, ValueError):
        return []


def _local_time(value: str) -> str:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone().strftime("%d %b, %H:%M")
    except (TypeError, ValueError):
        return "Time unavailable"


def _domain_card(name: str, icon: str, tint: str, status: str) -> None:
    status_class = "chip-ready" if status == "Ready to try" else "chip-soon"
    st.markdown(
        f'<div class="domain-card"><div class="icon" style="background:{tint}">{escape(icon)}</div>'
        f'<h3>{escape(name)}</h3><p>Smart home domain</p>'
        f'<span class="chip {status_class}">{escape(status)}</span></div>',
        unsafe_allow_html=True,
    )


def _rail() -> None:
    records = _records()
    key_ready = bool(os.getenv("ELEC5620_API_KEY", "").strip())
    st.markdown('<div class="rail-heading">PROJECT STATUS</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="rail-card"><h3>Domain integration</h3><div class="rail-number">01 / 05</div>'
        '<p>Pet Care demo is available. The other domains will appear here as their modules are integrated.</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="rail-card"><h3>Campus AI</h3>'
        f'<p>{"API key configured for this process. Choose the AI option in Pet Care to make a live request." if key_ready else "API key not configured in this process. Rule-based Pet Care still works."}</p>'
        '<p style="margin-top:10px">A configured key does not confirm VPN or proxy connectivity.</p></div>',
        unsafe_allow_html=True,
    )
    activity = '<div class="rail-card"><h3>Recent activity</h3>'
    if records:
        for record in records:
            event = record.get("event", {})
            assessment = record.get("assessment", {})
            risk = escape(str(assessment.get("risk_level", "Unknown")))
            event_type = escape(str(event.get("event_type", "Pet event")).replace("_", " ").title())
            when = escape(_local_time(event.get("timestamp", "")))
            activity += f'<div class="activity"><strong>{event_type} · {risk}</strong><small>{when} · simulated</small></div>'
    else:
        activity += '<p>No assessments yet. Run a Pet Care scenario to create the first record.</p>'
    st.markdown(activity + '</div>', unsafe_allow_html=True)


def render_home() -> None:
    st.markdown(
        '<div class="hero"><div class="hero-content"><div class="eyebrow">GOOD TO SEE YOU</div>'
        '<h1>A calmer way to care for home.</h1>'
        '<p>Explore the five smart home domains in one place. Start with the working Pet Care simulation and follow each result from sensor reading to recorded assessment.</p>'
        '<div class="hero-tags"><span>◌  Simulated sensor input</span><span>✧  Explainable assessment</span><span>▤  Local event history</span></div>'
        '</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="section-line"><h2>Your home</h2><span>5 domains · 1 interactive demo</span></div>', unsafe_allow_html=True)
    first = st.columns(3, gap="medium")
    second = st.columns(2, gap="medium")
    for col, domain in zip((*first, *second), DOMAINS):
        with col:
            _domain_card(*domain)
    st.write("")
    st.button("Open Pet Care demo →", type="primary", on_click=_open_pet_care)


def render_pet_care() -> None:
    st.markdown('<div class="eyebrow">PET CARE · INTERACTIVE DEMO</div>', unsafe_allow_html=True)
    st.title("Look after the little things.")
    st.markdown('<p class="muted">Choose a fictional sensor scenario, run the real monitoring logic, and inspect its recorded decision.</p>', unsafe_allow_html=True)
    with st.container(border=True):
        st.subheader("01  Choose an observation")
        selected = st.selectbox("Scenario", list(SCENARIOS), help="Every scenario uses simulated data; no physical devices are controlled.")
        scenario, reading = SCENARIOS[selected]
        st.caption(f"Simulated input · {reading}")
        use_ai = st.toggle("Ask campus AI for an additional explanation", value=False)
        if use_ai and not os.getenv("ELEC5620_API_KEY", "").strip():
            st.warning("Set ELEC5620_API_KEY in your local environment, then restart the app to use campus AI.")
        if st.button("Run assessment →", type="primary", disabled=use_ai and not os.getenv("ELEC5620_API_KEY", "").strip()):
            event = make_pet_scenario(scenario)
            provider = None
            if use_ai:
                from services.campus_proxy import CampusProxyConfig, propose_pet_risk

                config = CampusProxyConfig.from_environment()
                provider = lambda observation: propose_pet_risk(observation, config)
            try:
                with st.spinner("Assessing and recording the event..."):
                    assessment = monitor_pet_event(event, record_path=DEFAULT_RECORD_PATH, proposal_provider=provider)
                st.session_state.pet_result = (event, assessment, use_ai)
            except OSError as exc:
                st.error(f"The assessment could not be recorded: {exc}")
    result = st.session_state.get("pet_result")
    if result is None:
        st.info("Select a scenario and run an assessment to see a result.")
        return
    event, assessment, requested_ai = result
    st.markdown('<div class="section-line"><h2>Assessment result</h2><span>Recorded simulated event</span></div>', unsafe_allow_html=True)
    risk = assessment.risk_level
    st.markdown(
        f'<div class="risk-card risk-{risk.lower()}"><div class="eyebrow">{escape(risk)} RISK</div>'
        f'<h2>{escape(risk.title())} attention level</h2><p>{escape(assessment.rationale)}</p></div>',
        unsafe_allow_html=True,
    )
    if assessment.model_rationale:
        st.success(f"Campus AI explanation: {assessment.model_rationale}")
    elif requested_ai and assessment.policy_override:
        st.warning("The AI proposal disagreed with the safety rule. The rule-based risk was retained.")
    elif requested_ai and assessment.fallback_used:
        st.warning("The campus AI response was unavailable or invalid. The rule-based result was retained.")
    else:
        st.caption("Rule-based assessment. Campus AI was not requested.")
    st.caption(f"Event ID: {event.event_id}  ·  {_local_time(event.timestamp)}  ·  Simulated input")
    st.markdown('<p class="tiny-note">No owner notification was sent. No feeder or other physical device was activated.</p>', unsafe_allow_html=True)
    with st.expander("View event and assessment data"):
        st.json({"event": event.to_dict(), "assessment": assessment.to_dict()})


def render_pending(name: str) -> None:
    st.markdown('<div class="eyebrow">SMART HOME DOMAIN</div>', unsafe_allow_html=True)
    st.title(name)
    st.markdown(
        '<div class="rail-card" style="padding:32px; margin-top:22px">'
        '<h3>Integration in progress</h3><p>This domain does not have a runnable module on this branch yet. '
        'Its controls and status will appear when the owner’s implementation is integrated.</p></div>',
        unsafe_allow_html=True,
    )
