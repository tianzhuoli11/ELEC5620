"""Haven: the resident-facing smart-home application."""

from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from ui.dashboard import DOMAINS, icon, render_home
from ui.domain_views import DOMAIN_VIEWS, render_domain
from ui.styles import apply_styles


st.set_page_config(page_title="Haven | Home console", page_icon="⌂", layout="wide", initial_sidebar_state="expanded")
apply_styles()

with st.sidebar:
    st.markdown(f'<div class="brand"><span class="brand-icon">{icon("home")}</span>haven<span class="brand-dot">.</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="home-picker"><span class="home-avatar">H</span><div><strong>My home</strong><small>Home controls</small></div></div>', unsafe_allow_html=True)
    pages = ["Overview", *DOMAINS, "Decision explanations"]
    if "page" not in st.session_state:
        st.session_state.page = "Overview"
    if "navigation" not in st.session_state:
        st.session_state.navigation = st.session_state.page
    selected = st.radio("YOUR HOME", pages, key="navigation", width="stretch")
    if selected != st.session_state.page:
        st.session_state.page = selected
        st.rerun()
    st.markdown('<div class="sidebar-footer"><span class="status-dot"></span> Demo home<small>Sample sensor readings<br>Check history saved locally</small></div>', unsafe_allow_html=True)

date_label = datetime.now(ZoneInfo("Australia/Sydney")).strftime("%A, %d %B")
st.markdown(f'<div class="topbar"><div><span class="breadcrumb">MY HOME /</span><strong>{st.session_state.page}</strong></div><div class="topbar-right"><span>{date_label}</span><span class="demo-badge">Demo home</span></div></div>', unsafe_allow_html=True)

if st.session_state.page == "Overview":
    render_home(set(DOMAIN_VIEWS))
elif st.session_state.page == "Decision explanations":
    from ui.explanations import render_explanations
    render_explanations()
else:
    render_domain(st.session_state.page)
