import streamlit as st
from blueprint.auth import handle_logout_query, require_auth
from blueprint.app_navigation import render_app_navigation
from blueprint.state import reset
from blueprint.schemas import UserProfile

st.set_page_config(page_title="Profile / Settings · Blueprint", page_icon="⚙️", layout="wide")
handle_logout_query()
require_auth()
reset()
render_app_navigation("")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600&display=swap');
:root{--paper:#f7f8f6;--ink:#243330;--muted:#788480;--green:#117025;--line:#d9e1dc}
[data-testid="stAppViewContainer"],[data-testid="stHeader"]{background:var(--paper)}main .block-container{max-width:1160px;padding:25px 4vw 90px 100px;color:var(--ink)}
.nav{display:flex;justify-content:space-between;border-bottom:1px solid var(--line);padding-bottom:16px;color:var(--muted);font:12px 'DM Mono',monospace;text-transform:uppercase}.kicker{margin-top:42px;color:var(--green);font:12px 'DM Mono',monospace;letter-spacing:.1em;text-transform:uppercase}.title{margin:10px 0 34px;font:500 64px/.9 'Space Grotesk',sans-serif;letter-spacing:-.08em}.stButton button{border-radius:5px!important;background:#117025!important;color:#fff!important;border:1px solid #117025!important;font:500 12px 'DM Mono',monospace!important}.stTextInput input,.stTextArea textarea,.stSelectbox>div,.stMultiSelect>div{background:#fff!important;border:1px solid var(--line)!important;border-radius:6px!important}.stTextInput label,.stTextArea label,.stSelectbox label,.stMultiSelect label{color:var(--ink)!important;font:500 13px 'DM Mono',monospace!important}.stExpander{border:1px solid var(--line)!important;border-radius:8px!important;background:#fff!important}
</style>
<div class="nav"><span>BLUEPRINT / ALPHA</span><span>GLOBAL PROJECT SETTINGS</span><span>PROFILE</span></div>
<div class="kicker">Project context</div><div class="title">Profile / Settings</div>
""", unsafe_allow_html=True)

profile = st.session_state.get("profile")
if not profile:
    st.info("Create a Blueprint first to edit its project context.")
    st.markdown('<a href="/" style="color:#117025;text-decoration:none">Return to Blueprint home →</a>', unsafe_allow_html=True)
    st.stop()

st.markdown('<a href="/Your_Plan" style="color:#117025;text-decoration:none">← Return to current Blueprint</a>', unsafe_allow_html=True)
st.markdown("### Project details")
c1, c2 = st.columns(2)
with c1:
    idea = st.text_input("Project name / idea", value=profile.idea)
    location = st.text_input("Location / geography", value=profile.location)
    target_customer = st.text_input("Target customer", value=profile.target_customer)
    success = st.text_area("Definition of success", value=profile.success_definition, height=90)
with c2:
    goal = st.text_input("Primary goal", value=profile.goal.replace("_", " ").title())
    launch = st.selectbox("Target launch or test timeline", ["Within 30 days", "Within 3 months", "Within 6 months", "Within 12 months", "No fixed date", "Not sure"], index=["Within 30 days", "Within 3 months", "Within 6 months", "Within 12 months", "No fixed date", "Not sure"].index(profile.launch_timeline) if profile.launch_timeline in ["Within 30 days", "Within 3 months", "Within 6 months", "Within 12 months", "No fixed date", "Not sure"] else 5)
    budget = st.number_input("Available budget", min_value=0, value=profile.money_available, step=500)
    hours = st.slider("Hours available per week", 0, 40, profile.hours_per_week)

st.markdown("### Experience and constraints")
background = st.text_area("What have you already done?", value=profile.current_work, height=90)
constraints = st.multiselect("Constraints", ["Full-time job", "Caregiving", "School", "Debt or financial pressure", "Health constraint", "Relocation", "Need predictable income"], default=profile.constraints)

st.markdown("### Preferences")
pref1, pref2 = st.columns(2)
with pref1:
    st.toggle("Ask before applying material Blueprint changes", value=True)
with pref2:
    st.toggle("Show cost warnings before high-commitment steps", value=True)

if st.button("Save project context", type="primary"):
    updated = UserProfile(idea=idea, idea_type=profile.idea_type, location=location, target_customer=target_customer, background=profile.background, life_context=constraints, goal=profile.goal, success_definition=success, launch_timeline=launch, current_work=background, constraints=constraints, hours_per_week=hours, money_available=budget)
    st.session_state["profile"] = updated
    st.session_state.setdefault("projects", {})[idea] = {"profile": updated, "plan": st.session_state.get("plan")}
    st.success("Project context saved.")

with st.expander("Uploaded evidence", expanded=False):
    st.caption("Documents, spreadsheets, images, and notes will be analyzed and linked to Blueprint, Plan, Progress, or Ledger in a later evidence pass.")
    st.file_uploader("Add research or a business document", accept_multiple_files=True)
