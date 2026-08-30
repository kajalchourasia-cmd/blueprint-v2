import html

import streamlit as st

from blueprint.auth import handle_logout_query, require_auth
from blueprint.app_navigation import render_app_navigation
from blueprint.product_dashboard_v2 import _get, _title
from blueprint.state import reset


st.set_page_config(page_title="User Inputs · Blueprint", page_icon="🎛️", layout="wide", initial_sidebar_state="collapsed")
handle_logout_query()
require_auth()
reset()
render_app_navigation("inputs")
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600&display=swap');
[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stSidebar"],#MainMenu,footer{display:none!important}[data-testid="stAppViewContainer"]{background:linear-gradient(145deg,#f7f7f4,#e9eae7);color:#1c1f1d}.block-container{max-width:1240px;padding:38px 55px 90px 100px}.input-kicker{color:#727873;font:10px 'DM Mono';letter-spacing:.1em}.input-title{max-width:750px;margin:14px 0 12px;font:500 58px/.94 'Space Grotesk';letter-spacing:-.075em}.input-intro{max-width:690px;margin-bottom:34px;color:#707570;font:14px/1.5 'Space Grotesk'}.input-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:13px}.input-card{min-height:112px;padding:19px;border:1px solid #d3d5d2;border-radius:22px;background:rgba(255,255,255,.74)}.input-card span{display:block;color:#929692;font:8px 'DM Mono';letter-spacing:.08em}.input-card strong{display:block;margin-top:12px;font:500 17px/1.35 'Space Grotesk';letter-spacing:-.025em}.input-card small{display:block;margin-top:7px;color:#858985;font-size:10px}.input-footer{margin-top:28px;padding:24px;border-radius:25px;background:#202321;color:#f4f6f2;display:flex;justify-content:space-between;align-items:center;gap:20px}.input-footer h3{margin:0;font:500 22px 'Space Grotesk'}.input-footer p{margin:6px 0 0;color:#adb3ae;font-size:11px}.input-footer a{padding:12px 15px;border-radius:15px;background:#fff;color:#202321;text-decoration:none;font:9px 'DM Mono';white-space:nowrap}@media(max-width:760px){.block-container{padding:28px 18px 90px}.input-grid{grid-template-columns:1fr}.input-title{font-size:44px}.input-footer{display:block}.input-footer a{display:inline-block;margin-top:18px}}
</style>
""",
    unsafe_allow_html=True,
)

profile = st.session_state.get("profile")
answers = st.session_state.get("dialog_answers", {})
idea = str(_get(profile, "idea", answers.get("idea", "No Blueprint created yet")))
st.markdown(
    f'<div class="input-kicker">FIRST-PARTY CONTEXT / USER PROVIDED</div><h1 class="input-title">Inputs for {html.escape(_title(idea))}</h1><p class="input-intro">These are the facts Blueprint received directly from you. They may shape the plan, but they are not treated as proof that the market wants the idea.</p>',
    unsafe_allow_html=True,
)

fields = [
    ("Idea", idea, "Required"),
    ("Idea type", str(_get(profile, "idea_type", ", ".join(answers.get("idea_type", [])) or "Not captured")).replace("_", " ").title(), "Required"),
    ("Target customer", str(_get(profile, "target_customer", ", ".join(answers.get("target_customer", [])) or "Not captured")), "Required"),
    ("Market / location", str(_get(profile, "location", answers.get("location", "Not captured"))), "Required"),
    ("Personal goal", str(_get(profile, "goal", answers.get("goal", "Not captured"))).replace("_", " ").title(), "Required"),
    ("Success definition", str(_get(profile, "success_definition", answers.get("success_definition", "Not captured"))), "Required"),
    ("Capital available", f'${int(_get(profile, "money_available", answers.get("money_available", 0)) or 0):,}', "Planning constraint"),
    ("Weekly capacity", f'{int(_get(profile, "hours_per_week", answers.get("hours_per_week", 0)) or 0)} hours', "Planning constraint"),
    ("Target timeline", str(_get(profile, "launch_timeline", answers.get("launch_timeline", "Not captured"))), "Planning constraint"),
    ("Prior work", str(_get(profile, "current_work", ", ".join(answers.get("prior_work", [])) or "Nothing recorded")), "Starting position"),
    ("Life constraints", ", ".join(_get(profile, "constraints", answers.get("constraints", [])) or []) or "None recorded", "Starting position"),
    ("Additional context", str(_get(profile, "background", answers.get("goal_detail", "Not captured"))) or "Not captured", "Optional"),
]
cards = "".join(f'<article class="input-card"><span>{html.escape(label.upper())}</span><strong>{html.escape(value)}</strong><small>{kind}</small></article>' for label, value, kind in fields)
st.markdown(f'<section class="input-grid">{cards}</section><div class="input-footer"><div><h3>Something changed?</h3><p>Edit the starting context before relying on later recommendations.</p></div><a href="/Profile_Settings">EDIT USER INPUTS →</a></div>', unsafe_allow_html=True)
