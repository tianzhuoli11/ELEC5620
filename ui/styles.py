"""Presentation styles for the Streamlit smart-home dashboard."""

from base64 import b64encode
from pathlib import Path

import streamlit as st


def apply_styles() -> None:
    hero_bytes = (Path(__file__).parent / "assets" / "living_room.png").read_bytes()
    hero_url = "data:image/png;base64," + b64encode(hero_bytes).decode("ascii")
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root { --ink:#20212b; --muted:#7c7d89; --line:#e8e7eb; --orange:#e86a45; --blue:#4e86b7; }
html, body, [class*="css"], [data-testid="stApp"] { font-family:'DM Sans',sans-serif; color:var(--ink); }
[data-testid="stAppViewContainer"] { background:radial-gradient(circle at 9% 6%, #fff9d9 0, transparent 31%), radial-gradient(circle at 50% 0%, #d8f4e9 0, transparent 36%), radial-gradient(circle at 96% 18%, #f6d9f4 0, transparent 37%), #f8f8f7; }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stSidebar"] { background:rgba(255,255,255,.79); border-right:1px solid rgba(255,255,255,.85); }
[data-testid="stSidebar"] > div:first-child { padding-top:2.1rem; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span { color:#343541; }
.block-container { max-width:1500px; padding-top:2.1rem; padding-bottom:3rem; }
h1,h2,h3,h4 { font-family:'Manrope',sans-serif; letter-spacing:-.04em; }
h1 { font-size:2.2rem !important; font-weight:800 !important; }
h2 { font-size:1.3rem !important; font-weight:800 !important; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius:22px !important; border-color:rgba(255,255,255,.9) !important; background:rgba(255,255,255,.75); box-shadow:0 12px 40px rgba(58,55,80,.045); }
[data-testid="stButton"] button { border-radius:13px; min-height:2.8rem; font-weight:700; border-color:#dedde1; }
[data-testid="stButton"] button[kind="primary"] { background:#e86a45; border-color:#e86a45; color:#fff; }
[data-testid="stButton"] button[kind="primary"]:hover { background:#d95a37; border-color:#d95a37; }
[data-testid="stRadio"] label { border-radius:12px; }
[data-testid="stMetric"] { background:#fff; border:1px solid #eeeef1; border-radius:16px; padding:14px 18px; }
.brand { display:flex; align-items:center; gap:11px; font:800 1.15rem Manrope,sans-serif; letter-spacing:-.04em; margin-bottom:7px; }
.brand-icon { display:grid; place-items:center; width:38px; height:38px; border-radius:13px; background:#ffe9de; color:#dc6748; font-size:1.3rem; }
.brand-sub { margin-left:49px; color:#93949d; font-size:.72rem; letter-spacing:.04em; text-transform:uppercase; }
.eyebrow { font-size:.72rem; text-transform:uppercase; letter-spacing:.14em; font-weight:800; color:#c16b51; margin-bottom:7px; }
.muted { color:var(--muted); font-size:.91rem; line-height:1.55; }
.topline { display:flex; justify-content:space-between; align-items:center; gap:1rem; margin-bottom:1.3rem; }
.topline .pill { background:#fff; border:1px solid #e8e7eb; border-radius:999px; padding:8px 13px; color:#666a72; font-size:.76rem; font-weight:700; white-space:nowrap; }
.hero { min-height:290px; border-radius:24px; padding:30px 34px; background:linear-gradient(90deg,rgba(253,251,246,.98) 0%,rgba(253,251,246,.93) 42%,rgba(253,251,246,.08) 87%), url('__HERO_IMAGE__') center/cover; border:1px solid #fff; box-shadow:0 16px 36px rgba(54,64,60,.08); position:relative; overflow:hidden; }
.hero-content { position:relative; z-index:1; max-width:66%; }
.hero h1 { margin:0 0 8px; line-height:1.2; }
.hero p { color:#65717a; max-width:530px; font-size:.96rem; }
.hero-tags { display:flex; flex-wrap:wrap; gap:8px; margin-top:30px; }
.hero-tags span { background:rgba(255,255,255,.78); padding:8px 11px; border-radius:10px; font-size:.75rem; font-weight:700; color:#515b66; }
.section-line { display:flex; justify-content:space-between; align-items:baseline; margin:26px 0 10px; }
.section-line h2 { margin:0; }
.section-line span { color:#92949b; font-size:.78rem; }
.domain-card { background:rgba(255,255,255,.83); border:1px solid #fff; border-radius:19px; padding:19px; min-height:164px; box-shadow:0 8px 30px rgba(48,45,64,.035); }
.domain-card .icon { display:grid; place-items:center; width:38px; height:38px; border-radius:12px; font-size:1.2rem; margin-bottom:19px; }
.domain-card h3 { font-size:.96rem; margin:0 0 3px; letter-spacing:-.02em; }
.domain-card p { color:#92949d; font-size:.75rem; margin:0; }
.chip { display:inline-block; border-radius:999px; padding:4px 8px; font-size:.66rem; font-weight:800; margin-top:11px; }
.chip-ready { background:#e6f5eb; color:#3d8862; }
.chip-soon { background:#f1f1f4; color:#888a95; }
.rail-heading { color:#898b93; text-transform:uppercase; letter-spacing:.12em; font-size:.68rem; font-weight:800; margin-bottom:13px; }
.rail-card { background:rgba(255,255,255,.85); border:1px solid #fff; border-radius:20px; padding:20px; margin-bottom:15px; box-shadow:0 8px 24px rgba(50,47,65,.035); }
.rail-card h3 { margin:0 0 8px; font-size:.96rem; }
.rail-card p { color:#8a8c95; font-size:.77rem; line-height:1.5; margin:0; }
.rail-number { font:800 2rem Manrope,sans-serif; letter-spacing:-.06em; margin:7px 0; }
.activity { border-top:1px solid #efeff2; padding:11px 0; }
.activity:first-of-type { border-top:none; }
.activity strong { display:block; font-size:.78rem; }
.activity small { color:#9698a0; font-size:.7rem; }
.risk-card { border-radius:19px; padding:24px; margin:12px 0; border:1px solid; }
.risk-card h2 { margin:0 0 6px; }
.risk-low { background:#ebf7ef; border-color:#d2ebdc; color:#285d40; }
.risk-medium { background:#fff4e6; border-color:#f6dfbb; color:#865a21; }
.risk-high { background:#fff0ec; border-color:#f3cec5; color:#a33b31; }
.risk-card p { margin:0; color:inherit; }
.tiny-note { color:#9a9ca5; font-size:.7rem; }
@media(max-width:900px) { .hero-content { max-width:100%; } .hero { background:linear-gradient(90deg,rgba(253,251,246,.96),rgba(253,251,246,.75)), url('__HERO_IMAGE__') center/cover; } .topline { flex-wrap:wrap; } }
</style>
""".replace("__HERO_IMAGE__", hero_url),
        unsafe_allow_html=True,
    )
