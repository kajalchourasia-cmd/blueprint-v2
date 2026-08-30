from pathlib import Path

import pandas as pd
import streamlit as st

from blueprint.auth import handle_logout_query, require_auth
from blueprint.app_navigation import render_app_navigation


st.set_page_config(page_title="Blueprint Data Library", page_icon="▦", layout="wide", initial_sidebar_state="collapsed")
handle_logout_query()
require_auth()
render_app_navigation("data")

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
FILES = {
    "Online idea master — 60 fields": "blueprint_idea_master.csv",
    "Observed evidence events": "blueprint_evidence_events.csv",
    "Detailed phase actions": "blueprint_phase_actions.csv",
    "Signal benchmarks": "blueprint_signal_benchmarks.csv",
    "Financial models": "blueprint_financial_models.csv",
    "Comparable founder journeys": "founder_journeys.csv",
    "Real-cost templates": "cost_templates.csv",
    "Gap library": "gap_library.csv",
}

st.markdown(
    """
    <style>
    [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stSidebar"], #MainMenu, footer { display:none!important; }
    [data-testid="stAppViewContainer"] { background:#ececeb; color:#1d1d1d; }
    .block-container { max-width:1450px; padding:38px 42px 70px 100px; }
    h1 { font:400 48px/1 -apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif!important; letter-spacing:-.07em!important; }
    .data-intro { max-width:700px; margin:4px 0 28px; color:#707070; font-size:14px; line-height:1.5; }
    [data-testid="stMetric"] { padding:18px; border-radius:20px; background:#fff; }
    [data-testid="stDataFrame"] { border-radius:22px; overflow:hidden; }
    .stDownloadButton button { border-radius:22px!important; border:0!important; background:#fff!important; color:#222!important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<a href="/" style="color:#222;text-decoration:none;font-size:13px">← Back to dashboard</a>', unsafe_allow_html=True)
st.title("Blueprint data library")
st.markdown(
    '<div class="data-intro">Inspect the exact records used to shape phases, actions, evidence thresholds, financial allocation, reality checks, and real-cost estimates. Synthetic seed records are labeled and must not be treated as verified market facts.</div>',
    unsafe_allow_html=True,
)

selected_label = st.selectbox("Dataset", list(FILES))
selected_file = FILES[selected_label]
try:
    frame = pd.read_csv(DATA_DIR / selected_file)
except pd.errors.ParserError:
    # Legacy seed files may contain unquoted commas. Keep the inspector usable
    # while surfacing only structurally valid records.
    frame = pd.read_csv(DATA_DIR / selected_file, engine="python", on_bad_lines="skip")
frame = frame.replace({r"Proofpath": "Blueprint", r"proofpath": "blueprint"}, regex=True)

left, middle, right = st.columns(3)
left.metric("Rows", f"{len(frame):,}")
middle.metric("Columns", f"{len(frame.columns):,}")
right.metric("Missing cells", f"{int(frame.isna().sum().sum()):,}")

st.subheader(selected_label)
st.dataframe(frame, width="stretch", hide_index=True, height=560)
st.download_button(
    "Download this CSV",
    data=frame.to_csv(index=False).encode("utf-8"),
    file_name=selected_file,
    mime="text/csv",
)

with st.expander("View all column names"):
    st.write(list(frame.columns))

st.markdown("## Data provenance and next sources")
st.caption("Blueprint must show where a value came from before presenting it as a signal.")
source_rows = pd.DataFrame(
    [
        {"Source": "User onboarding", "Status": "Connected", "Use": "Founder context, budget, time, goal, constraints", "Trust rule": "First-party input; not market proof"},
        {"Source": "Evidence event ledger", "Status": "Connected; empty for a new idea", "Use": "Interviews, tests, deposits, purchases, repeat use", "Trust rule": "Only observed events can create positive signals"},
        {"Source": "Blueprint CSV planning priors", "Status": "Connected", "Use": "Suggested phases, actions, costs, thresholds", "Trust rule": "Synthetic rows remain labeled as planning priors"},
        {"Source": "User uploads", "Status": "Next", "Use": "Research notes, exports, interviews, financial documents", "Trust rule": "Keep source file, date, and extraction confidence"},
        {"Source": "Official open data", "Status": "Next", "Use": "Population, geography, industry, public-health and economic context", "Trust rule": "Cite agency, dataset, geography, and update date"},
        {"Source": "Search-interest data", "Status": "Next", "Use": "Relative topic demand and seasonality", "Trust rule": "Directional only; never equate searches with purchases"},
        {"Source": "Marketplace / competitor listings", "Status": "Next", "Use": "Pricing, category density, feature and review themes", "Trust rule": "Respect terms and preserve listing date"},
        {"Source": "Official company pages and filings", "Status": "Next", "Use": "Verified pricing, positioning, market disclosures", "Trust rule": "Prefer primary sources over summaries"},
    ]
)
st.dataframe(source_rows, width="stretch", hide_index=True)
