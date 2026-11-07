from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
LOGO = ROOT / "assets" / "move30-logo.svg"

st.set_page_config(
    page_title="MOVE30 | Dashboards",
    page_icon=":material/monitor_heart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.html("""
<style>
:root {
  --move-navy:#030b18; --move-panel:#071a30; --move-panel-light:#0a2340;
  --move-border:#16436a; --move-text:#f4f8ff; --move-muted:#a9c0d9;
  --move-pre:#22b8ff; --move-post:#13d6a0; --move-score:#ffc83d;
  --move-alert:#ff5b70; --move-purple:#b28bff;
}
[data-testid="stAppViewContainer"] { background:radial-gradient(ellipse at 12% 0%,#0b2545 0%,#030b18 58%); }
[data-testid="stMain"] > div, .main > div.block-container { max-width:none !important; width:100% !important; padding-left:clamp(1.25rem,2.2vw,2.75rem) !important; padding-right:clamp(1.25rem,2.2vw,2.75rem) !important; }
[data-testid="stSidebar"][aria-expanded="true"] { min-width:15rem; max-width:15rem; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#020916 0%,#04142a 100%); border-right:1px solid var(--move-border); }
[data-testid="stSidebarContent"] { padding-top:1.1rem; }
[data-testid="stVerticalBlockBorderWrapper"] { background:linear-gradient(145deg,rgba(8,29,53,.96),rgba(3,15,31,.98)); border-color:rgba(34,184,255,.28); border-radius:10px; box-shadow:0 8px 26px rgba(0,0,0,.2); }
[data-testid="stMetric"] { min-height:112px; padding:14px 16px; border:1px solid rgba(34,184,255,.22); border-radius:14px; background:linear-gradient(150deg,#0a2340,#041226); box-shadow:inset 0 1px 0 rgba(255,255,255,.035),0 7px 20px rgba(0,0,0,.16); }
[data-testid="stMetricLabel"] { color:#c6d8ef; } [data-testid="stMetricValue"] { color:var(--move-text); }
[data-testid="stPageLink-NavLink"] { border:1px solid transparent; border-radius:10px; padding:.58rem .72rem; transition:all .18s ease; }
[data-testid="stPageLink-NavLink"]:hover { border-color:rgba(34,184,255,.52); background:rgba(7,135,249,.13); }
h1,h2,h3 { letter-spacing:-.025em; }
.move-icon { flex:none; filter:drop-shadow(0 0 5px color-mix(in srgb,currentColor 25%,transparent)); }
.move-kpi-value { font-size:clamp(1.55rem,2vw,2rem); line-height:1.2; font-weight:720; letter-spacing:-.04em; padding:4px 0 0 33px; white-space:nowrap; }
.move-kpi-value--pre { color:var(--move-pre); text-shadow:0 0 14px rgba(34,184,255,.18); }
.move-kpi-value--post { color:var(--move-post); text-shadow:0 0 14px rgba(19,214,160,.16); }
.move-kpi-value--score { color:var(--move-score); text-shadow:0 0 14px rgba(255,200,61,.16); }
.move-kpi-value--alert { color:var(--move-alert); }
.move-kpi-value--purple { color:var(--move-purple); }
[class*="st-key-move-kpi-"] h3 { font-size:.98rem !important; line-height:1.25 !important; min-height:2.35rem; margin-bottom:.15rem !important; }
[class*="st-key-move-kpi-"] [data-testid="stMarkdownContainer"] { overflow-wrap:anywhere; }
[data-testid="stPlotlyChart"] { border-radius:9px; }
@media (max-width:700px) { .move-kpi-value { padding:12px 0 0 30px; font-size:1.45rem; } }
</style>
""")

personal = st.Page("app_pages/pessoal.py", title="Dashboard pessoal", icon=":material/person:", url_path="pessoal")
collective = st.Page("app_pages/coletivo.py", title="Dashboard geral", icon=":material/desktop_windows:", url_path="coletivo")
station = st.Page("app_pages/estacao.py", title="Estação de medição", icon=":material/sensors:", url_path="estacao")
navigation = st.navigation([personal, collective, station], position="hidden")

with st.sidebar:
    st.image(str(LOGO), width=190, alt="MOVE30")
    st.caption("Mais movimento,\nmais saúde.")
    st.space("medium")
    st.page_link(personal, label="Dashboard pessoal", icon=":material/person:", width="stretch")
    st.page_link(collective, label="Dashboard geral", icon=":material/desktop_windows:", width="stretch")
    st.page_link(station, label="Estação de medição", icon=":material/sensors:", width="stretch")
    st.space("large")
    st.caption(":material/qr_code_2:  Acessar pelo QR Code impresso")
    st.divider()
    st.image(str(LOGO), width=135, alt="MOVE30")
    st.caption("Mais movimento,\nmais saúde.")

navigation.run()
