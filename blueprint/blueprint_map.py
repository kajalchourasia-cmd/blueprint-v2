"""Calm, connected Blueprint system map."""

from __future__ import annotations

import html
from urllib.parse import quote

import streamlit as st

from blueprint.product_dashboard_v2 import _archetype, _get, _journey_actions, _journey_phases, _title


ACCENTS = ["#8db8ff", "#bca2ff", "#ff9b79", "#efd36b", "#78d3a2", "#79bceb", "#f18fa9", "#83c8d9", "#f0a76e", "#9ccc88"]
AREAS = ["foundation", "customer", "market", "solution", "revenue", "business", "launch", "financial", "distribution", "growth"]


def render_blueprint_map() -> None:
    st.markdown(
        """<style>[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stSidebar"],[data-testid="stSidebarNav"],[data-testid="collapsedControl"],#MainMenu,footer{display:none!important}html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]{margin:0!important;background:#090a09!important}.main .block-container,[data-testid="stMainBlockContainer"]{width:100%!important;max-width:none!important;padding:0!important}[data-testid="stVerticalBlock"]{gap:0!important}</style>""",
        unsafe_allow_html=True,
    )
    profile = st.session_state.get("profile")
    plan = st.session_state.get("plan")
    dialog_idea = (st.session_state.get("dialog_answers", {}) or {}).get("idea", "")
    idea = str(_get(profile, "idea", "") or st.session_state.get("idea", "") or dialog_idea or "Your Product Idea")
    title = _title(idea)
    archetype = _archetype(profile, idea)
    action_archetype = "digital_product" if archetype == "digital_product" and any(word in idea.lower() for word in ("plant", "garden", "nursery")) else "universal"
    phases = _journey_phases(archetype)
    action_rows = _journey_actions(action_archetype)
    completed = set(st.session_state.get("completed_steps", set()) or st.session_state.get("done_steps", set()))
    active_index = min(len(completed) // 3, max(0, len(phases) - 1))
    total_days = int(_get(plan, "total_estimated_days", 0) or 0)

    radios: list[str] = []
    nodes: list[str] = []
    drawers: list[str] = []
    action_count = 0
    total_cash = 0
    dynamic: list[str] = []
    for index, phase in enumerate(phases):
        order = int(phase["phase_order"])
        phase_actions = [row for row in action_rows if row["archetype"] == action_archetype and int(row["phase_order"]) == order]
        if not phase_actions:
            phase_actions = [row for row in action_rows if row["archetype"] == "universal" and int(row["phase_order"]) == order]
        phase_actions = phase_actions[:3]
        action_count += len(phase_actions)
        phase_cash = sum(int(row.get("estimated_cash", 0) or 0) for row in phase_actions)
        total_cash += phase_cash
        status = "earned" if index < active_index else "current" if index == active_index else "waiting"
        radios.append(f'<input class="phase-radio" type="radio" name="phase" id="phase-{index}"{" checked" if index == active_index else ""}>')
        dependencies = {(5, "1"): "↶ 02.1 IF COMMITMENT FAILS", (6, "2"): "↶ 01.3 IF ECONOMICS FAIL", (10, "1"): "↶ 07.2 IF RETENTION FAILS"}
        chip_parts = []
        for row in phase_actions:
            dependency = dependencies.get((order, row["action_order"]))
            relation = f'<em>{dependency}</em>' if dependency else ""
            chip_parts.append(
                f'<span class="action-chip" title="{html.escape(row["action_description"])}"><i>{order}.{row["action_order"]}</i>'
                f'<b>{html.escape(row["action_title"])}</b><small>TIME {row["estimated_days"]}d · EFFORT {row["estimated_hours"]}h · CASH ${row["estimated_cash"]}</small>{relation}</span>'
            )
        action_chips = "".join(chip_parts)
        nodes.append(
            f'<label class="phase-card order-{order} {status}" for="phase-{index}" style="--area:{AREAS[index]};--accent:{ACCENTS[index]}">'
            f'<div class="phase-top"><span>{order:02d}</span><i>{"YOU ARE HERE" if status == "current" else "EARNED" if status == "earned" else "WAITING"}</i></div>'
            f'<h2>{html.escape(phase["phase_name"])}</h2><p>{html.escape(phase["focus"])}</p>'
            f'<div class="phase-meta"><b>{len(phase_actions)} actions</b><b>${phase_cash} planned</b></div><div class="chips">{action_chips}</div></label>'
        )
        drawer_actions = "".join(
            f'<li><span>{order}.{row["action_order"]}</span><div><b>{html.escape(row["action_title"])}</b><small>{html.escape(row["deliverable"])}</small></div><em>{row["estimated_days"]}d · {row["estimated_hours"]}h · ${row["estimated_cash"]}</em></li>'
            for row in phase_actions
        )
        drawers.append(
            f'<article class="drawer drawer-{index}"><div class="drawer-copy"><small>PHASE {order:02d} · DECISION GATE</small><h3>{html.escape(phase["phase_name"])}</h3><p>{html.escape(phase["completion_signal"])}</p></div>'
            f'<ol>{drawer_actions}</ol><a href="/Your_Plan">WORK THIS PHASE →</a></article>'
        )
        dynamic.append(f'.blueprint:has(#phase-{index}:checked) .drawer-{index}{{display:grid}}.blueprint:has(#phase-{index}:checked) label[for="phase-{index}"]{{border-color:{ACCENTS[index]};box-shadow:0 0 0 1px {ACCENTS[index]}55,0 18px 55px #0008}}')

    shell = f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{html.escape(title)} Blueprint</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600" rel="stylesheet"><style>
*{{box-sizing:border-box}}html,body{{margin:0;background:#090a09;color:#f4f5f2;font-family:'Space Grotesk',Arial,sans-serif}}.blueprint{{min-height:100vh;padding:20px 28px 32px 92px;position:relative;background:radial-gradient(circle at 52% 48%,#24302755,transparent 38%),#090a09;overflow:hidden}}.blueprint:before{{content:'';position:absolute;inset:0;opacity:.18;pointer-events:none;background-image:radial-gradient(circle,#778078 1px,transparent 1.2px);background-size:24px 24px;mask-image:linear-gradient(180deg,transparent,#000 17%,#000 88%,transparent)}}
.icon-nav{{position:fixed;z-index:40;left:22px;top:50%;transform:translateY(-50%);width:48px;padding:6px;border:1px solid #292d29;border-radius:26px;background:#151715dd;backdrop-filter:blur(18px)}}.icon-nav a{{width:34px;height:34px;margin:4px 0;display:grid;place-items:center;border-radius:50%;color:#777e78;text-decoration:none;font:17px Arial;transition:.2s}}.icon-nav a:hover,.icon-nav a.active{{background:#2a2e2a;color:#fff}}.top{{height:48px;position:relative;z-index:3;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #292c29}}.brand{{color:#aeb4af;font:500 9px 'DM Mono';letter-spacing:.13em}}.top-actions{{display:flex;gap:8px}}.top-actions a{{height:31px;padding:0 13px;display:flex;align-items:center;border:1px solid #313531;border-radius:16px;background:#151715;color:#c9cec9;text-decoration:none;font:8px 'DM Mono'}}.top-actions .primary{{background:#edf0ec;color:#151715}}
.hero{{position:relative;z-index:2;padding:18px 0 15px;display:grid;grid-template-columns:1fr 430px;gap:40px;align-items:end}}.hero small{{color:#717972;font:8px 'DM Mono';letter-spacing:.12em}}.hero h1{{margin:7px 0 0;color:#f2f4f1!important;font-size:clamp(40px,4.6vw,66px);font-weight:400;line-height:.92;letter-spacing:-.074em}}.hero h1 em{{font-style:normal;color:#a1a8a2}}.hero p{{margin:0;color:#8e968f;font-size:11px;line-height:1.55}}.meta{{position:relative;z-index:2;padding:9px 0;display:flex;gap:30px;border-top:1px solid #222522;color:#697069;font:8px 'DM Mono'}}.meta b{{color:#d1d6d1;font-weight:400}}
.map-shell{{height:900px;position:relative;z-index:2;padding:30px;border:1px solid #252825;border-radius:31px;background:#111311e8;box-shadow:inset 0 1px 0 #ffffff0b,0 30px 90px #0007;overflow:hidden}}.map-shell:before{{content:'';position:absolute;inset:20px;opacity:.23;background-image:linear-gradient(#283028 1px,transparent 1px),linear-gradient(90deg,#283028 1px,transparent 1px);background-size:44px 44px;mask-image:radial-gradient(circle,#000,transparent 85%);pointer-events:none}}.connectors{{position:absolute;z-index:0;left:5%;top:5%;width:90%;height:85%;overflow:visible}}.connectors path{{fill:none;stroke:#828d84;stroke-width:1.8;stroke-linecap:round;stroke-dasharray:2 8}}.connectors path.main{{stroke:#e2e6e2;stroke-width:2.15;stroke-dasharray:1 9}}.connectors path.loop{{stroke:#8db8ff;stroke-width:2;opacity:.76;stroke-dasharray:7 9}}.map-grid{{height:100%;position:relative;z-index:1;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));grid-template-rows:repeat(3,minmax(0,1fr));grid-template-areas:'foundation customer market solution' 'financial launch business revenue' 'distribution growth . .';gap:25px 28px}}
.phase-radio{{position:absolute;opacity:0;pointer-events:none}}.phase-card{{grid-area:var(--area);min-width:0;position:relative;padding:16px 16px 14px;border:1px solid #343934;border-radius:22px;background:linear-gradient(145deg,#1c201d,#131513);color:#f0f3ef!important;cursor:pointer;box-shadow:8px 12px 30px #0005,inset 0 1px 0 #ffffff0b;transition:.24s}}.phase-card:hover{{transform:translateY(-3px);border-color:#626a63}}.phase-card:before{{content:'';display:block;width:34px;height:4px;margin:-18px 0 12px;border-radius:5px;background:var(--accent);box-shadow:0 0 18px color-mix(in srgb,var(--accent) 38%,transparent)}}.phase-card:after{{position:absolute;z-index:5;color:#dfe4df;font:18px 'DM Mono';text-shadow:0 0 12px #fff8}}.phase-card.order-1:after,.phase-card.order-2:after,.phase-card.order-3:after,.phase-card.order-9:after{{content:'→';right:-24px;top:48%}}.phase-card.order-4:after,.phase-card.order-8:after{{content:'↓';left:49%;bottom:-24px}}.phase-card.order-5:after,.phase-card.order-6:after,.phase-card.order-7:after{{content:'←';left:-24px;top:48%}}.phase-top{{display:flex;justify-content:space-between;color:#89918a;font:7px 'DM Mono'}}.phase-top i{{font-style:normal;letter-spacing:.08em}}.phase-card.current .phase-top i{{color:var(--accent)}}.phase-card.earned{{opacity:.72}}.phase-card h2{{margin:10px 0 5px;color:#f0f3ef!important;font-size:18px;font-weight:500}}.phase-card>p{{height:31px;margin:0;color:#9aa29b!important;font-size:9px;line-height:1.45;overflow:hidden}}.phase-meta{{display:flex;gap:13px;margin:10px 0;color:#aeb5af;font:7px 'DM Mono'}}.phase-meta b{{font-weight:400}}.chips{{display:grid;gap:6px}}.action-chip{{position:relative;display:grid;grid-template-columns:27px 1fr;gap:2px 8px;padding:7px 8px;border:1px solid #2c302c;border-radius:11px;background:#181b18}}.action-chip i{{grid-row:span 2;color:#838b84;font:7px 'DM Mono';font-style:normal}}.action-chip b{{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#dce1dc!important;font-size:9px;font-weight:500}}.action-chip small{{color:#858d86!important;font:6.3px 'DM Mono'}}.action-chip em{{grid-column:2;margin-top:2px;color:#8db8ff;font:5.8px 'DM Mono';font-style:normal;letter-spacing:.04em}}
.loop-label{{position:absolute;z-index:4;padding:5px 8px;border:1px solid #334238;border-radius:11px;background:#111511;color:#82b69a;font:6px 'DM Mono';letter-spacing:.08em}}.loop-one{{left:69%;top:32.3%}}.loop-two{{left:8%;top:65.3%}}.loop-three{{left:53%;top:65.3%}}.drawer-wrap{{position:relative;z-index:8;margin-top:14px}}.drawer{{min-height:125px;padding:17px 19px;display:none;grid-template-columns:240px minmax(0,1fr) auto;gap:18px;align-items:center;border:1px solid #3a3f3a;border-radius:22px;background:#181b18f2;color:#f0f3ef!important;backdrop-filter:blur(20px);box-shadow:0 22px 60px #0009}}.drawer-copy small{{color:#788078;font:7px 'DM Mono'}}.drawer-copy h3{{margin:6px 0 4px;color:#f0f3ef!important;font-size:21px;font-weight:500}}.drawer-copy p{{margin:0;color:#929a93;font-size:9px;line-height:1.4}}.drawer ol{{margin:0;padding:0;display:grid;grid-template-columns:repeat(3,1fr);gap:8px;list-style:none}}.drawer li{{min-width:0;padding:9px;display:grid;grid-template-columns:22px 1fr;gap:7px;border:1px solid #303530;border-radius:13px;background:#202320}}.drawer li>span{{color:#778078;font:6px 'DM Mono'}}.drawer li b,.drawer li small{{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.drawer li b{{color:#dce1dc!important;font-size:8px}}.drawer li small{{margin-top:3px;color:#8d958e;font-size:6.5px}}.drawer li em{{grid-column:2;color:#9da49e;font:6px 'DM Mono';font-style:normal}}.drawer>a{{height:36px;padding:0 14px;display:flex;align-items:center;border-radius:14px;background:#eef0ed;color:#171917;text-decoration:none;font:7px 'DM Mono';white-space:nowrap}}{''.join(dynamic)}
@media(max-width:1050px){{.hero{{grid-template-columns:1fr}}.hero p{{display:none}}.map-shell{{overflow:auto}}.map-grid{{min-width:850px}}.drawer{{grid-template-columns:1fr}}.drawer ol{{display:none}}}} </style></head><body>
<main class="blueprint">{''.join(radios)}<nav class="icon-nav"><a href="/" title="Home">⌂</a><a href="/Your_Plan" title="Dashboard">▦</a><a class="active" href="/Your_Plan?view=blueprint" title="Full Blueprint">⌘</a><a href="/Case_Study" title="Case study">¶</a></nav><header class="top"><div class="brand">BLUEPRINT / CONNECTED DECISION PATH</div><div class="top-actions"><a href="/?logout=1">SIGN OUT</a><a href="/Your_Plan">DASHBOARD</a><a class="primary download-link" href="#">DOWNLOAD BLUEPRINT</a></div></header>
<section class="hero"><div><small>IDEA → EVIDENCE → REPEATABLE SYSTEM</small><h1>{html.escape(title)} <em>Blueprint</em></h1></div><p>Follow the bright path in sequence. Dotted loops show where weak evidence sends the work backward. Select any phase to inspect its decision gate and exact investment.</p></section><div class="meta"><span>MODEL <b>{html.escape(archetype.replace('_',' ').title())}</b></span><span>PHASES <b>{len(phases)}</b></span><span>ACTIONS <b>{action_count}</b></span><span>PLANNED CASH <b>${total_cash}</b></span><span>TIMELINE <b>{total_days or 'TBD'} days</b></span></div>
<section class="map-shell"><svg class="connectors" viewBox="0 0 1200 760" preserveAspectRatio="none" aria-hidden="true"><defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7" fill="none" stroke="#cbd1cc"/></marker></defs><path class="main" marker-end="url(#arrow)" d="M125 120 H1025 V380 H125 V650 H425"/><path class="loop" marker-end="url(#arrow)" d="M1025 425 C930 570 520 550 425 175"/><path class="loop" marker-end="url(#arrow)" d="M725 425 C570 590 170 525 125 175"/><path class="loop" marker-end="url(#arrow)" d="M425 690 C520 615 525 490 425 425"/></svg><span class="loop-label loop-one">05.1 → 02.1 IF COMMITMENT FAILS</span><span class="loop-label loop-two">06.2 → 01.3 IF ECONOMICS FAIL</span><span class="loop-label loop-three">10.1 → 07.2 IF RETENTION FAILS</span><div class="map-grid">{''.join(nodes)}</div></section><div class="drawer-wrap">{''.join(drawers)}</div></main></body></html>'''
    downloadable = shell.replace('class="primary download-link" href="#"', 'class="primary" href="#"')
    data_uri = "data:text/html;charset=utf-8," + quote(downloadable)
    shell = shell.replace('class="primary download-link" href="#"', f'class="primary download-link" href="{data_uri}" download="{html.escape(title)}-blueprint.html"')
    st.html("".join(line.strip() for line in shell.splitlines()))
