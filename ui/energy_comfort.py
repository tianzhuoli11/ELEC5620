"""UC-05 Energy & Comfort page: assessment, eligibility and explanation only."""

from __future__ import annotations

from collections import deque
from html import escape
import json
from pathlib import Path

import streamlit as st

from domains.energy_comfort.control_policy import (
    EXPLICIT_LIGHT_SHUTDOWN_BASIS,
    LightShutdownPolicyInput,
)
from domains.energy_comfort.explanations import explain_energy_comfort
from domains.energy_comfort.integration import evaluate_light_shutdown_candidate
from models import (
    DeviceObservation,
    EnergyProfile,
    HomeContext,
    HomeEnvironment,
    HomeMode,
    UserPreference,
)
from simulation.energy_comfort_demo import make_energy_comfort_event


DEFAULT_RECORD_PATH = Path("data/runtime/energy_comfort.jsonl")

SCENARIOS = {
    "Comfort OK (occupied)": {
        "occupancy": "Occupied",
        "temperature_c": 22.0,
        "pref_min": 20.0,
        "pref_max": 24.0,
        "include_energy": False,
        "current_power_w": 350.0,
        "power_limit_w": 400.0,
        "home_mode": "HOME",
        "include_device": False,
        "device_id": "observed-light",
        "device_available": True,
        "device_power": "on",
    },
    "Too warm (occupied)": {
        "occupancy": "Occupied",
        "temperature_c": 27.0,
        "pref_min": 20.0,
        "pref_max": 24.0,
        "include_energy": False,
        "current_power_w": 350.0,
        "power_limit_w": 400.0,
        "home_mode": "HOME",
        "include_device": False,
        "device_id": "observed-light",
        "device_available": True,
        "device_power": "on",
    },
    "Occupancy unknown": {
        "occupancy": "Unknown",
        "temperature_c": 27.0,
        "pref_min": 20.0,
        "pref_max": 24.0,
        "include_energy": True,
        "current_power_w": 900.0,
        "power_limit_w": 400.0,
        "home_mode": "HOME",
        "include_device": True,
        "device_id": "observed-light",
        "device_available": True,
        "device_power": "on",
    },
    "Unoccupied high power": {
        "occupancy": "Unoccupied",
        "temperature_c": 22.0,
        "pref_min": 20.0,
        "pref_max": 24.0,
        "include_energy": True,
        "current_power_w": 900.0,
        "power_limit_w": 400.0,
        "home_mode": "AWAY",
        "include_device": True,
        "device_id": "observed-light",
        "device_available": True,
        "device_power": "on",
    },
    "Unoccupied within limit": {
        "occupancy": "Unoccupied",
        "temperature_c": 22.0,
        "pref_min": 20.0,
        "pref_max": 24.0,
        "include_energy": True,
        "current_power_w": 350.0,
        "power_limit_w": 400.0,
        "home_mode": "AWAY",
        "include_device": True,
        "device_id": "observed-light",
        "device_available": True,
        "device_power": "off",
    },
}

OCCUPANCY_OPTIONS = ("Occupied", "Unoccupied", "Unknown")


def _clear_result() -> None:
    st.session_state.pop("energy_result", None)


def _load_preset() -> None:
    preset = SCENARIOS[st.session_state.energy_scenario]
    for key, value in preset.items():
        st.session_state[f"energy_{key}"] = value
    st.session_state.energy_unknown_temp = False
    st.session_state.energy_shutdown_basis = False
    st.session_state.energy_control_authorized = False
    st.session_state.energy_auth_source = ""
    st.session_state.energy_trust_source = False
    st.session_state.energy_safety_passed = "Unknown"
    st.session_state.energy_unknown_safety = False
    st.session_state.energy_conflict_safety = False
    _clear_result()


def _reset_demo() -> None:
    st.session_state.energy_scenario = "Comfort OK (occupied)"
    _load_preset()


def _occupancy_value(label: str) -> bool | None:
    if label == "Occupied":
        return True
    if label == "Unoccupied":
        return False
    return None


def _build_context() -> HomeContext:
    occupied = _occupancy_value(st.session_state.energy_occupancy)
    temperature = None if st.session_state.get("energy_unknown_temp") else float(st.session_state.energy_temperature_c)
    preference = UserPreference(
        float(st.session_state.energy_pref_min),
        float(st.session_state.energy_pref_max),
    )
    energy = None
    if st.session_state.energy_include_energy:
        energy = EnergyProfile(
            float(st.session_state.energy_current_power_w),
            float(st.session_state.energy_power_limit_w),
        )
    mode = HomeMode(st.session_state.energy_home_mode)
    devices: tuple[DeviceObservation, ...] = ()
    if st.session_state.energy_include_device:
        devices = (
            DeviceObservation(
                st.session_state.energy_device_id.strip() or "observed-light",
                bool(st.session_state.energy_device_available),
                {"power": st.session_state.energy_device_power},
            ),
        )
    return HomeContext(
        HomeEnvironment(temperature, occupied),
        preference,
        energy,
        mode,
        devices,
        simulated=True,
    )


def _policy_input() -> LightShutdownPolicyInput:
    safety_label = st.session_state.get("energy_safety_passed", "Unknown")
    safety_passed = {"Passed": True, "Rejected": False, "Unknown": None}[safety_label]
    unknown = ("unknown_hazard",) if st.session_state.get("energy_unknown_safety") else ()
    conflict = ("elderly_or_security_protection",) if st.session_state.get("energy_conflict_safety") else ()
    return LightShutdownPolicyInput(
        observed_device_id=(st.session_state.energy_device_id.strip() or None)
        if st.session_state.energy_include_device else None,
        shutdown_basis=EXPLICIT_LIGHT_SHUTDOWN_BASIS if st.session_state.get("energy_shutdown_basis") else None,
        control_authorized=True if st.session_state.get("energy_control_authorized") else None,
        authorization_source=(st.session_state.get("energy_auth_source") or "").strip() or None,
        safety_policy_passed=safety_passed,
        unknown_safety_conditions=unknown,
        conflicting_safety_conditions=conflict,
    )


def _append_record(payload: dict, record_path: Path) -> None:
    record_path.parent.mkdir(parents=True, exist_ok=True)
    with record_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _run_assessment(record_path: Path | None = None) -> None:
    path = record_path if record_path is not None else DEFAULT_RECORD_PATH
    context = _build_context()
    event = make_energy_comfort_event(context)
    trusted: frozenset[str] = frozenset()
    source = (st.session_state.get("energy_auth_source") or "").strip()
    if st.session_state.get("energy_trust_source") and source:
        trusted = frozenset({source})
    outcome = evaluate_light_shutdown_candidate(
        event,
        _policy_input(),
        trusted_authorization_sources=trusted,
    )
    explanation = explain_energy_comfort(
        outcome.assessment,
        workflow=outcome.workflow,
        eligibility=outcome.eligibility,
    )
    payload = {
        "record_type": "energy_comfort_assessment",
        "scope": {
            "assessment": "ASSESSMENT_ONLY",
            "execution_fixture": "TEST_ONLY_SIMULATION_NOT_RUN_HERE",
            "formal_energy_comfort_control": "PENDING",
        },
        "assessment": outcome.assessment.to_dict(),
        "eligibility": {
            "eligible": outcome.eligibility.eligible,
            "observed_device_id": outcome.eligibility.observed_device_id,
            "reasons": list(outcome.eligibility.reasons),
            "evidence": list(outcome.eligibility.evidence),
        },
        "explanation": explanation.to_dict(),
        "workflow": outcome.workflow.to_dict(),
    }
    _append_record(payload, path)
    st.session_state.energy_result = {
        "assessment": outcome.assessment,
        "eligibility": outcome.eligibility,
        "explanation": explanation,
        "workflow": outcome.workflow,
        "scope": payload["scope"],
    }


def _recent_records(limit: int = 8) -> list[dict]:
    if not DEFAULT_RECORD_PATH.exists():
        return []
    try:
        with DEFAULT_RECORD_PATH.open(encoding="utf-8") as stream:
            lines = deque(stream, maxlen=limit)
        return [json.loads(line) for line in reversed(lines)]
    except (OSError, ValueError):
        return []


def render_energy_comfort() -> None:
    st.markdown(
        '<div class="page-heading"><h1>Energy &amp; Comfort</h1>'
        "<p>Assess simulated temperature, occupancy, preference and energy context through the shared agents. "
        "No device command is authorized or dispatched from this page.</p></div>",
        unsafe_allow_html=True,
    )

    if "energy_scenario" not in st.session_state:
        st.session_state.energy_scenario = "Comfort OK (occupied)"
        _load_preset()

    controls, outcome = st.columns([1, 1.35], gap="medium")
    with controls:
        with st.container(border=True, key="energy-controls"):
            st.markdown(
                '<div class="panel-heading"><h2>Simulated context</h2>'
                '<span class="small-badge">ASSESSMENT ONLY</span></div>',
                unsafe_allow_html=True,
            )
            st.selectbox(
                "Scenario",
                list(SCENARIOS),
                key="energy_scenario",
                on_change=_load_preset,
            )
            st.selectbox(
                "Occupancy",
                OCCUPANCY_OPTIONS,
                key="energy_occupancy",
                on_change=_clear_result,
            )
            st.checkbox(
                "Temperature unknown",
                key="energy_unknown_temp",
                on_change=_clear_result,
            )
            st.number_input(
                "Indoor temperature (°C)",
                min_value=-20.0,
                max_value=50.0,
                step=0.5,
                key="energy_temperature_c",
                disabled=bool(st.session_state.get("energy_unknown_temp")),
                on_change=_clear_result,
            )
            pref_a, pref_b = st.columns(2)
            with pref_a:
                st.number_input(
                    "Comfort min (°C)",
                    min_value=-20.0,
                    max_value=50.0,
                    step=0.5,
                    key="energy_pref_min",
                    on_change=_clear_result,
                )
            with pref_b:
                st.number_input(
                    "Comfort max (°C)",
                    min_value=-20.0,
                    max_value=50.0,
                    step=0.5,
                    key="energy_pref_max",
                    on_change=_clear_result,
                )
            st.selectbox(
                "Home mode",
                ("HOME", "AWAY", "SLEEP"),
                key="energy_home_mode",
                on_change=_clear_result,
            )
            st.checkbox(
                "Include energy profile",
                key="energy_include_energy",
                on_change=_clear_result,
            )
            if st.session_state.energy_include_energy:
                power_a, power_b = st.columns(2)
                with power_a:
                    st.number_input(
                        "Current power (W)",
                        min_value=0.0,
                        max_value=20000.0,
                        step=50.0,
                        key="energy_current_power_w",
                        on_change=_clear_result,
                    )
                with power_b:
                    st.number_input(
                        "Unoccupied limit (W)",
                        min_value=0.0,
                        max_value=20000.0,
                        step=50.0,
                        key="energy_power_limit_w",
                        on_change=_clear_result,
                    )
            st.checkbox(
                "Include observed device",
                key="energy_include_device",
                on_change=_clear_result,
            )
            if st.session_state.energy_include_device:
                st.text_input(
                    "Observed device ID",
                    key="energy_device_id",
                    on_change=_clear_result,
                )
                st.checkbox(
                    "Device available",
                    key="energy_device_available",
                    on_change=_clear_result,
                )
                st.selectbox(
                    "Observed power",
                    ("on", "off"),
                    key="energy_device_power",
                    on_change=_clear_result,
                )

            with st.expander("Light-shutdown eligibility inputs (non-executable)"):
                st.caption(
                    "These fields only feed fail-closed eligibility. They never create an ActionRequest "
                    "and never dispatch a device."
                )
                st.checkbox(
                    "Explicit unoccupied light-shutdown basis",
                    key="energy_shutdown_basis",
                    on_change=_clear_result,
                )
                st.checkbox(
                    "Eligibility authorization metadata confirmed",
                    key="energy_control_authorized",
                    on_change=_clear_result,
                )
                st.text_input(
                    "Authorization source label",
                    key="energy_auth_source",
                    placeholder="fictional-team-source",
                    on_change=_clear_result,
                )
                st.checkbox(
                    "Treat source as trusted for eligibility demo only",
                    key="energy_trust_source",
                    on_change=_clear_result,
                )
                st.selectbox(
                    "Safety policy check",
                    ("Unknown", "Passed", "Rejected"),
                    key="energy_safety_passed",
                    on_change=_clear_result,
                )
                st.checkbox(
                    "Unknown safety conditions present",
                    key="energy_unknown_safety",
                    on_change=_clear_result,
                )
                st.checkbox(
                    "Conflicting elderly/security protection",
                    key="energy_conflict_safety",
                    on_change=_clear_result,
                )

            run, reset = st.columns([1.6, 1], gap="small")
            with run:
                submitted = st.button(
                    "Run assessment →",
                    key="run-energy-assessment",
                    type="primary",
                    width="stretch",
                )
            with reset:
                st.button("Reset demo", key="reset-energy", on_click=_reset_demo, width="stretch")
            if submitted:
                try:
                    with st.spinner("Assessing energy and comfort context…"):
                        _run_assessment()
                    st.rerun()
                except OSError:
                    _clear_result()
                    st.error("Assessment ran but the local audit record could not be saved.")
                except Exception as exc:
                    _clear_result()
                    st.error(f"Assessment failed safely before completion: {type(exc).__name__}.")

    with outcome:
        with st.container(border=True, key="energy-result"):
            st.markdown(
                '<div class="panel-heading"><h2>Assessment result</h2></div>',
                unsafe_allow_html=True,
            )
            saved = st.session_state.get("energy_result")
            if not isinstance(saved, dict):
                st.markdown(
                    '<div class="result-placeholder"><span class="waiting-dot"></span>'
                    "<h3>Ready for a scenario</h3>"
                    "<p>Choose simulated context, then run the assessment.</p></div>",
                    unsafe_allow_html=True,
                )
            else:
                assessment = saved["assessment"]
                eligibility = saved["eligibility"]
                explanation = saved["explanation"]
                workflow = saved["workflow"]
                scope = saved["scope"]

                st.info(
                    f"**Scope:** `{scope['assessment']}` · "
                    f"formal control `{scope['formal_energy_comfort_control']}` · "
                    "TEST_ONLY_SIMULATION is not run from this page."
                )
                st.metric("Decision", assessment.decision)
                st.write(f"Workflow outcome: **{workflow.outcome}**")
                st.write(assessment.rationale)
                st.caption(f"Policy: {assessment.policy}")

                if assessment.evidence:
                    st.write("Evidence: " + "; ".join(assessment.evidence))
                if assessment.missing_fields:
                    st.warning("Missing evidence: " + ", ".join(assessment.missing_fields))

                st.subheader("Control eligibility (not execution)")
                if eligibility.eligible:
                    st.warning(
                        "Eligible for later planning only. This is **not** device execution success "
                        "and no ActionRequest was created."
                    )
                else:
                    st.write("**Not eligible** for later planning under the supplied fail-closed inputs.")
                st.caption(
                    f"eligible={eligibility.eligible} · device={eligibility.observed_device_id or '—'}"
                )
                if eligibility.reasons:
                    st.write("Denial reasons: " + ", ".join(eligibility.reasons))
                if eligibility.evidence:
                    st.caption("Eligibility evidence: " + "; ".join(eligibility.evidence))

                st.subheader("Explanation")
                st.write(explanation.summary)
                st.caption(
                    f"Evidence status: {explanation.evidence_status} · "
                    f"Execution: {explanation.execution_status} · "
                    f"Safety: {explanation.safety_status}"
                )
                st.write(explanation.execution_detail)
                st.write(explanation.safety_detail)
                st.caption(explanation.environment_effect)
                for limit in explanation.limitations:
                    st.caption(f"Limitation: {limit}")

                if workflow.action_results:
                    st.error("Unexpected action results were returned; Energy & Comfort must not dispatch.")
                else:
                    st.caption("No device command was dispatched.")

                with st.expander("Agent trace and saved evidence"):
                    st.dataframe(
                        [{"Agent": item.agent, "Step": item.outcome, "Time": item.timestamp}
                         for item in workflow.trace],
                        hide_index=True,
                        width="stretch",
                    )
                    st.json({
                        "assessment": assessment.to_dict(),
                        "eligibility": {
                            "eligible": eligibility.eligible,
                            "reasons": list(eligibility.reasons),
                            "evidence": list(eligibility.evidence),
                        },
                        "explanation": explanation.to_dict(),
                        "workflow": workflow.to_dict(),
                        "scope": scope,
                    })

    records = _recent_records()
    if records:
        st.markdown(
            '<div class="section-line"><h2>Recent local assessments</h2>'
            "<span>Saved under data/runtime</span></div>",
            unsafe_allow_html=True,
        )
        st.dataframe(
            [
                {
                    "Decision": item.get("assessment", {}).get("decision", "—"),
                    "Workflow": item.get("workflow", {}).get("outcome", "—"),
                    "Eligible": item.get("eligibility", {}).get("eligible"),
                    "Execution": item.get("explanation", {}).get("execution_status", "—"),
                    "Formal control": item.get("scope", {}).get("formal_energy_comfort_control", "PENDING"),
                }
                for item in records
            ],
            hide_index=True,
            width="stretch",
        )

    st.markdown(
        '<div class="section-line"><h2>How this page decides</h2>'
        "<span>Prototype rules, not tariff or medical advice</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "- **NO_ADJUSTMENT**: occupied temperature inside the inclusive preference range, "
        "or unoccupied power at/below the configured limit.\n"
        "- **ADJUSTMENT_NEEDED**: occupied temperature outside preference, or unoccupied power "
        "above the limit with an available device observed `power=on`.\n"
        "- **INSUFFICIENT_DATA**: occupancy unknown, or required temperature/preference/energy facts missing.\n"
        "- Eligibility is fail-closed preparation only. Formal Energy & Comfort device control remains **PENDING**."
    )
    st.caption(
        "All readings and devices on this page are simulated. "
        f"Each run appends local evidence to {escape(str(DEFAULT_RECORD_PATH))}."
    )
