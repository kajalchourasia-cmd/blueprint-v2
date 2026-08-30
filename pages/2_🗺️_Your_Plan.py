import html
import io
import re
import zipfile
import xml.etree.ElementTree as ET

import plotly.graph_objects as go
import streamlit as st

from blueprint.auth import handle_logout_query, require_auth
from blueprint.backend_ui import render_backend_status_panel, render_research_workspace
from blueprint.product_dashboard_v2 import render_product_dashboard_v2
from blueprint.blueprint_map import render_blueprint_map
from blueprint.coach import chat
from blueprint.cost_calculator import add_delta, compute_initial, mark_done
from blueprint.gap_generator import generate as generate_gap
from blueprint.plan_generator import generate as generate_plan
from blueprint.reality_check import generate as generate_reality
from blueprint.state import reset

st.set_page_config(page_title="Blueprint", page_icon="⌁", layout="wide", initial_sidebar_state="collapsed")
handle_logout_query()
require_auth()

if working_note := st.query_params.get("working_note"):
    st.session_state["working_note"] = str(working_note).strip()[:1200]
    st.query_params.clear()
    st.rerun()

if action_key := st.query_params.get("complete_action"):
    completed_actions = set(st.session_state.get("completed_steps", set()))
    action_key = str(action_key)
    if action_key in completed_actions:
        completed_actions.remove(action_key)
    else:
        completed_actions.add(action_key)
    st.session_state["completed_steps"] = completed_actions
    st.query_params.clear()
    st.rerun()

if st.query_params.get("view") == "blueprint":
    render_blueprint_map()
    st.stop()
else:
    render_backend_status_panel()
    render_research_workspace()
    render_product_dashboard_v2()
    st.stop()


st.set_page_config(page_title="Blueprint", page_icon="⌖", layout="wide", initial_sidebar_state="collapsed")
reset()
profile = st.session_state.get("profile")
if not profile:
    st.switch_page("app.py")
st.session_state.setdefault("projects", {})
st.session_state.setdefault("selected_step", None)
st.session_state.setdefault("applied_gap_costs", set())
st.session_state.setdefault("node_evidence", {})


def project_title(idea: str) -> str:
    clean = re.sub(r"\s+", " ", idea.strip()).rstrip(".!?")
    clean = re.sub(r"^(i\s+(?:want|would like|plan|hope)\s+to|my idea is to|we want to)\s+", "", clean, flags=re.I)
    match = re.match(r"open\s+(?:an?\s+)?(.+?)\s+in\s+(.+)$", clean, re.I)
    if match:
        business, location = match.groups()
        business = re.sub(r"^(specialty|small|new)\s+", "", business, flags=re.I)
        return f"{location.title()} {business.title()}"
    clean = re.sub(r"^(build|create|launch|start|open)\s+(?:an?\s+)?", "", clean, flags=re.I)
    return " ".join(clean.split()[:7]).title() or "Untitled Blueprint"


def phase_for(step_type: str) -> str:
    if step_type in {"research", "interview", "learn_skill"}:
        return "Understand"
    if step_type in {"validate", "measure"}:
        return "Validate"
    if step_type in {"launch", "sell"}:
        return "Launch"
    return "Build"


def step_support(step) -> dict[str, list[str] | str]:
    coffee = "coffee" in profile.idea.lower() or "cafe" in profile.idea.lower()
    location = re.sub(r"\s+", "+", profile.location.strip() or "Pune")
    return {
        "checklist": getattr(step, "action_checklist", None) or [
            f"Write the assumption this step must test: {step.name}.",
            "Prepare one evidence sheet before contacting anyone.",
            "Complete the field work and record exact words or behaviour.",
            "Compare the result with a pass/fail threshold.",
            "Write a continue, change, or stop decision.",
        ],
        "people": getattr(step, "people_to_contact", None) or ([
            "Independent cafe owner", "Cafe manager", "Morning-shift barista", "Morning commuter", "Office administrator"
        ] if coffee else ["Target user", "Recent buyer of an alternative", "Budget owner", "Front-line operator"]),
        "places": getattr(step, "places_or_channels", None) or ([
            f"[Google Maps: specialty coffee near {profile.location or 'Pune'}](https://www.google.com/maps/search/specialty+coffee+{location})",
            "Koregaon Park and Kalyani Nagar cafe clusters",
            "Baner and Aundh weekday cafe corridors",
            "Viman Nagar offices and co-working spaces",
            f"[Search local cafe reviews](https://www.google.com/search?q=best+cafes+{location}+reviews)",
        ] if coffee else ["LinkedIn role and location filters", "Relevant Reddit and community searches", "Competitor review pages", "Industry directories"]),
        "evidence": getattr(step, "evidence_to_capture", None) or [
            "Who you contacted and why they were relevant", "Exact words or observed behaviour", "Current alternative and price", "Contradicting evidence", "Dated decision"
        ],
        "signal": getattr(step, "decision_signal", None) or "Continue only when at least half of the relevant people show the same unmet need or make a real commitment.",
        "blocker": getattr(step, "likely_blocker", None) or "Polite interest may look like demand. Treat compliments as zero evidence unless they create observable behaviour.",
    }


def extract_upload(uploaded) -> str:
    data = uploaded.getvalue()
    if uploaded.name.lower().endswith(".docx"):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
            return " ".join(node.text for node in root.iter() if node.text)
    return data.decode("utf-8", errors="ignore")


def process_locally(text: str, note: str, step_name: str) -> str:
    combined = re.sub(r"\s+", " ", f"{note} {text}").strip()
    sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", combined) if item.strip()]
    preview = " ".join(sentences[:3])[:850] or "No readable text was found."
    commitments = [term for term in ["paid", "deposit", "booked", "bought", "ordered", "introduced"] if term in combined.lower()]
    cautions = [term for term in ["but", "however", "not", "expensive", "difficult", "stopped"] if term in combined.lower()]
    return f"**Local evidence review for {step_name}**\n\n{preview}\n\n- Words captured: {len(combined.split())}\n- Commitment signals: {', '.join(commitments) if commitments else 'none found'}\n- Caution signals: {', '.join(cautions) if cautions else 'none found'}\n- Next review: compare this with the decision signal before completion."


if "reality" not in st.session_state:
    with st.spinner("Building your Blueprint..."):
        st.session_state["reality"] = generate_reality(profile)
        st.session_state["plan"] = generate_plan(profile)
        st.session_state["ledger"] = compute_initial(st.session_state["plan"])
        st.session_state["projects"].setdefault(profile.idea, {})["profile"] = profile
        st.session_state["projects"][profile.idea]["plan"] = st.session_state["plan"]

reality = st.session_state["reality"]
plan = st.session_state["plan"]
ledger = st.session_state["ledger"]
current = next((step for step in plan.steps if step.number not in st.session_state["done_steps"]), plan.steps[-1])
selected_query = st.query_params.get("node")
if selected_query and str(selected_query).isdigit():
    st.session_state["selected_step"] = int(selected_query)
selected = next((step for step in plan.steps if step.number == st.session_state["selected_step"]), None)
completed = len(st.session_state["done_steps"])
percent = round(completed / len(plan.steps) * 100) if plan.steps else 0
title = project_title(profile.idea)


st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600&display=swap');
:root{--bg:#e7e7e7;--ink:#242424;--muted:#8c8c8c;--card:#f7f7f7;--line:#dedede;--green:#c9ef00;--pink:#f04b83;--orange:#f69c26}
[data-testid="stAppViewContainer"],[data-testid="stHeader"]{background:var(--bg)}main .block-container{max-width:1600px;padding:16px 30px 70px;color:var(--ink)}
.topbar{display:flex;align-items:center;justify-content:space-between;margin-bottom:22px}.wordmark{font:600 15px 'Space Grotesk',sans-serif;letter-spacing:-.05em}.top-actions{display:flex;gap:8px;align-items:center}.top-actions a{display:grid;place-items:center;width:38px;height:38px;border-radius:50%;background:#fafafa;color:var(--ink);text-decoration:none;font-size:16px}.nav-rule{height:1px;background:#d2d2d2;margin-bottom:22px}
.side{border-right:1px solid #d2d2d2;padding-right:20px;min-height:900px}.side-tab{font:500 30px 'Space Grotesk',sans-serif;letter-spacing:-.08em;margin:8px 0 22px}.side-tab span{color:#ababab;margin-left:12px}.side-item{display:flex;justify-content:space-between;align-items:center;background:#f8f8f8;border-radius:16px;padding:14px 16px;margin:8px 0;font:12px 'Space Grotesk',sans-serif}.side-item.active{background:#fff}.side-item small{background:#eee;border-radius:12px;padding:5px 8px;color:#8a8a8a;font:10px 'DM Mono',monospace}.side-pill{display:inline-block;background:var(--green);padding:6px 10px;border-radius:14px;font:10px 'DM Mono',monospace;margin-top:24px}
.headline{font:500 clamp(38px,5vw,68px)/.94 'Space Grotesk',sans-serif;letter-spacing:-.08em;margin:5px 0 18px}.subline{color:#8b8b8b;font:12px 'DM Mono',monospace;text-transform:uppercase;letter-spacing:.06em}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:24px 0}.metric{position:relative;background:transparent;padding:10px 0}.metric b{font:40px 'DM Mono',monospace;letter-spacing:-.1em}.metric span{font:10px 'DM Mono',monospace;color:#999;text-transform:uppercase;margin-left:8px}.metric em{position:absolute;top:5px;right:18px;background:#f5f5f5;border-radius:12px;padding:5px 8px;font:9px 'DM Mono',monospace;color:#999;font-style:normal}
.timeline{background:#f4f4f4;border-radius:30px;padding:15px 25px;display:flex;align-items:center;gap:0;margin:12px 0 24px;overflow:hidden}.timeline .phase{flex:1;position:relative;text-align:center;font:10px 'DM Mono',monospace;color:#888}.timeline .phase:after{content:'';position:absolute;top:7px;left:50%;right:-50%;border-top:1px dashed #c7c7c7;z-index:0}.timeline .phase:last-child:after{display:none}.timeline i{position:relative;z-index:1;display:inline-grid;place-items:center;width:15px;height:15px;background:#cfcfcf;border-radius:50%;font-style:normal;font-size:8px}.timeline .phase.active i{background:var(--green)}.timeline .phase.active{color:var(--ink)}.timeline b{display:block;margin-top:7px;font-weight:400}
.soft-card{background:#f5f5f5;border-radius:24px;padding:23px;min-height:220px;position:relative;overflow:hidden}.soft-card h3{font:500 16px 'Space Grotesk',sans-serif;margin:0 0 10px}.soft-card p{font:12px/1.4 'Space Grotesk',sans-serif;color:#888;max-width:270px}.gradient-card{min-height:255px;border-radius:24px;padding:26px;color:#fff;position:relative;overflow:hidden;box-shadow:0 15px 35px rgba(0,0,0,.05)}.gradient-card.green{background:radial-gradient(circle at 50% 75%,#35af3e 0,#8ed74a 27%,#f0cf82 62%,#f6a885 100%)}.gradient-card.pink{background:radial-gradient(circle at 70% 45%,#f15372 0,#ef9259 32%,#c7d8bf 66%,#d6edf4 100%)}.gradient-card h3{font:500 15px 'Space Grotesk',sans-serif;text-align:center;opacity:.8}.gradient-card .big{font:58px 'DM Mono',monospace;letter-spacing:-.1em;text-align:center;margin-top:46px}.gradient-card small{display:block;text-align:center;font:11px 'DM Mono',monospace;opacity:.8}.dots{position:absolute;left:28px;right:28px;bottom:18px;height:36px;background:radial-gradient(circle,#fff 1.5px,transparent 2px);background-size:9px 9px;opacity:.55}.results{background:#fafafa;border-radius:24px;padding:25px;min-height:255px}.results h3{font:500 15px 'Space Grotesk',sans-serif;margin:0 0 26px}.results .range{font:36px 'DM Mono',monospace;margin-bottom:14px}.range-line{height:6px;background:#e2e2e2;border-radius:9px;position:relative}.range-line i{position:absolute;width:13px;height:13px;top:-4px;left:27%;border-radius:50%;background:var(--green);box-shadow:0 0 0 4px #fff}.section-title{font:500 28px 'Space Grotesk',sans-serif;letter-spacing:-.07em;margin:28px 0 13px}.section-copy{font:12px 'DM Mono',monospace;color:#999;margin-bottom:15px}.data-card{background:#fafafa;border-radius:20px;padding:18px;min-height:155px}.data-card .label{font:11px 'Space Grotesk',sans-serif;color:#888}.data-card .value{font:35px 'DM Mono',monospace;margin:20px 0 5px}.data-card small{font:10px 'DM Mono',monospace;color:#aaa}.data-card .mini-line{height:28px;margin-top:16px;background:repeating-linear-gradient(90deg,#ddd 0 2px,transparent 2px 9px);opacity:.8}.supplement{background:#fafafa;border-radius:20px;padding:16px;min-height:180px;text-align:center}.supplement .tag{display:inline-block;background:var(--green);border-radius:12px;padding:5px 8px;font:9px 'DM Mono',monospace}.supplement .orb{width:60px;height:60px;border-radius:50%;margin:20px auto 12px;background:radial-gradient(circle at 35% 30%,#f8ffcf,#6db47d 60%,#2c6b3d);box-shadow:0 12px 18px rgba(52,121,64,.25)}.supplement b{font:18px 'DM Mono',monospace}.panel{background:#f7f7f7;border-radius:24px;padding:20px;position:sticky;top:15px;max-height:calc(100vh - 30px);overflow:auto}.panel h2{font:500 25px 'Space Grotesk',sans-serif;letter-spacing:-.06em;margin:8px 0 10px}.panel .eyebrow{font:10px 'DM Mono',monospace;color:#888;text-transform:uppercase}.panel-section{border-top:1px solid #dedede;margin-top:18px;padding-top:15px}.panel-section h4{font:10px 'DM Mono',monospace;text-transform:uppercase;color:#888;margin:0 0 10px}.panel-section li{font:12px/1.45 'Space Grotesk',sans-serif;margin:6px 0}.panel-note{background:#fff;border-radius:14px;padding:12px;font:11px/1.45 'DM Mono',monospace;color:#777}.stButton button{border:0!important;border-radius:12px!important;background:#f7f7f7!important;color:var(--ink)!important;font:11px 'DM Mono',monospace!important}.stButton button:hover{background:var(--green)!important}.stTextInput input,.stTextArea textarea,.stFileUploader{background:#fff!important;border:1px solid #dedede!important;border-radius:11px!important}.stTabs [data-baseweb="tab-list"]{background:transparent;border-bottom:1px solid #d4d4d4;gap:28px}.stTabs [data-baseweb="tab"]{font:11px 'DM Mono',monospace;color:#999;text-transform:uppercase;padding:10px 0}.stTabs [aria-selected="true"]{color:var(--ink)!important;border-bottom:2px solid var(--ink)!important}.stMetric{background:#fafafa;border:0;border-radius:16px}.stMetric label,.stMetric [data-testid="stMetricValue"]{color:var(--ink)!important}@media(max-width:950px){.side{border:0;min-height:auto}.metrics{grid-template-columns:repeat(2,1fr)}.panel{position:relative;max-height:none}.headline{font-size:42px}}
</style>
""", unsafe_allow_html=True)


top_left, top_space, top_right = st.columns([2, 6, 1.2], vertical_alignment="center")
with top_left:
    st.page_link("app.py", label="Blueprint")
with top_right:
    st.page_link("pages/3_⚙️_Profile_Settings.py", label="◌ Profile")
st.markdown('<div class="nav-rule"></div>', unsafe_allow_html=True)

side, content = st.columns([1.05, 4.5], gap="large")
with side:
    st.markdown('<div class="side-tab">Data <span>Records</span></div>', unsafe_allow_html=True)
    side_items = [
        ("▧", "All Blueprint", len(plan.steps)),
        ("✧", "Reality signals", reality.fit_score),
        ("♡", "Evidence", len(st.session_state.get("node_evidence", {}))),
        ("⌁", "Experiments", sum(1 for step in plan.steps if step.step_type == "validate")),
        ("○", "Decisions", completed),
        ("⌁", "Real cost", f"${ledger.cash_dollars:,}"),
    ]
    for icon, label, value in side_items:
        st.markdown(f'<div class="side-item {"active" if label == "All Blueprint" else ""}"><span>{icon} &nbsp; {label}</span><small>{value}</small></div>', unsafe_allow_html=True)
    st.markdown('<span class="side-pill">LOCAL ALPHA</span>', unsafe_allow_html=True)
    st.caption("Blueprint turns an unfinished idea into the next evidence-backed move.")

with content:
    st.markdown(f'<div class="subline">Personal blueprint · {profile.goal.replace("_", " ").title()}</div><div class="headline">{html.escape(title)}</div>', unsafe_allow_html=True)
    top_controls = st.columns([5, 1.3])
    with top_controls[1]:
        project_names = list(st.session_state["projects"].keys()) or [profile.idea]
        st.selectbox("Blueprint", project_names, label_visibility="collapsed")
    st.markdown(
        f'<div class="metrics"><div class="metric"><b>{len(plan.steps)}</b><span>steps</span><em>total</em></div><div class="metric"><b>{percent}%</b><span>complete</span><em>path</em></div><div class="metric"><b>{plan.total_estimated_days}</b><span>days</span><em>estimated</em></div><div class="metric"><b>{len(st.session_state.get("node_evidence", {}))}</b><span>evidence</span><em>recorded</em></div></div>',
        unsafe_allow_html=True,
    )
    phases = ["Understand", "Validate", "Build", "Launch"]
    active_phase = phase_for(current.step_type)
    st.markdown('<div class="timeline">' + ''.join(f'<div class="phase {"active" if phase == active_phase else ""}"><i>{index}</i><b>{phase}</b></div>' for index, phase in enumerate(phases, 1)) + '</div>', unsafe_allow_html=True)

    data_tab, records_tab = st.tabs(["Data", "Records"])
    with data_tab:
        left, right = st.columns([2.5, 1], gap="large")
        with left:
            gradient_left, gradient_right = st.columns(2, gap="medium")
            with gradient_left:
                st.markdown(f'<div class="gradient-card green"><h3>Reality signal</h3><div class="big">{reality.fit_score}/10</div><small>{html.escape(reality.fit_rationale)}</small><div class="dots"></div></div>', unsafe_allow_html=True)
            with gradient_right:
                st.markdown(f'<div class="gradient-card pink"><h3>Projected commitment</h3><div class="big">${ledger.projected_3yr_total:,}</div><small>3-year true cost</small><div class="dots"></div></div>', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Decision nodes</div><div class="section-copy">A working set of the next decisions in your path</div>', unsafe_allow_html=True)
            node_cols = st.columns(3)
            for col, step in zip(node_cols, plan.steps[:3]):
                state = "complete" if step.number in st.session_state["done_steps"] else "next" if step.number == current.number else ""
                with col:
                    st.markdown(f'<a href="?node={step.number}" style="text-decoration:none;color:inherit"><div class="data-card"><div class="label">{phase_for(step.step_type)} · {state or "up next"}</div><div class="value">{step.number:02d}</div><strong>{html.escape(step.name)}</strong><div class="mini-line"></div><small>{step.estimated_time_days} calendar days · {step.estimated_hours} hands-on hours</small></div></a>', unsafe_allow_html=True)
            st.markdown('<div class="section-title">What the path is asking of you</div><div class="section-copy">Costs shown in context, not as disconnected metrics</div>', unsafe_allow_html=True)
            effort_cols = st.columns(3)
            effort_cols[0].metric("Cash", f"${ledger.cash_dollars:,}", "expected spend")
            effort_cols[1].metric("Time", f"{ledger.hours_invested} hrs", "hands-on work")
            effort_cols[2].metric("Career trade-off", f"${ledger.opportunity_cost_dollars:,}", "value displaced")
        with right:
            with st.container(key="reference_panel"):
                if selected:
                    support = step_support(selected)
                    st.markdown('<div class="panel"><div class="eyebrow">Selected node</div><h2>' + html.escape(selected.name) + '</h2><div class="panel-note">' + html.escape(selected.what_to_do) + '</div>', unsafe_allow_html=True)
                    st.markdown('<div class="panel-section"><h4>Do this next</h4></div>', unsafe_allow_html=True)
                    for i, item in enumerate(support["checklist"], 1): st.markdown(f"{i}. {item}")
                    st.markdown('<div class="panel-section"><h4>People and places</h4></div>', unsafe_allow_html=True)
                    for item in support["people"]: st.markdown(f"- {item}")
                    for item in support["places"]: st.markdown(f"- {item}")
                    uploaded = st.file_uploader("Attach evidence", type=["txt", "md", "csv", "docx"], key=f"upload_dashboard_{selected.number}")
                    note = st.text_area("Add a note", key=f"note_dashboard_{selected.number}", height=90, placeholder="What did you learn?")
                    if st.button("Process and attach", key=f"process_dashboard_{selected.number}", type="primary", use_container_width=True):
                        if uploaded or note.strip():
                            raw = extract_upload(uploaded)[:10000] if uploaded else ""
                            st.session_state["node_evidence"].setdefault(selected.number, []).append({"file": uploaded.name if uploaded else "Typed note", "analysis": process_locally(raw, note, selected.name)})
                            st.success("Evidence attached locally.")
                        else: st.warning("Add a note or document first.")
                    if selected.number in st.session_state["done_steps"]: st.success("Completed")
                    elif st.button("Mark this node complete", key=f"complete_dashboard_{selected.number}", type="primary", use_container_width=True):
                        st.session_state["done_steps"].add(selected.number); st.session_state["ledger"] = mark_done(selected, ledger); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="panel"><div class="eyebrow">Upload records</div><h2>Build the next proof</h2><div class="panel-note">Select a decision node to see the exact people, places, evidence, and actions for that step.</div>', unsafe_allow_html=True)
                    st.file_uploader("Upload evidence", type=["txt", "md", "csv", "docx"], key="upload_empty_panel")
                    st.markdown('</div>', unsafe_allow_html=True)

    with records_tab:
        st.markdown('<div class="section-title">Evidence records</div><div class="section-copy">Notes and documents attached to Blueprint decisions</div>', unsafe_allow_html=True)
        if st.session_state.get("node_evidence"):
            for step_number, entries in st.session_state["node_evidence"].items():
                step = next((item for item in plan.steps if item.number == step_number), None)
                with st.expander(f"Step {step_number:02d} · {step.name if step else 'Decision'}"):
                    for entry in entries: st.markdown(f"**{entry['file']}**\n\n{entry['analysis']}")
        else:
            st.info("Your evidence records will appear here as you upload notes and documents against decision nodes.")
        with st.expander("Talk to Blueprint", expanded=False):
            for msg in st.session_state["chat"]: st.chat_message(msg["role"]).write(msg["content"])
            if message := st.chat_input("Ask about your next move"):
                st.session_state["chat"].append({"role":"user","content":message})
                st.session_state["chat"].append({"role":"assistant","content":chat(message, profile, plan, ledger, st.session_state["chat"])})
                st.rerun()
