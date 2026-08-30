"""Product dashboard that maps Blueprint state into the approved visual system."""

from __future__ import annotations

import html
import re
from typing import Any

import streamlit as st


def _value(source: Any, key: str, default: Any = None) -> Any:
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def _project_title(idea: str) -> str:
    clean = re.sub(r"\s+", " ", idea.strip()).rstrip(".!?")
    clean = re.sub(
        r"^(i\s+(?:want|would like|plan|hope)\s+to|my idea is to|we want to)\s+",
        "",
        clean,
        flags=re.I,
    )
    clean = re.sub(r"^(build|create|launch|start|open)\s+(?:an?\s+)?", "", clean, flags=re.I)
    words = clean.split()
    return " ".join(words[:6]).title() if words else "Plant Analyzing App"


def _step_dict(step: Any, index: int) -> dict[str, Any]:
    return {
        "number": int(_value(step, "number", index + 1)),
        "name": str(_value(step, "name", f"Milestone {index + 1}")),
        "days": int(_value(step, "estimated_time_days", 4 + index)),
        "hours": int(_value(step, "estimated_hours", 3 + index)),
        "type": str(_value(step, "step_type", "validate")),
    }


def render_product_dashboard() -> None:
    st.set_page_config(
        page_title="Blueprint Alpha",
        page_icon="⌁",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(
        """
        <style>
        [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stSidebar"],
        [data-testid="stSidebarNav"], [data-testid="collapsedControl"], #MainMenu, footer {
            display:none !important;
        }
        html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
            margin:0 !important; background:#050505 !important;
        }
        .main .block-container, [data-testid="stMainBlockContainer"] {
            width:100% !important; max-width:none !important; padding:0 !important;
        }
        [data-testid="stVerticalBlock"] { gap:0 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    profile = st.session_state.get("profile")
    plan = st.session_state.get("plan")
    reality = st.session_state.get("reality")
    ledger = st.session_state.get("ledger")

    idea = str(_value(profile, "idea", st.session_state.get("idea", "Plant Analyzing App")))
    title = _project_title(idea)
    raw_steps = list(_value(plan, "steps", []) or [])
    if not raw_steps:
        raw_steps = [
            {"number": 1, "name": "Define the customer problem", "estimated_time_days": 3, "estimated_hours": 4, "step_type": "research"},
            {"number": 2, "name": "Interview 10 target users", "estimated_time_days": 7, "estimated_hours": 8, "step_type": "interview"},
            {"number": 3, "name": "Map competing alternatives", "estimated_time_days": 4, "estimated_hours": 5, "step_type": "research"},
            {"number": 4, "name": "Build the smallest test", "estimated_time_days": 6, "estimated_hours": 9, "step_type": "build"},
            {"number": 5, "name": "Run a willingness-to-pay test", "estimated_time_days": 5, "estimated_hours": 6, "step_type": "validate"},
            {"number": 6, "name": "Choose a revenue model", "estimated_time_days": 3, "estimated_hours": 4, "step_type": "sell"},
            {"number": 7, "name": "Launch to the first cohort", "estimated_time_days": 10, "estimated_hours": 12, "step_type": "launch"},
        ]
    steps = [_step_dict(step, index) for index, step in enumerate(raw_steps)]

    completed = set(st.session_state.get("completed_steps", set()))
    if not completed:
        completed = set(st.session_state.get("done_steps", set()))
    completion = round((len(completed) / max(len(steps), 1)) * 100)
    delusions = list(_value(reality, "specific_delusions", []) or [])
    advantages = list(_value(reality, "unfair_advantages", []) or [])
    gaps = list(_value(reality, "critical_gaps", []) or [])
    assumptions = len(delusions) or 8
    positive_signals = len(advantages) or 3
    risks = len(gaps) or 5
    fit_score = int(_value(reality, "fit_score", 6) or 6)
    clarity = min(94, max(18, completion + fit_score * 7))
    money = int(_value(profile, "money_available", _value(ledger, "cash_dollars", 2500)) or 0)
    hours_per_week = int(_value(profile, "hours_per_week", 8) or 0)
    total_days = int(_value(plan, "total_estimated_days", sum(step["days"] for step in steps)) or 0)
    launch_readiness = min(96, max(12, round(completion * 0.7 + fit_score * 3)))

    phase_labels = [
        ("Foundation", "⌂"),
        ("Customer research", "1"),
        ("Market research", "2"),
        ("Solution test", "3"),
        ("Revenue model", "4"),
        ("Business model", "5"),
        ("Launch", "6"),
    ]
    nav_items = []
    for index, (label, icon) in enumerate(phase_labels):
        checked = " checked" if index == 0 else ""
        nav_items.append(
            f'<input class="nav-radio" type="radio" name="phase" id="phase-{index}"{checked}>'
            f'<label class="phase-item" for="phase-{index}"><span class="phase-icon">{icon}</span>'
            f'<span>{html.escape(label)}</span><span class="phase-arrow">›</span></label>'
        )

    step_rows = []
    for index, step in enumerate(steps[:9]):
        is_done = step["number"] in completed or str(step["number"]) in completed
        state = "done" if is_done else ("active" if index == len(completed) else "")
        state_copy = "Complete" if is_done else ("Next step" if state == "active" else f'{step["days"]} days')
        step_rows.append(
            f'<div class="plan-step {state}"><span class="step-node">{"✓" if is_done else step["number"]}</span>'
            f'<div><b>{html.escape(step["name"])}</b><small>{html.escape(step["type"].replace("_", " ").title())} · {step["hours"]} hours</small></div>'
            f'<span class="step-state">{state_copy}</span></div>'
        )

    signal_cards = [
        ("Customer pain", "High", "pain", "Strong repeated need", "⌁"),
        ("Competition", "Moderate", "competition", "Alternatives exist", "◎"),
        ("Differentiation", "62", "difference", "Signal strength", "◇"),
        ("Pricing", "3 tests", "pricing", "Evidence pending", "₹"),
        ("Blueprint strength", f"{clarity}", "strength", "Out of 100", "◉"),
        ("Launch readiness", f"{launch_readiness}%", "launch", "Current estimate", "↗"),
    ]
    signal_html = []
    for name, value, style, note, icon in signal_cards:
        signal_html.append(
            f'<article class="signal-card {style}"><div class="signal-top"><span>{icon}</span><span>{html.escape(name)}</span></div>'
            f'<div class="signal-value">{html.escape(str(value))}</div><div class="signal-note">{html.escape(note)}</div>'
            f'<div class="signal-visual"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div></article>'
        )

    dashboard_html = r"""
<style>
*{box-sizing:border-box}html,body{margin:0;background:#050505;color:#181818;font-family:-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif}.shell{width:calc(100vw - 12px);min-height:calc(100vh - 12px);margin:6px;padding:24px 26px 30px;background:#e9e9e9;border-radius:30px;overflow:hidden}.topbar{height:54px;display:flex;align-items:center;justify-content:space-between}.brand{font-size:18px;font-weight:760;letter-spacing:-.055em}.top-actions{display:flex;align-items:center;gap:17px}.project-select{appearance:none;border:0;background:transparent;color:#555;padding:8px 24px 8px 4px;font-size:12px;background-image:linear-gradient(45deg,transparent 50%,#777 50%),linear-gradient(135deg,#777 50%,transparent 50%);background-position:calc(100% - 10px) 50%,calc(100% - 6px) 50%;background-size:4px 4px,4px 4px;background-repeat:no-repeat}.profile-icon{width:30px;height:30px;position:relative;border:0;background:transparent}.profile-icon:before{content:"";position:absolute;left:10px;top:3px;width:8px;height:8px;border:1.7px solid #222;border-radius:50%}.profile-icon:after{content:"";position:absolute;left:5px;bottom:2px;width:18px;height:11px;border:1.7px solid #222;border-bottom:0;border-radius:12px 12px 0 0}.layout{display:grid;grid-template-columns:232px minmax(0,1fr);gap:32px}.rail-title{display:flex;align-items:baseline;gap:10px;height:68px}.rail-title strong,.rail-title span{font-size:29px;font-weight:400;letter-spacing:-.065em}.rail-title span{color:#a4a4a4}.rail-title em{font-size:12px;font-style:normal;color:#aaa;margin-right:-5px}.overview{height:54px;padding:0 15px;display:grid;grid-template-columns:27px 1fr auto;align-items:center;gap:9px;background:#fff;border-radius:27px;margin-bottom:12px;font-size:13px}.dashboard-icon{width:21px;height:21px;padding:4px;display:grid;grid-template-columns:1fr 1fr;gap:2px;border:1px solid #aaa;border-radius:6px}.dashboard-icon i{display:block;background:#aaa;border-radius:1px}.overview .arrow,.phase-arrow{font-size:19px;color:#8c8c8c}.phase-list{border-top:1px solid rgba(0,0,0,.07)}.nav-radio{position:absolute;opacity:0;pointer-events:none}.phase-item{height:58px;padding:0 14px;display:grid;grid-template-columns:27px 1fr auto;align-items:center;gap:9px;border-bottom:1px solid rgba(0,0,0,.07);border-radius:25px;cursor:pointer;font-size:13px;transition:.2s ease}.phase-icon{width:21px;height:21px;display:grid;place-items:center;color:#777;font-size:11px;border:1px solid #aaa;border-radius:50%}.phase-arrow{opacity:0}.phase-item:hover,.nav-radio:focus+.phase-item{background:rgba(255,255,255,.54)}.nav-radio:checked+.phase-item{margin:5px 0;background:#fff;border-bottom-color:transparent}.nav-radio:checked+.phase-item .phase-arrow{opacity:1}.rail-note{margin-top:20px;padding:18px;border-radius:23px;background:rgba(255,255,255,.58)}.rail-note b{display:block;font-size:12px}.rail-note p{margin:7px 0 0;color:#8d8d8d;font-size:10px;line-height:1.45}.workspace{min-width:0}.hero{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:22px}.idea-title{margin:7px 0 25px;font-size:49px;font-weight:400;letter-spacing:-.075em;line-height:.95}.kpis{display:grid;grid-template-columns:repeat(4,minmax(100px,1fr));gap:12px;margin-bottom:24px}.kpi{min-height:61px;display:flex;align-items:center;justify-content:center;gap:8px}.kpi b{font:400 39px/1 "Courier New",monospace;letter-spacing:-.11em}.kpi span{align-self:flex-start;margin-top:5px;padding:5px 8px;border-radius:11px;background:rgba(255,255,255,.55);color:#777;font-size:9px;white-space:nowrap}.kpi:first-child span{background:#dfff00;color:#313600;font-weight:700}.clarity-track{height:75px;position:relative;border-radius:38px;background:rgba(255,255,255,.27);overflow:hidden}.clarity-track:before{content:"";position:absolute;left:5%;right:5%;top:50%;height:1px;background:#d1d1d1}.track-dots{position:absolute;inset:0;background-image:radial-gradient(circle,#b2b2b2 1.2px,transparent 1.4px);background-size:31px 13px;opacity:.45}.clarity-marker{position:absolute;z-index:1;left:calc(__CLARITY__% - 105px);top:10px;width:210px;height:55px;padding:11px 17px;border-radius:28px;background:#fff;box-shadow:0 8px 22px rgba(0,0,0,.03)}.clarity-marker b{display:block;font-size:12px}.clarity-marker small{display:block;margin-top:5px;color:#999;font-size:9px}.clarity-labels{position:absolute;left:19px;right:19px;bottom:5px;display:flex;justify-content:space-between;color:#aaa;font-size:8px}.resource-card{min-height:225px;padding:20px;border-radius:29px;background:rgba(255,255,255,.72)}.resource-card h3{margin:0 0 20px;font-size:14px;font-weight:500}.resource-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.resource{min-height:74px;padding:12px;border-radius:17px;background:#f1f1f1}.resource small{display:block;color:#929292;font-size:9px}.resource b{display:block;margin-top:8px;font:400 18px "Courier New",monospace}.strength-bar{height:5px;margin-top:9px;background:#d7d7d7;border-radius:4px;overflow:hidden}.strength-bar i{display:block;width:__READINESS__%;height:100%;background:#dfff00}.main-grid{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:22px;margin-top:22px}.plan-card{min-height:455px;padding:25px 27px;border-radius:31px;background:linear-gradient(145deg,#fbfbfb 0%,#f7f7f7 72%,#edf3e1 100%)}.plan-head{display:flex;justify-content:space-between;align-items:flex-start;padding-bottom:18px;border-bottom:1px solid #dedede}.plan-head h2{margin:0;font-size:25px;font-weight:400;letter-spacing:-.05em}.plan-head p{margin:5px 0 0;color:#999;font-size:10px}.plan-pill{padding:8px 12px;border-radius:16px;background:#e9e9e9;font-size:9px}.plan-flow{padding-top:8px}.plan-step{min-height:47px;display:grid;grid-template-columns:32px 1fr auto;gap:12px;align-items:center;position:relative}.plan-step:not(:last-child):before{content:"";position:absolute;left:15px;top:37px;width:1px;height:21px;background:#ccc}.step-node{width:31px;height:31px;display:grid;place-items:center;border:1px solid #aaa;border-radius:50%;font:11px "Courier New",monospace;background:#f8f8f8}.plan-step b{display:block;font-size:12px;font-weight:500}.plan-step small{display:block;margin-top:3px;color:#999;font-size:9px}.step-state{color:#999;font-size:9px}.plan-step.active .step-node{background:#dfff00;border-color:#dfff00;box-shadow:0 0 0 5px rgba(223,255,0,.18)}.plan-step.active b{font-weight:700}.plan-step.done .step-node{background:#202020;color:#fff;border-color:#202020}.calendar-card{min-height:455px;padding:23px;border-radius:31px;background:rgba(255,255,255,.7)}.calendar-title{display:flex;justify-content:space-between;align-items:center}.calendar-title h3{margin:0;font-size:15px;font-weight:500}.calendar-title span{color:#999;font-size:10px}.calendar-days,.calendar-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:7px;text-align:center}.calendar-days{margin:24px 0 12px;color:#aaa;font-size:8px}.calendar-grid span{height:28px;display:grid;place-items:center;border-radius:50%;font-size:9px}.calendar-grid .muted{color:#bbb}.calendar-grid .active{background:#dfff00;font-weight:700}.calendar-grid .event{border:1px solid #222}.up-next{margin-top:28px;padding-top:20px;border-top:1px solid #ddd}.up-next small{color:#999;font-size:9px}.up-next h4{margin:8px 0 4px;font-size:13px}.up-next p{margin:0;color:#777;font-size:10px;line-height:1.45}.week-load{margin-top:20px}.week-load div{height:8px;margin-top:8px;border-radius:5px;background:linear-gradient(90deg,#dfff00 0 64%,#ddd 64%)}.signals-head{display:flex;justify-content:space-between;align-items:end;margin:29px 0 15px}.signals-head h2{margin:0;font-size:27px;font-weight:400;letter-spacing:-.055em}.signals-head p{margin:5px 0 0;color:#999;font-size:10px}.signals-head button{border:0;padding:10px 16px;border-radius:19px;background:#fff;font-size:10px}.signals{display:grid;grid-template-columns:repeat(6,minmax(130px,1fr));gap:12px}.signal-card{min-height:184px;padding:17px;border-radius:24px;background:rgba(255,255,255,.72);position:relative;overflow:hidden}.signal-top{display:flex;gap:8px;color:#777;font-size:9px}.signal-value{margin-top:36px;font:400 31px "Courier New",monospace;letter-spacing:-.08em}.signal-note{margin-top:3px;color:#aaa;font-size:9px}.signal-visual{position:absolute;left:16px;right:16px;bottom:17px;height:34px;display:flex;align-items:end;gap:5px}.signal-visual i{flex:1;height:20%;border-radius:3px;background:#bcbcbc}.signal-visual i:nth-child(2){height:40%}.signal-visual i:nth-child(3){height:58%}.signal-visual i:nth-child(4){height:34%}.signal-visual i:nth-child(5){height:70%}.signal-visual i:nth-child(6){height:82%}.signal-visual i:nth-child(7){height:66%}.signal-visual i:nth-child(8){height:92%}.pain .signal-visual i,.strength .signal-visual i{background:#7fc96e}.competition .signal-visual{align-items:center;border-top:1px solid #ccc;border-bottom:1px solid #ccc}.competition .signal-visual i{height:4px;background:#777}.difference .signal-visual i{border-radius:50%;height:7px;background:#777}.difference .signal-visual i:nth-child(-n+4){background:#dfff00}.pricing .signal-visual{border-bottom:1px solid #aaa}.pricing .signal-visual i{height:1px;background:transparent}.pricing .signal-visual:after{content:"";position:absolute;left:0;right:0;bottom:3px;height:20px;border:1.5px solid #777;border-color:#777 transparent transparent #777;border-radius:70% 0 0 0;transform:skewX(-20deg)}.launch .signal-visual{height:5px;background:#ddd;border-radius:5px;top:auto;bottom:24px}.launch .signal-visual:after{content:"";width:__READINESS__%;height:100%;background:#dfff00;border-radius:5px}.launch .signal-visual i{display:none}@media(max-width:1200px){.layout{grid-template-columns:205px 1fr;gap:22px}.hero,.main-grid{grid-template-columns:1fr}.resource-card{display:none}.calendar-card{min-height:auto}.signals{grid-template-columns:repeat(3,1fr)}}@media(max-width:760px){.shell{width:100%;margin:0;border-radius:0;padding:16px}.layout{display:block}.rail{display:none}.idea-title{font-size:37px}.kpis{grid-template-columns:1fr 1fr}.main-grid{display:block}.calendar-card{margin-top:14px}.signals{grid-template-columns:1fr 1fr}.top-actions select{display:none}}
</style>
<main class="shell"><header class="topbar"><div class="brand">blueprint alpha</div><div class="top-actions"><select class="project-select" aria-label="Select blueprint"><option>__TITLE__</option><option>New blueprint</option></select><button class="profile-icon" aria-label="Profile"></button></div></header><div class="layout"><aside class="rail"><div class="rail-title"><strong>Plan</strong><em>&amp;</em><span>Progress</span></div><div class="overview"><span class="dashboard-icon"><i></i><i></i><i></i><i></i></span><span>Overview</span><span class="arrow">›</span></div><div class="phase-list">__NAV__</div><div class="rail-note"><b>What this plan is doing</b><p>Each phase converts one important assumption into evidence before you invest more money or time.</p></div></aside><section class="workspace"><div class="hero"><div><h1 class="idea-title">__TITLE__</h1><div class="kpis"><div class="kpi"><b>__COMPLETION__%</b><span>Completed</span></div><div class="kpi"><b>__ASSUMPTIONS__</b><span>Assumptions</span></div><div class="kpi"><b>__POSITIVE__</b><span>+VE signals</span></div><div class="kpi"><b>__RISKS__</b><span>Risks</span></div></div><div class="clarity-track"><div class="track-dots"></div><div class="clarity-marker"><b>↗ Idea becoming clearer</b><small>Strong knowledge base · validation in progress</small></div><div class="clarity-labels"><span>Uncertain</span><span>Evidence-backed</span></div></div></div><aside class="resource-card"><h3>Your starting position</h3><div class="resource-grid"><div class="resource"><small>Money in hand</small><b>$__MONEY__</b></div><div class="resource"><small>Weekly time</small><b>__HOURS__ hrs</b></div><div class="resource"><small>Plan timeline</small><b>__DAYS__ days</b></div><div class="resource"><small>Launch readiness</small><b>__READINESS__%</b><div class="strength-bar"><i></i></div></div></div></aside></div><div class="main-grid"><article class="plan-card"><div class="plan-head"><div><h2>Your evidence path</h2><p>The shortest sequence from idea to a defensible launch decision.</p></div><span class="plan-pill">__STEP_COUNT__ milestones</span></div><div class="plan-flow">__STEPS__</div></article><aside class="calendar-card"><div class="calendar-title"><h3>Plan calendar</h3><span>August 2026</span></div><div class="calendar-days"><span>M</span><span>T</span><span>W</span><span>T</span><span>F</span><span>S</span><span>S</span></div><div class="calendar-grid"><span class="muted">27</span><span class="muted">28</span><span class="muted">29</span><span class="muted">30</span><span class="muted">31</span><span>1</span><span>2</span><span>3</span><span>4</span><span>5</span><span>6</span><span>7</span><span>8</span><span>9</span><span>10</span><span>11</span><span>12</span><span>13</span><span>14</span><span>15</span><span class="active">16</span><span class="event">17</span><span>18</span><span>19</span><span>20</span><span>21</span><span>22</span><span>23</span><span>24</span><span>25</span><span>26</span><span>27</span><span>28</span><span>29</span><span>30</span><span>31</span><span class="muted">1</span><span class="muted">2</span><span class="muted">3</span><span class="muted">4</span><span class="muted">5</span><span class="muted">6</span></div><div class="up-next"><small>NEXT COMMITMENT</small><h4>Complete your first evidence step</h4><p>Protect one focused block this week. Do not start building before the signal is recorded.</p></div><div class="week-load"><small>This week's capacity</small><div></div></div></aside></div><div class="signals-head"><div><h2>Key signals</h2><p>The evidence that changes whether this idea deserves more investment.</p></div><button>See all evidence</button></div><section class="signals">__SIGNALS__</section></section></div></main>
"""
    replacements = {
        "__TITLE__": html.escape(title),
        "__NAV__": "".join(nav_items),
        "__COMPLETION__": str(completion),
        "__ASSUMPTIONS__": str(assumptions),
        "__POSITIVE__": str(positive_signals),
        "__RISKS__": str(risks),
        "__CLARITY__": str(clarity),
        "__MONEY__": f"{money:,}",
        "__HOURS__": str(hours_per_week),
        "__DAYS__": str(total_days),
        "__READINESS__": str(launch_readiness),
        "__STEP_COUNT__": str(len(steps)),
        "__STEPS__": "".join(step_rows),
        "__SIGNALS__": "".join(signal_html),
    }
    for token, value in replacements.items():
        dashboard_html = dashboard_html.replace(token, value)

    st.html("".join(line.strip() for line in dashboard_html.splitlines()))
