"""Share safety evidence across pages in this browser session only."""
import streamlit as st
from services.safety_state import SafetyState


def current_safety():
    if "home_safety_state" not in st.session_state:
        st.session_state.home_safety_state = SafetyState()
    return st.session_state.home_safety_state
