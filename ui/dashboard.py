"""Operational views with real editable sample inputs and persisted outcomes."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from html import escape
import json
import os
from pathlib import Path

import streamlit as st

from domains.pet_care.records import monitor_pet_event
from simulation.events import make_sensor_event
from simulation.pet_demo import DEFAULT_RECORD_PATH


DOMAINS = {
    "Pet Care": ("paw", "peach", "Food levels and activity checks.", "Bowl levels & activity"),
    "Elderly Safety": ("heart", "lilac", "Daily wellbeing and safety monitoring.", "Wellbeing & safety"),
    "Smart Home Control": ("sliders", "blue", "Home device controls and returned state.", "Lights & home devices"),
    "Home Security": ("shield", "mint", "Door and motion monitoring.", "Doors & motion"),
    "Energy & Comfort": ("sun", "butter", "Temperature and energy monitoring.", "Temperature & energy"),
}
SCENARIOS = {
    "Food bowl": ("pet_bowl_level", "food_level_percent", 0.0, "%", "Food level"),
    "Activity check": ("pet_inactivity", "inactive_minutes", 150.0, "min", "Time without activity"),
    "Normal activity": ("pet_inactivity", "inactive_minutes", 5.0, "min", "Time without activity"),
}
RISK_LABELS = {"LOW": "Normal reading", "MEDIUM": "Needs attention", "HIGH": "Check on your pet"}


def icon(name: str) -> str:
    paths = {
        "home": '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z"/>',
        "paw": '<ellipse cx="12" cy="16" rx="5" ry="4"/><ellipse cx="5" cy="9" rx="2" ry="2.7"/><ellipse cx="10" cy="5" rx="2" ry="2.7"/><ellipse cx="16" cy="5.5" rx="2" ry="2.7"/><ellipse cx="20" cy="10" rx="2" ry="2.7"/>',
        "heart": '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0l-1 1-1-1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/>',
        "shield": '<path d="M12 3 3 7v5c0 5 9 9 9 9s9-4 9-9V7Z"/><path d="m8 12 3 3 5-6"/>',
        "sliders": '<path d="M4 4v5m0 5v6M12 4v10m0 5v1M20 4v1m0 5v10"/><circle cx="4" cy="11.5" r="2.5"/><circle cx="12" cy="16.5" r="2.5"/><circle cx="20" cy="7.5" r="2.5"/>',
        "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
        "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
        "check": '<path d="m5 12 4 4L19 6"/>',
    }
    return f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{paths[name]}</svg>'


def _navigate(page: str) -> None:
    st.session_state.page = page
    st.session_state.navigation = page


def _clear_result() -> None:
    st.session_state.pop("pet_result", None)


def _preset_changed() -> None:
    st.session_state.pet_value = SCENARIOS[st.session_state.pet_scenario][2]
    _clear_result()


def _reset_inputs() -> None:
    st.session_state.pet_scenario = "Food bowl"
    st.session_state.pet_value = 0.0
    st.session_state.pet_use_ai = False
    _clear_result()


def _records(path: Path | None = None, limit: int | None = None) -> list[dict]:
    """Read newest first; filtering happens before the UI truncates the list."""
    path = path or DEFAULT_RECORD_PATH
    if not path.exists():
        return []
    try:
        with path.open(encoding="utf-8") as stream:
            lines = deque(stream, maxlen=limit)
        records = []
        for line in reversed(lines):
            try:
                record = json.loads(line)
                if isinstance(record.get("event"), dict) and isinstance(record.get("assessment"), dict):
                    records.append(record)
            except (ValueError, AttributeError):
                continue
        return records
    except OSError:
        return []


def _local_time(value: str) -> str:
    try:
        from zoneinfo import ZoneInfo
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(ZoneInfo("Australia/Sydney")).strftime("%d %b · %H:%M")
    except (AttributeError, TypeError, ValueError):
        return "Time unavailable"


def _last_reading(records: list[dict], reading_type: str) -> tuple[str, str]:
    for record in records:
        readings = record["event"].get("readings", [])
        if not isinstance(readings, list):
            continue
        for reading in readings:
            if isinstance(reading, dict) and reading.get("reading_type") == reading_type:
                value = reading.get("value")
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    return f'{value:g} {reading.get("unit", "")}'.strip(), _local_time(record["event"].get("timestamp"))
    return "—", "No saved sample"


def _metrics(records: list[dict]) -> None:
    bowl, activity, latest = st.columns(3, gap="small")
    for column, title, reading_type in ((bowl, "FOOD BOWL · LAST SAMPLE", "food_level_percent"), (activity, "INACTIVITY · LAST SAMPLE", "inactive_minutes")):
        value, when = _last_reading(records, reading_type)
        with column:
            st.markdown(f'<div class="status-card"><span>{title}</span><strong>{escape(value)}</strong><small>{escape(when)}</small></div>', unsafe_allow_html=True)
    with latest:
        level = records[0]["assessment"].get("risk_level", "") if records else ""
        label = RISK_LABELS.get(level, "No checks yet")
        css = level.lower() if level in RISK_LABELS else "unknown"
        st.markdown(f'<div class="status-card"><span>LATEST RESULT</span><strong class="status-{css}">{escape(label)}</strong><small>{escape(_local_time(records[0]["event"].get("timestamp"))) if records else "Run a check to get started"}</small></div>', unsafe_allow_html=True)


def _recommendation(event, risk: str) -> str:
    if risk == "LOW":
        return "Keep your usual routine and check in again later."
    if event.event_type == "pet_bowl_level":
        return "Check the bowl and refill it as appropriate for your pet’s routine."
    return "Check on your pet in person and make sure they are comfortable."


def _check_workspace() -> None:
    controls, outcome = st.columns([1, 1.3], gap="medium")
    with controls:
        with st.container(border=True, key="pet-controls"):
            st.markdown('<div class="panel-heading"><h2>Run a pet check</h2><span class="small-badge">SIMULATED INPUT</span></div>', unsafe_allow_html=True)
            selected = st.selectbox("Scenario", list(SCENARIOS), key="pet_scenario", on_change=_preset_changed)
            event_type, reading_type, preset, unit, reading_label = SCENARIOS[selected]
            if "pet_value" not in st.session_state:
                st.session_state.pet_value = preset
            value = st.number_input(f"{reading_label} ({unit})", min_value=0.0, max_value=100.0 if event_type == "pet_bowl_level" else 1440.0, step=1.0, key="pet_value", on_change=_clear_result)
            st.caption("Edit the reading to test a different situation.")
            with st.expander("AI options"):
                use_ai = st.toggle("Include an AI explanation", value=False, key="pet_use_ai", on_change=_clear_result)
                if use_ai and not os.getenv("ELEC5620_API_KEY", "").strip():
                    st.caption("AI is not connected. Turn this option off to run a standard check.")
            disabled = use_ai and not os.getenv("ELEC5620_API_KEY", "").strip()
            run, reset = st.columns([1.6, 1], gap="small")
            with run:
                submitted = st.button("Run check →", key="run-pet-check", type="primary", disabled=disabled, use_container_width=True)
            with reset:
                st.button("Reset inputs", on_click=_reset_inputs, use_container_width=True)
            if submitted:
                event = make_sensor_event(event_type, reading_type, value, unit, sensor_id="simulated-pet-bowl" if event_type == "pet_bowl_level" else "simulated-pet-motion", context={"pet_id": "fictional-pet-1"})
                provider = None
                if use_ai:
                    from services.campus_proxy import CampusProxyConfig, propose_pet_risk
                    config = CampusProxyConfig.from_environment()
                    provider = lambda observation: propose_pet_risk(observation, config)
                try:
                    with st.spinner("Assessing and saving…"):
                        assessment = monitor_pet_event(event, record_path=DEFAULT_RECORD_PATH, proposal_provider=provider)
                    st.session_state.pet_result = {"event": event, "assessment": assessment, "requested_ai": use_ai, "observation": selected, "reading": f"{value:g} {unit}"}
                    st.rerun()
                except OSError:
                    _clear_result()
                    st.error("This check could not be saved. Please try again.")
    with outcome:
        with st.container(border=True, key="check-result"):
            result = st.session_state.get("pet_result")
            st.markdown('<div class="panel-heading"><h2>Check result</h2></div>', unsafe_allow_html=True)
            if not isinstance(result, dict):
                st.markdown('<div class="result-placeholder"><span class="waiting-dot"></span><h3>Ready for a reading</h3><p>Choose a scenario, adjust the value and run a check.</p></div>', unsafe_allow_html=True)
            else:
                event, assessment = result["event"], result["assessment"]
                risk = assessment.risk_level
                st.markdown(f'<div class="result-banner risk-{risk.lower()}"><span class="risk-label">{risk} RISK</span><h3>{escape(RISK_LABELS[risk])}</h3><p>{escape(assessment.rationale)}</p></div><div class="next-step"><span>NEXT STEP</span><p>{escape(_recommendation(event, risk))}</p></div>', unsafe_allow_html=True)
                if assessment.model_rationale:
                    st.info(f"AI explanation: {assessment.model_rationale}")
                elif result["requested_ai"] and assessment.fallback_used:
                    st.warning("AI was unavailable or its proposal did not match the rule. The rule-based result was kept.")
                else:
                    st.caption("Rule-based assessment · AI was not requested")
                st.markdown(f'<div class="completion-line">{icon("check")} Reading assessed <span>→</span> Record saved</div>', unsafe_allow_html=True)
                st.caption(f'{result["observation"]} · {result.get("reading", "Sample reading")} · {_local_time(event.timestamp)}')
                with st.expander("Event details"):
                    st.caption("No notification was sent. No feeder or other device was activated.")
                    st.json({"event": event.to_dict(), "assessment": assessment.to_dict()})


def _history(records: list[dict]) -> None:
    st.markdown('<div class="section-line"><h2>Check history</h2><span>Saved sample readings</span></div>', unsafe_allow_html=True)
    selected = st.radio("Filter history", ["All", "Needs attention", "Normal"], horizontal=True, label_visibility="collapsed", key="history_filter")
    matching = [record for record in records if selected == "All" or (selected == "Normal" and record["assessment"].get("risk_level") == "LOW") or (selected == "Needs attention" and record["assessment"].get("risk_level") in ("MEDIUM", "HIGH"))]
    if not matching:
        st.info("No checks match this filter." if records else "No saved checks yet. Run a check above to create the first record.")
        return
    rows = []
    for record in matching[:20]:
        event, assessment = record["event"], record["assessment"]
        readings = event.get("readings", [])
        reading = readings[0] if isinstance(readings, list) and readings and isinstance(readings[0], dict) else {}
        rows.append({"Time": _local_time(event.get("timestamp")), "Observation": "Food bowl" if event.get("event_type") == "pet_bowl_level" else "Activity", "Reading": f'{reading.get("value", "—")} {reading.get("unit", "")}'.strip(), "Risk": assessment.get("risk_level", "Unknown"), "Assessment": assessment.get("rationale", "Unavailable")})
    st.dataframe(rows, hide_index=True, use_container_width=True)
    if len(matching) > 20:
        st.caption(f"Showing the latest 20 of {len(matching)} matching checks.")


def _services(available: set[str]) -> None:
    with st.expander("Home services"):
        for name, (symbol, tint, _, subtitle) in DOMAINS.items():
            label, action = st.columns([3, 1], gap="small")
            with label:
                status = "View available" if name in available else "Not available in this version"
                st.markdown(f'<div class="service-row"><span class="icon-bubble {tint}">{icon(symbol)}</span><div><strong>{escape(name)}</strong><small>{escape(subtitle)} · {status}</small></div></div>', unsafe_allow_html=True)
            with action:
                st.button("Open →", key="open-" + name, on_click=_navigate, args=(name,), use_container_width=True)


def render_home(available: set[str] | None = None) -> None:
    st.markdown('<div class="page-heading"><h1>Home overview</h1><p>Review saved readings or run a new check.</p></div>', unsafe_allow_html=True)
    _metrics(_records())
    _check_workspace()
    _history(_records())
    _services(available if available is not None else {"Pet Care"})


def render_pet_care() -> None:
    st.markdown('<div class="page-heading"><h1>Pet Care</h1><p>Test food levels and inactivity, then review the recorded assessment.</p></div>', unsafe_allow_html=True)
    _metrics(_records())
    _check_workspace()
    _history(_records())


def render_pending(name: str) -> None:
    _, _, description, _ = DOMAINS[name]
    st.markdown(f'<div class="page-heading"><h1>{escape(name)}</h1><p>{escape(description)}</p></div>', unsafe_allow_html=True)
    st.info("This service is not available in this version. No devices or monitoring are connected here.")
    st.button("Open Pet Care →", type="primary", on_click=_navigate, args=("Pet Care",))
