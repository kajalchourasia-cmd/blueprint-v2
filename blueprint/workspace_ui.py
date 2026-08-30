"""Codex-style, section-specific workspace for the live Blueprint run."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from blueprint.backend import BackendError, ask_research, hydrate_current_run, make_idempotency_key, preview_research_rerun, resolve_founder_checkpoint, resolve_research_rerun


STAGES = [
    ("Stage 1 · Discover", [
        ("foundation", "Foundation"), ("customer_demand", "Customer Research"),
        ("competitor_intelligence", "Competitor Research"), ("market_economics", "Market Research"),
        ("evidence_audit", "Evidence Audit"), ("research_verdict", "Research Verdict"),
    ]),
    ("Stage 2 · Prove & design", [
        ("assumptions_risks", "Assumptions & Risks"), ("offer_pricing", "Offer & Pricing"),
        ("validation_proof", "Validation Plan"), ("operating_model", "Operating Model"),
        ("financial_readiness", "Financial Readiness"), ("execution_readiness", "Gate 2 Readiness"),
    ]),
    ("Stage 3 · Action Blueprint", [
        ("launch_distribution", "MVP & Distribution"), ("growth_optimization", "Growth Prerequisites"),
        ("action_blueprint", "Action Blueprint"),
    ]),
]

LABELS = {key: label for _, items in STAGES for key, label in items}
RESEARCH_RERUNS = {"customer_demand", "competitor_intelligence", "market_economics"}
DONE = {"COMPLETED", "REUSED", "NOT_APPLICABLE"}
FAILED = {"PARTIAL", "SAFE_FAILED", "HUMAN_REVIEW", "NEEDS_INPUT"}


def _items(value: Any) -> list:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _task_map(bundle: dict) -> dict[str, dict]:
    context = _dict(bundle.get("research_context"))
    return {str(task.get("module_key")): task for task in _items(context.get("orchestration_tasks")) if isinstance(task, dict)}


def _stage_number(section_key: str) -> int:
    for number, (_, items) in enumerate(STAGES, 1):
        if any(key == section_key for key, _ in items):
            return number
    return 1


def _section_state(task: dict | None, stage_number: int, has_gate_1: bool, has_gate_2: bool) -> tuple[str, str]:
    if task:
        status = str(task.get("status") or "PLANNED").upper()
        if status in DONE:
            return "done", "Completed" if status != "NOT_APPLICABLE" else "Not applicable"
        if status == "RUNNING":
            return "running", "Running"
        if status == "READY":
            return "ready", "Queued"
        if status in FAILED:
            return "error", status.replace("_", " ").title()
        return "locked", status.replace("_", " ").title()
    if stage_number == 2 and not has_gate_1:
        return "locked", "Unlocks after Gate 1"
    if stage_number == 3 and not has_gate_2:
        return "locked", "Unlocks after Gate 2"
    return "idle", "Not started"


def _extract_output(task: dict | None, artifact: dict, section_key: str) -> dict:
    if task and isinstance(task.get("output"), dict):
        return task["output"]
    for section in _items(artifact.get("sections")):
        if isinstance(section, dict) and section.get("section_key") == section_key:
            content = section.get("content") or section.get("summary") or section
            return content if isinstance(content, dict) else {"executive_finding": str(content)}
    if section_key == "action_blueprint" and artifact.get("module_key") == "action_blueprint":
        return artifact
    return {}


def _flatten_sources(output: dict, context: dict) -> list[dict]:
    seen, sources = set(), []
    for item in _items(output.get("evidence_cards")) + _items(context.get("accepted_evidence")):
        if not isinstance(item, dict):
            continue
        url = str(item.get("source_url") or item.get("url") or "")
        key = str(item.get("evidence_id") or item.get("id") or url)
        if key and key not in seen:
            seen.add(key); sources.append(item)
    return sources


def _status_icon(kind: str) -> str:
    return {"done": "✓", "running": "◌", "ready": "·", "error": "!", "locked": "⌁", "idle": "○"}.get(kind, "○")


def _render_css() -> None:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600&display=swap');
    :root{--ink:#1b1e1c;--muted:#777d78;--line:#d8dbd7;--paper:#f4f5f2;--panel:#fbfbf9;--green:#d9f45a;--orange:#f0a06b}
    [data-testid="stAppViewContainer"],[data-testid="stHeader"]{background:#eceeeb} [data-testid="stHeader"],#MainMenu,footer,[data-testid="stSidebarNav"]{display:none!important}
    main .block-container{max-width:1800px;padding:18px 24px 60px}.bp-brand{font:500 11px 'DM Mono';letter-spacing:.12em;text-transform:uppercase}.bp-title{font:500 34px/1 'Space Grotesk';letter-spacing:-.055em;margin:8px 0 2px}.bp-sub{font:11px 'DM Mono';color:var(--muted)}
    .kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:18px 0}.kpi{background:var(--panel);border:1px solid var(--line);border-radius:17px;padding:14px 16px}.kpi b{display:block;font:500 24px 'Space Grotesk';letter-spacing:-.04em}.kpi span{font:9px 'DM Mono';color:var(--muted);text-transform:uppercase;letter-spacing:.07em}
    .stage-label{margin:18px 0 7px;font:500 9px 'DM Mono';letter-spacing:.08em;text-transform:uppercase;color:#777}.thread-card{padding:10px 11px;border-radius:12px;background:#f8f8f5;border:1px solid #e0e2df;margin:6px 0}.thread-card.active{background:#222724;color:white;border-color:#222724}.thread-card .name{font:500 11px 'Space Grotesk'}.thread-card small{display:block;margin-top:3px;font:8px 'DM Mono';opacity:.68}.state-dot{float:right;font:500 12px 'DM Mono'}
    .workspace-pane{background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:18px;min-height:680px}.section-kicker{font:9px 'DM Mono';color:var(--muted);text-transform:uppercase}.section-title{font:500 30px 'Space Grotesk';letter-spacing:-.055em;margin:6px 0 3px}.finding{font:15px/1.55 'Space Grotesk';color:#333;margin:15px 0 18px}.detail-block{border-top:1px solid var(--line);padding-top:13px;margin-top:13px}.detail-block h4{font:500 10px 'DM Mono';text-transform:uppercase;color:#747a75;letter-spacing:.06em}.detail-block li{font:13px/1.5 'Space Grotesk';margin:5px 0}.empty-state{margin-top:70px;text-align:center;color:#747a75}.empty-state b{display:block;font:500 22px 'Space Grotesk';color:#2a2e2b}.right-card{border:1px solid var(--line);border-radius:15px;padding:13px;margin-bottom:10px;background:#fff}.right-card h4{font:500 9px 'DM Mono';text-transform:uppercase;color:#777;margin:0 0 9px}.right-card p,.right-card li{font:11px/1.45 'Space Grotesk';color:#4f5550}.source-link{display:block;padding:7px 0;border-top:1px solid #eceeeb;font:10px 'Space Grotesk'}.chat-divider{margin:22px 0 10px;border-top:1px solid var(--line)}
    .stButton button{border-radius:11px!important;font:500 10px 'DM Mono'!important}.stChatMessage{background:#f5f6f3!important;border-radius:13px!important;padding:9px!important}.stChatInputContainer{border-radius:14px!important}
    @media(max-width:1050px){.kpi-grid{grid-template-columns:repeat(2,1fr)}.workspace-pane{min-height:auto}}
    </style>
    """, unsafe_allow_html=True)


def _gate_dialog(checkpoint: dict, latest_verdict: dict) -> None:
    @st.dialog("Your decision unlocks the next stage", width="large")
    def gate() -> None:
        verdict = str(latest_verdict.get("verdict") or checkpoint.get("title") or "Review required").replace("_", " ").title()
        score = latest_verdict.get("score")
        st.markdown(f"### {verdict}" + (f" · {float(score):.0f}/100" if isinstance(score, (int, float)) else ""))
        st.write(latest_verdict.get("explanation") or checkpoint.get("message") or "Review the completed stage before Blueprint continues.")
        allowed = checkpoint.get("allowed_decisions") or []
        labels = {"PROCEED":"Continue to the next stage","CONTINUE_ANYWAY":"Continue with the stated limitations","TARGETED_VALIDATION":"Run focused validation first","RUN_MISSING_RESEARCH":"Complete missing research","PAUSE_OR_REVISE":"Pause and review/tweak the idea","CANCEL":"Stop this Blueprint"}
        decision = st.radio("What should Blueprint do?", allowed, format_func=lambda value: labels.get(value, value.replace("_", " ").title()))
        note = st.text_area("Optional founder note", placeholder="Add context that the next stage should respect.")
        if st.button("Apply decision", type="primary", use_container_width=True):
            try:
                resolve_founder_checkpoint(str(checkpoint["checkpoint_id"]), int(checkpoint["state_version"]), str(decision), {"founder_note": note} if note else {})
                st.session_state.pop("backend_bundle", None); st.session_state["backend_last_refresh_at"] = 0
                st.rerun()
            except BackendError as exc:
                st.error(str(exc))
    gate()


def _render_center(section_key: str, task: dict | None, output: dict, state: tuple[str, str], context: dict) -> None:
    stage = _stage_number(section_key)
    label = LABELS.get(section_key, section_key.replace("_", " ").title())
    st.markdown(f'<div class="section-kicker">Stage {stage} · {html.escape(state[1])}</div><div class="section-title">{html.escape(label)}</div>', unsafe_allow_html=True)
    if not output:
        message = "This section is waiting for the previous gate." if state[0] == "locked" else "Blueprint has not produced this section yet."
        if state[0] == "running": message = "The specialist is researching this section now. Refresh to see accepted results."
        if state[0] == "error": message = "The attempted result was preserved safely, but this section needs input, retry, or review."
        st.markdown(f'<div class="empty-state"><b>{html.escape(state[1])}</b><p>{html.escape(message)}</p></div>', unsafe_allow_html=True)
    else:
        finding = output.get("executive_finding") or output.get("summary") or output.get("explanation") or "Structured output is available below."
        st.markdown(f'<div class="finding">{html.escape(str(finding))}</div>', unsafe_allow_html=True)
        groups = [
            ("Evidence-supported signals", output.get("observed_signals")), ("Recommendations", output.get("recommendations")),
            ("Scenarios", output.get("scenarios")), ("Milestones", output.get("milestones")),
            ("Assumptions", output.get("assumptions")), ("Risks", output.get("risks")),
            ("Contradictions", output.get("contradictions")), ("Unknowns", output.get("unknowns")),
            ("Limitations", output.get("limitations")),
        ]
        for heading, values in groups:
            values = _items(values)
            if not values: continue
            st.markdown(f"#### {heading}")
            for value in values[:20]:
                if isinstance(value, dict):
                    text = value.get("claim") or value.get("title") or value.get("name") or value.get("risk") or value.get("why") or str(value)
                else: text = str(value)
                st.markdown(f"- {text}")

    st.markdown('<div class="chat-divider"></div>', unsafe_allow_html=True)
    st.caption(f"Ask about {label}. This conversation is isolated to this section and its accepted project evidence.")
    chats = st.session_state.setdefault("bp_section_chats", {})
    threads = st.session_state.setdefault("bp_section_threads", {})
    history = chats.setdefault(section_key, [])
    for message in history[-8:]:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message.get("citations"): st.caption("Evidence: " + ", ".join(message["citations"]))
    if question := st.chat_input(f"Ask about {label.lower()}…", key=f"chat_{section_key}"):
        history.append({"role":"user","content":question})
        try:
            result = ask_research(question, project_id=str(st.session_state["backend_project_id"]), run_id=str(st.session_state["backend_run_id"]), thread_id=threads.get(section_key), section_key=section_key)
            if result.get("thread_id"): threads[section_key] = result["thread_id"]
            history.append({"role":"assistant","content":result.get("answer") or "UNKNOWN — this section does not contain enough accepted evidence.","citations":_items(result.get("citations"))})
        except BackendError as exc:
            history.append({"role":"assistant","content":str(exc),"citations":[]})
        st.rerun()


def _render_right(section_key: str, task: dict | None, output: dict, sources: list[dict]) -> None:
    actions = _items(output.get("contextual_actions"))
    st.markdown('<div class="right-card"><h4>Founder actionables</h4>', unsafe_allow_html=True)
    if actions:
        for action in actions[:5]:
            if isinstance(action, dict): st.markdown(f"- **{action.get('title','Next action')}** — {action.get('why','')}")
            else: st.markdown(f"- {action}")
    else: st.caption("No actionable is shown until this section has a valid output.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="right-card"><h4>Sources</h4>', unsafe_allow_html=True)
    scoped_ids = {str(x) for signal in _items(output.get("observed_signals")) if isinstance(signal, dict) for x in _items(signal.get("evidence_ids"))}
    scoped = [s for s in sources if not scoped_ids or str(s.get("id") or s.get("evidence_id")) in scoped_ids]
    if scoped:
        for source in scoped[:10]:
            title = source.get("source_title") or source.get("title") or source.get("source_domain") or "Evidence source"
            url = source.get("source_url") or source.get("url")
            st.markdown(f"[{title}]({url})" if url else str(title))
    else: st.caption("No accepted source is attached to this section yet.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="right-card"><h4>Background process</h4>', unsafe_allow_html=True)
    if task:
        st.write(f"Status: **{str(task.get('status','PLANNED')).replace('_',' ').title()}**")
        st.caption(task.get("route_reason") or "Waiting for the dynamic Supervisor.")
    else: st.caption("This worker has not been planned yet.")
    st.markdown('</div>', unsafe_allow_html=True)

    if section_key in RESEARCH_RERUNS and task:
        if st.button("Rerun this research", key=f"rerun_{section_key}", use_container_width=True):
            try:
                result = preview_research_rerun(section_key, project_id=str(st.session_state["backend_project_id"]), source_run_id=str(st.session_state["backend_run_id"]), idempotency_key=make_idempotency_key())
                st.session_state["bp_rerun_preview"] = result
                st.session_state["bp_rerun_proposal"] = {"target_module":section_key}
                st.info("Impact preview created. Nothing has been rerun yet.")
            except BackendError as exc: st.error(str(exc))
        preview = st.session_state.get("bp_rerun_preview")
        if preview and (st.session_state.get("bp_rerun_proposal") or {}).get("target_module") == section_key:
            impact = _dict(preview.get("impact"))
            st.warning(impact.get("explanation") or "Review the affected modules. Nothing has been rerun yet.")
            approve, cancel = st.columns(2)
            if approve.button("Approve", type="primary", key=f"approve_{section_key}", use_container_width=True):
                try:
                    result = resolve_research_rerun(str(preview["rerun_request_id"]), int(preview["expected_source_state_version"]), "APPROVE")
                    st.session_state["backend_run_id"] = result["run_id"]
                    for key in ("backend_bundle","bp_rerun_preview","bp_rerun_proposal"): st.session_state.pop(key, None)
                    st.session_state["backend_last_refresh_at"] = 0; st.rerun()
                except BackendError as exc: st.error(str(exc))
            if cancel.button("Cancel", key=f"cancel_{section_key}", use_container_width=True):
                try: resolve_research_rerun(str(preview["rerun_request_id"]), int(preview["expected_source_state_version"]), "CANCEL")
                except BackendError as exc: st.error(str(exc)); return
                st.session_state.pop("bp_rerun_preview", None); st.session_state.pop("bp_rerun_proposal", None); st.rerun()


def render_blueprint_workspace() -> None:
    if not st.session_state.get("backend_run_id"):
        st.info("Complete onboarding to create the first Blueprint run."); return
    _render_css()
    try:
        refresh = st.button("Refresh", key="workspace_refresh")
        bundle = hydrate_current_run(force=refresh) or {}
    except BackendError as exc:
        st.error(str(exc)); st.caption("Your completed data remains in Supabase. Refresh once the backend is available."); return

    context = _dict(bundle.get("research_context")); dashboard = _dict(bundle.get("blueprint")); current = _dict(dashboard.get("current_version")); artifact = _dict(current.get("blueprint")); tasks = _task_map(bundle)
    control = _dict(bundle.get("control_panel")); checkpoints = [x for x in _items(control.get("panel_items")) if isinstance(x,dict) and x.get("item_type") == "HUMAN_CHECKPOINT"]
    verdicts = [v for v in _items(dashboard.get("latest_verdicts")) if isinstance(v, dict)]
    research_verdict = next((v for v in verdicts if v.get("gate") == "RESEARCH_VERDICT"), {})
    latest_verdict = _dict(context.get("latest_verdict")) or research_verdict
    has_gate_1 = any(k in tasks for k in ("assumptions_risks","offer_pricing","validation_proof","operating_model","financial_readiness","execution_readiness"))
    has_gate_2 = any(k in tasks for k in ("launch_distribution","growth_optimization","action_blueprint"))
    all_outputs = [_dict(t.get("output")) for t in tasks.values() if isinstance(t.get("output"), dict)]
    risks = sum(len(_items(o.get("risks"))) for o in all_outputs)
    coverages = [float(o.get("coverage")) for o in all_outputs if isinstance(o.get("coverage"),(int,float))]
    coverage = round(100 * sum(coverages) / len(coverages)) if coverages else 0
    progress_rows = [p for p in _items(dashboard.get("stage_progress")) if isinstance(p, dict)]
    completion = round(sum(float(p.get("completion_percent") or 0) for p in progress_rows) / max(1,len(progress_rows)))
    score = research_verdict.get("score")
    score_text = f"{float(score):.0f}/100" if isinstance(score,(int,float)) else "Withheld"
    idea = _dict(context.get("project")).get("idea_text") or artifact.get("product_idea") or st.session_state.get("idea","Your Blueprint")
    st.markdown(f'<div class="bp-brand">Blueprint Evidence Dev</div><div class="bp-title">{html.escape(str(idea))}</div><div class="bp-sub">Dynamic evidence Blueprint · advisory, source-bounded, founder-controlled</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kpi-grid"><div class="kpi"><b>{score_text}</b><span>Research viability</span></div><div class="kpi"><b>{coverage}%</b><span>Evidence coverage</span></div><div class="kpi"><b>{risks}</b><span>Open risks</span></div><div class="kpi"><b>{completion}%</b><span>Blueprint completion</span></div></div>', unsafe_allow_html=True)

    selected = st.session_state.setdefault("bp_selected_section", "customer_demand")
    left, center, right = st.columns([1.05,3.4,1.25], gap="medium")
    with left:
        with st.container(border=True):
            for stage_name, section_items in STAGES:
                st.markdown(f'<div class="stage-label">{stage_name}</div>', unsafe_allow_html=True)
                for key, label in section_items:
                    state = _section_state(tasks.get(key), _stage_number(key), has_gate_1, has_gate_2)
                    active = key == selected
                    if st.button(f"{_status_icon(state[0])}  {label}\n\n{state[1]}", key=f"select_{key}", use_container_width=True, type="primary" if active else "secondary"):
                        st.session_state["bp_selected_section"] = key; st.rerun()
    selected = st.session_state.get("bp_selected_section", selected); task = tasks.get(selected); state = _section_state(task,_stage_number(selected),has_gate_1,has_gate_2); output = _extract_output(task,artifact,selected); sources = _flatten_sources(output,context)
    with center:
        with st.container(border=True): _render_center(selected,task,output,state,context)
    with right: _render_right(selected,task,output,sources)

    if checkpoints and not st.session_state.get(f"gate_seen_{checkpoints[0].get('checkpoint_id')}"):
        _gate_dialog(checkpoints[0], latest_verdict)
