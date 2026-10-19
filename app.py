"""Launch the ELEC5620 Streamlit smart-home dashboard."""

from __future__ import annotations

import streamlit as st

from ui.dashboard import DOMAINS, _rail, render_home, render_pending, render_pet_care
from ui.styles import apply_styles


st.set_page_config(page_title="Haven | Smart Home", page_icon="⌂", layout="wide", initial_sidebar_state="expanded")
apply_styles()

with st.sidebar:
    st.markdown('<div class="brand"><span class="brand-icon">⌂</span> Haven</div><div class="brand-sub">SMART HOME HUB</div>', unsafe_allow_html=True)
    st.write("")
    pages = ["Overview", *[item[0] for item in DOMAINS]]
    if "page" not in st.session_state:
        st.session_state.page = "Overview"
    if "navigation" not in st.session_state:
        st.session_state.navigation = st.session_state.page
    selected = st.radio("EXPLORE", pages, key="navigation", label_visibility="visible")
    if selected != st.session_state.page:
        st.session_state.page = selected
        st.rerun()
    st.divider()
    st.caption("ELEC5620 · Group 11")
    st.caption("Local demo · simulated inputs")

main, rail = st.columns([3.2, 1.05], gap="large")
with main:
    st.markdown('<div class="topline"><div><div class="eyebrow">ELEC5620 · GROUP 11</div><span class="muted">Your smart home, at a glance.</span></div><span class="pill">●  Local demo</span></div>', unsafe_allow_html=True)
    if st.session_state.page == "Overview":
        render_home()
    elif st.session_state.page == "Pet Care":
        render_pet_care()
    else:
        render_pending(st.session_state.page)
with rail:
    _rail()
