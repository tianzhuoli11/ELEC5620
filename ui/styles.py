"""Compact, responsive styles for the operational home console."""

import streamlit as st


def apply_styles() -> None:
    st.markdown("""
<style>
:root{--ink:#28372e;--muted:#7b867d;--line:#e0e7df;--accent:#b9674b}
html,body,[data-testid="stApp"]{font-family:"Segoe UI",Arial,sans-serif;color:var(--ink)}
[data-testid="stAppViewContainer"]{background:linear-gradient(135deg,#f9f9f2,#eff5f0 70%,#f3f5f0)}
[data-testid="stHeader"]{background:transparent}
/* The toolbar also owns the sidebar opener: never hide the whole toolbar. */
[data-testid="stToolbarActions"],[data-testid="stAppDeployButton"],[data-testid="stMainMenu"]{display:none}
[data-testid="stExpandSidebarButton"]{background:#fff;border:1px solid var(--line);border-radius:9px;color:#65755f;margin:8px;min-width:36px;min-height:36px}
[data-testid="stExpandSidebarButton"]:focus-visible{outline:3px solid #c6d7c2;outline-offset:2px}
[data-testid="stSidebar"]{background:#fdfdf9;border-right:1px solid #e4e9de}
[data-testid="stSidebar"][data-collapsed="false"]{min-width:220px!important;width:220px!important;max-width:220px!important}
[data-testid="stSidebar"][data-collapsed="true"]{min-width:0!important;width:0!important;max-width:0!important;border-right:0}
[data-testid="stSidebar"]>div:first-child{padding-top:1.1rem}
.block-container{max-width:1500px;padding:2rem 2.2rem 2.5rem}
[data-testid="stAppViewContainer"]:has([data-testid="stSidebar"][data-collapsed="true"]) .block-container{padding-top:4rem}
h1,h2,h3{font-family:"Segoe UI",Arial,sans-serif;letter-spacing:-.035em;color:var(--ink);font-weight:600!important}
h1{font-size:1.7rem!important;line-height:1.2!important;margin:0 0 6px!important}h2{font-size:1rem!important;margin:0!important}h3{font-size:1.08rem!important}
p{line-height:1.5}svg{width:21px;height:21px;flex-shrink:0}
.brand{display:flex;align-items:center;font-size:1.8rem;line-height:1;letter-spacing:-.075em;font-weight:700;gap:9px;margin-bottom:24px}
.brand-icon{display:grid;place-items:center;width:35px;height:35px;border-radius:10px;background:#f5e8dc;color:#95694d}.brand-dot{color:#c78364;margin-left:-8px}
.home-picker{display:flex;align-items:center;gap:10px;padding:11px 10px;background:#f0f3eb;border:1px solid #e6eadf;border-radius:10px;margin-bottom:24px}
.home-avatar{display:grid;place-items:center;background:#e2e9d9;width:30px;height:30px;border-radius:8px;color:#6c775a;font-size:.75rem;font-weight:700}.home-picker strong{font-size:.8rem;display:block}.home-picker small{display:block;color:#929c89;font-size:.64rem;margin-top:3px}
[data-testid="stSidebar"] [data-testid="stRadio"]>label{font-size:.62rem;color:#949f8a;letter-spacing:.12em;font-weight:700;margin-bottom:8px}
[data-testid="stSidebar"] [role="radiogroup"]{gap:4px;width:100%}
[data-testid="stSidebar"] [data-testid="stRadioOption"]{width:100%!important;min-width:100%!important;max-width:none!important;box-sizing:border-box}
[data-testid="stSidebar"] [data-testid="stRadioOption"]>div>div:first-child{display:none}
[data-testid="stSidebar"] [role="radiogroup"] label{padding:10px 12px!important;border-radius:9px;cursor:pointer;margin:0}
[data-testid="stSidebar"] [role="radiogroup"] label:hover{background:#edf2e7}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){background:#e7efdf}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p{color:#60734d!important;font-weight:600}
[data-testid="stSidebar"] [role="radiogroup"] p{font-size:.79rem;color:#748269}
.sidebar-footer{margin-top:55px;border-top:1px solid #e5eadf;padding-top:17px;color:#748269;font-size:.73rem}.sidebar-footer small{display:block;font-size:.62rem;color:#99a28f;line-height:1.6;margin-top:7px}.status-dot{display:inline-block;background:#93a87b;width:6px;height:6px;border-radius:50%;margin-right:7px}
.topbar{display:flex;justify-content:space-between;align-items:center;gap:15px;margin-bottom:21px;font-size:.7rem}.breadcrumb{font-size:.59rem;letter-spacing:.12em;color:#9aa591;margin-right:10px}.topbar strong{font-weight:600;color:#708063}.topbar-right{display:flex;align-items:center;gap:15px;color:#929e88;font-size:.65rem}.demo-badge{border:1px solid #dce4d4;border-radius:99px;padding:5px 9px;color:#7b896c;font-size:.61rem;white-space:nowrap;background:#ffffff80}
.page-heading{margin-bottom:17px}.page-heading p{color:var(--muted);font-size:.79rem;margin:0}
.status-card{border:1px solid #e4e9df;border-radius:13px;background:#ffffffb8;padding:14px 17px;margin-bottom:6px;min-height:105px}.status-card>span{font-size:.55rem;letter-spacing:.08em;color:#98a18f;font-weight:600;display:block}.status-card>strong{font-size:1.5rem;font-weight:500;letter-spacing:-.04em;display:block;margin:8px 0 4px;line-height:1.2}.status-card>small{font-size:.61rem;color:#a2aa99}.status-card .status-high{color:#b46748;font-size:1.12rem}.status-card .status-medium{color:#b08a4f;font-size:1.12rem}.status-card .status-low{color:#718e5c;font-size:1.12rem}.status-card .status-unknown{color:#a0aa93;font-size:1.12rem}
.st-key-pet-controls,.st-key-check-result,.st-key-smart-home-controls,.st-key-smart-home-result{background:#fff;border:1px solid #e0e8dc!important;border-radius:14px!important;padding:20px!important;min-height:348px}
.st-key-pet-controls [data-testid="stHorizontalBlock"]{flex-wrap:nowrap!important}
.st-key-pet-controls [data-testid="stColumn"]{min-width:0!important;flex:1 1 0!important}
.panel-heading{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:8px}.small-badge{font-size:.5rem;letter-spacing:.07em;color:#9da88d;background:#f0f4e9;padding:5px 6px;border-radius:5px;white-space:nowrap}
[data-testid="stSelectbox"] label p,[data-testid="stNumberInput"] label p{font-size:.72rem!important;color:#708063}
[data-testid="stCaptionContainer"] p{font-size:.65rem!important;color:#98a28d}
[data-testid="stButton"] button{border-radius:8px;min-height:2.45rem;border:1px solid #dce4d4;color:#7e896f;background:#fff;transition:all .15s}
[data-testid="stButton"] button p{font-size:.73rem;font-weight:600}
[data-testid="stButton"] button:hover{border-color:#b7c8a7;background:#f3f7ee;color:#6d8257}
[data-testid="stButton"] button[kind="primary"]{background:#748e5b;color:#fff;border-color:#748e5b}
[data-testid="stButton"] button[kind="primary"]:hover{background:#647d4d;border-color:#647d4d;color:#fff}
[data-testid="stButton"] button:focus-visible{outline:3px solid #c6d7b7;outline-offset:2px}
[data-testid="stExpander"]{border:1px solid #e3e9de!important;border-radius:9px!important}[data-testid="stExpander"] summary p{font-size:.69rem!important;color:#859478}
.result-placeholder{padding:42px 15px;text-align:center;min-height:235px;display:flex;flex-direction:column;justify-content:center;align-items:center}.waiting-dot{height:12px;width:12px;border-radius:50%;background:#d9e5ce;box-shadow:0 0 0 9px #f3f7ec;margin-bottom:22px}.result-placeholder h3{font-size:1rem!important;color:#879b74;margin:0 0 8px}.result-placeholder p{font-size:.74rem;color:#a0ae94;margin:0;max-width:230px}
.result-banner{border-radius:10px;padding:15px 17px;margin:3px 0 12px;border-left:3px solid}.risk-low{background:#eef5e7;border-color:#a5bd8c;color:#6b8654}.risk-medium{background:#fcf4e7;border-color:#d1b17e;color:#a37f47}.risk-high{background:#fcf0e8;border-color:#cd9a7e;color:#a96e4c}.risk-label{font-size:.53rem;letter-spacing:.1em;font-weight:600;opacity:.8}.result-banner h3{color:inherit;margin:6px 0!important;font-size:1.1rem!important}.result-banner p{font-size:.74rem;line-height:1.6;margin:0;opacity:.85}
.next-step>span{font-size:.53rem;letter-spacing:.1em;color:#a1ad95}.next-step p{font-size:.76rem;color:#78876b;margin:5px 0 0;line-height:1.6}.completion-line{display:flex;align-items:center;gap:6px;color:#8c9e7c;font-size:.62rem}.completion-line svg{width:15px;height:15px}.completion-line>span{color:#bac4ae;margin:0 3px}
.section-line{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:22px 0 8px}.section-line h2{font-size:1rem!important}.section-line>span{font-size:.61rem;color:#9ca78f}
[data-testid="stRadio"] [role="radiogroup"] p{font-size:.71rem}
[data-testid="stDataFrame"]{border-radius:11px;overflow:hidden}
.service-row{display:flex;align-items:center;gap:10px;padding:7px 0}.service-row strong{display:block;font-size:.76rem;font-weight:600}.service-row small{font-size:.62rem;display:block;color:#a0ab94;margin-top:4px}.icon-bubble{width:32px;height:32px;border-radius:9px;display:grid;place-items:center;flex-shrink:0}.icon-bubble svg{width:18px;height:18px}.peach{background:#faeae0;color:#b47b59}.lilac{background:#eeebf5;color:#9b8eb5}.blue{background:#e7eef5;color:#829bb8}.mint{background:#e7f0e5;color:#869c78}.butter{background:#f8f0d9;color:#b8a164}
@media(max-width:1100px){.block-container{padding-left:1.5rem;padding-right:1.5rem}.topbar-right>span:first-child{display:none}[data-testid="stHorizontalBlock"]{flex-wrap:wrap;gap:.8rem!important}[data-testid="stColumn"]{min-width:220px!important;flex:1 1 240px!important;width:auto!important}.status-card{min-height:95px}}
@media(max-width:650px){.block-container{padding:1rem 1rem 2rem}.breadcrumb{display:none}h1{font-size:1.5rem!important}.topbar{margin-bottom:17px}[data-testid="stColumn"]{min-width:100%!important}.status-card{min-height:auto;margin-bottom:0;padding:10px 13px}.status-card>strong{font-size:1.25rem;margin:5px 0}.st-key-pet-controls,.st-key-check-result,.st-key-smart-home-controls,.st-key-smart-home-result{padding:16px!important;min-height:auto}.section-line>span{display:none}.sidebar-footer{margin-top:30px}}
</style>
""", unsafe_allow_html=True)
