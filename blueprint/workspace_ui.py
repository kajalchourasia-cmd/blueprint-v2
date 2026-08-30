"""Live, section-specific workspace for a founder's evidence Blueprint."""

from __future__ import annotations

import html
import re
from typing import Any

import streamlit as st

from blueprint.backend import (
    BackendError, ask_research, hydrate_current_run, make_idempotency_key,
    preview_research_rerun, resolve_founder_checkpoint, resolve_research_rerun,
)

STAGES = [
    ("Stage 1 · Discover", [("foundation", "Foundation"), ("customer_demand", "Customer Research"), ("competitor_intelligence", "Competitor Research"), ("market_economics", "Market Research"), ("evidence_audit", "Evidence Audit"), ("research_verdict", "Research Verdict")]),
    ("Stage 2 · Prove & design", [("assumptions_risks", "Assumptions & Risks"), ("offer_pricing", "Offer & Pricing"), ("validation_proof", "Validation Plan"), ("operating_model", "Operating Model"), ("financial_readiness", "Financial Readiness"), ("execution_readiness", "Gate 2 Readiness")]),
    ("Stage 3 · Action Blueprint", [("launch_distribution", "MVP & Distribution"), ("growth_optimization", "Growth Prerequisites"), ("action_blueprint", "Action Blueprint")]),
]
LABELS = {key: label for _, items in STAGES for key, label in items}
RESEARCH_RERUNS = {"customer_demand", "competitor_intelligence", "market_economics"}
DONE = {"COMPLETED", "REUSED", "NOT_APPLICABLE"}
FAILED = {"PARTIAL", "SAFE_FAILED", "HUMAN_REVIEW", "NEEDS_INPUT"}
VERDICT_LABELS = {"GO": "Promising — proceed to validation", "CONDITIONAL_GO": "Promising, with evidence gaps", "PROCEED_WITH_CAUTION": "Proceed carefully", "HOLD_OR_PIVOT": "Pause and refine the idea", "PAUSE_OR_REVISE": "Pause and refine the idea", "NO_GO": "Do not invest further yet", "WITHHELD": "Decision withheld — more evidence needed"}
DECISION_LABELS = {"PROCEED": "Continue to Stage 2", "CONTINUE_ANYWAY": "Continue with the stated limitations", "TARGETED_VALIDATION": "Run focused validation first", "RUN_MISSING_RESEARCH": "Complete missing research", "PAUSE_OR_REVISE": "Pause and revise the idea", "CANCEL": "Stop this Blueprint"}


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


def _project_title(idea: str) -> str:
    clean = re.sub(r"\s+", " ", str(idea).strip()).rstrip(".!?")
    clean = re.sub(r"^(?:i|we)\s+(?:really\s+)?(?:want|would like|plan|hope|need)\s+to\s+", "", clean, flags=re.I)
    clean = re.sub(r"^(?:my|our)\s+idea\s+is\s+(?:to\s+)?", "", clean, flags=re.I)
    clean = re.sub(r"^(?:build|create|launch|start|make)\s+(?:an?\s+)?", "", clean, flags=re.I)
    clean = re.split(r"\s+(?:that|which|so that)\s+", clean, maxsplit=1, flags=re.I)[0]
    product_phrase = re.match(r"^(.+?\b(?:app|platform|service|tool|marketplace|store|business|product))\s+for\b", clean, flags=re.I)
    if product_phrase:
        clean = product_phrase.group(1)
    words = clean.split()[:7]
    small = {"a", "an", "and", "for", "in", "of", "the", "to", "with"}
    return " ".join(word if word.isupper() else (word.lower() if i and word.lower() in small else word.capitalize()) for i, word in enumerate(words)) or "Untitled Blueprint"


def _goal_line(context: dict) -> str:
    stored = _dict(_dict(context.get("project")).get("constraints"))
    answers = _dict(stored.get("onboarding_answers")) or _dict(st.session_state.get("dialog_answers"))
    success, kind, goal = (str(answers.get(key) or "").strip() for key in ("success_definition", "success_type", "goal"))
    if success and kind:
        return f"Goal: {kind} — {success}"
    if success or (kind and kind.lower() != "not sure"):
        return f"Goal: {success or kind}"
    return f"Goal: {goal}" if goal else "Goal not specified — optimizing for evidence before commitment."


def _section_state(task: dict | None, stage: int, gate_1: bool, gate_2: bool) -> tuple[str, str]:
    if task:
        status = str(task.get("status") or "PLANNED").upper()
        if status in DONE:
            return "done", "Completed" if status != "NOT_APPLICABLE" else "Not applicable"
        if status == "RUNNING":
            return "running", "Researching"
        if status in {"READY", "PLANNED"}:
            return "ready", "Queued"
        if status in FAILED:
            return "error", status.replace("_", " ").title()
        return "locked", status.replace("_", " ").title()
    if stage == 2:
        return ("ready", "Starting") if gate_1 else ("locked", "Needs Gate 1 decision")
    if stage == 3:
        return ("ready", "Starting") if gate_2 else ("locked", "Needs Gate 2 decision")
    return "idle", "Not started"


def _extract_output(task: dict | None, artifact: dict, key: str) -> dict:
    if task and isinstance(task.get("output"), dict):
        return task["output"]
    for section in _items(artifact.get("sections")):
        if isinstance(section, dict) and section.get("section_key") == key:
            content = section.get("content") or section.get("summary") or section
            return content if isinstance(content, dict) else {"executive_finding": str(content)}
    return artifact if key == "action_blueprint" and artifact.get("module_key") == key else {}


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


def _score(verdict: dict) -> float | None:
    value = verdict.get("score", verdict.get("research_viability_score"))
    return float(value) if isinstance(value, (int, float)) else None


def _item_text(value: Any) -> str:
    if not isinstance(value, dict):
        return str(value).strip()
    for key in ("claim", "title", "name", "risk", "assumption", "unknown", "limitation", "recommendation", "why", "description", "summary"):
        if value.get(key):
            return str(value[key])
    return " · ".join(f"{str(k).replace('_', ' ').title()}: {v}" for k, v in list(value.items())[:4] if v not in (None, "", []))


def _clean(values: Any, limitations: bool = False) -> list[str]:
    rows, seen = [], set()
    for value in _items(values):
        text = re.sub(r"\s+", " ", _item_text(value)).strip(" -")
        canonical = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
        if not text or canonical in seen or (limitations and "must pass evidence audit before a decision" in canonical):
            continue
        seen.add(canonical); rows.append(text)
    return rows


def _render_css(running: list[str]) -> None:
    spin = "".join(f".st-key-select_{key} button:before{{content:'';width:9px;height:9px;border:2px solid #90b89c;border-top-color:#1f6a40;border-radius:50%;animation:spin .8s linear infinite;position:absolute;right:12px;top:15px}}" for key in running)
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600&display=swap');
:root{{--ink:#172019;--muted:#727a74;--line:#dce2dd;--panel:#fbfcf9;--deep:#193f2a;--green:#2c7a4b}}
[data-testid="stAppViewContainer"],[data-testid="stHeader"]{{background:linear-gradient(135deg,#f5f6f2,#e9eee9)}}[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stSidebar"],[data-testid="stSidebarNav"],#MainMenu,footer{{display:none!important}}[data-testid="stAppViewContainer"]>.main{{margin-left:0!important}}main .block-container{{width:100%!important;max-width:1920px!important;padding:10px 18px 24px!important}}
.bp-wordmark{{display:flex;align-items:center;gap:9px;font:600 18px 'Space Grotesk';letter-spacing:-.055em;margin:5px 0 20px}}.bp-wordmark:before{{content:'';width:12px;height:12px;border-radius:50%;background:var(--green);box-shadow:0 0 0 6px rgba(44,122,75,.1)}}
.bp-project-title{{font:500 clamp(30px,3.2vw,52px)/.96 'Space Grotesk';letter-spacing:-.068em;margin:2px 0 7px;color:var(--ink)}}.bp-goal{{font:10px/1.45 'DM Mono';color:var(--muted)}}.bp-live{{display:inline-flex;align-items:center;gap:7px;padding:8px 11px;border:1px solid #cbd8ce;border-radius:20px;background:#f7fbf7;color:#356447;font:9px 'DM Mono'}}.bp-live:before{{content:'';width:7px;height:7px;border-radius:50%;background:#43a467;animation:pulse 1.7s infinite}}
.kpi-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin:18px 0}}.kpi{{position:relative;overflow:hidden;background:#fff;border:1px solid var(--line);border-radius:16px;padding:13px 14px;min-height:74px}}.kpi:after{{content:'';position:absolute;right:-18px;bottom:-27px;width:65px;height:65px;border-radius:50%;background:var(--tint,#e6efe8)}}.kpi b{{display:block;white-space:nowrap;font:500 24px 'Space Grotesk';letter-spacing:-.055em}}.kpi span{{font:8px 'DM Mono';color:var(--muted);text-transform:uppercase}}
.st-key-bp_left_rail,.st-key-bp_center_pane,.st-key-bp_right_rail{{height:calc(100vh - 32px);min-height:720px;border:1px solid var(--line);background:rgba(251,252,249,.94);overflow-y:auto}}.st-key-bp_left_rail{{border-radius:25px 12px 12px 25px;padding:17px 12px!important}}.st-key-bp_center_pane{{border-radius:12px;padding:20px 26px 105px!important}}.st-key-bp_right_rail{{border-radius:12px 25px 25px 12px;padding:16px 13px!important;background:#f7f8f4}}
.stage-label{{margin:19px 7px 8px;font:500 8px 'DM Mono';text-transform:uppercase;color:#8a918b}}.st-key-bp_left_rail [data-testid="stButton"] button{{position:relative;min-height:47px!important;padding:8px 29px 8px 11px!important;border:0!important;border-radius:13px!important;background:transparent!important;color:#39423b!important;text-align:left!important;justify-content:flex-start!important;white-space:pre-line!important;font:500 10px/1.25 'Space Grotesk'!important;box-shadow:none!important}}.st-key-bp_left_rail [data-testid="stButton"] button:hover{{background:#edf2ec!important}}.st-key-bp_left_rail [data-testid="stButton"] button[kind="primary"]{{background:var(--deep)!important;color:#fff!important}}
.section-kicker{{font:8px 'DM Mono';color:#79827a;text-transform:uppercase}}.section-title{{font:500 31px 'Space Grotesk';letter-spacing:-.06em;margin:6px 0 2px}}.section-summary{{margin:13px 0 21px;padding:16px 18px;border-left:3px solid var(--green);border-radius:0 15px 15px 0;background:#f1f6f1;font:14px/1.55 'Space Grotesk'}}.state-banner{{display:flex;gap:13px;margin:22px 0;padding:18px;border:1px solid var(--line);border-radius:17px;background:#f6f8f5}}.state-spinner{{width:25px;height:25px;border:3px solid #cfdbd1;border-top-color:#267749;border-radius:50%;animation:spin .8s linear infinite}}.state-banner b{{display:block;font:500 14px 'Space Grotesk'}}.state-banner span{{font:10px/1.4 'DM Mono';color:var(--muted)}}
.detail-heading{{margin:23px 0 9px;font:500 9px 'DM Mono';text-transform:uppercase;color:#6e776f}}.insight-list{{display:grid;gap:8px}}.insight{{padding:11px 13px;border:1px solid #e1e5e1;border-radius:12px;background:#fff;font:12px/1.48 'Space Grotesk'}}.empty-state{{display:grid;place-items:center;min-height:260px;text-align:center;color:#737d75}}.empty-state b{{display:block;font:500 22px 'Space Grotesk';color:#2a352d}}.empty-state p{{max-width:500px;font:12px/1.5 'Space Grotesk'}}
.verdict-hero{{margin:17px 0;padding:22px;border-radius:20px;background:linear-gradient(135deg,#193f2a,#286345);color:#f2f8f3}}.verdict-hero strong{{font:500 25px 'Space Grotesk'}}.verdict-hero p{{color:#c8dbce;font:12px/1.5 'Space Grotesk'}}.score-row{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}}.score-cell{{padding:12px;border:1px solid var(--line);border-radius:13px;background:#fff}}.score-cell b{{display:block;font:500 18px 'Space Grotesk'}}.score-cell span{{font:8px 'DM Mono';text-transform:uppercase;color:#7c857e}}
.chat-divider{{margin:30px 0 12px;border-top:1px solid var(--line)}}.st-key-bp_center_pane [data-testid="stChatInput"]{{position:sticky!important;bottom:0;z-index:20;background:#fbfcf9;padding-top:12px}}.stChatMessage{{background:#f3f6f2!important;border-radius:15px!important}}.right-title{{font:500 9px 'DM Mono';text-transform:uppercase;margin:10px 4px}}.notepad{{padding:15px 13px 10px;border:1px solid #ded9b9;border-radius:17px;background:repeating-linear-gradient(#fffdf2 0,#fffdf2 27px,#e8e2c8 28px)}}.notepad-title{{font:500 17px 'Space Grotesk';margin-bottom:8px}}.st-key-bp_right_rail [data-testid="stExpander"]{{border:1px solid var(--line)!important;border-radius:14px!important;background:#fff!important;margin-top:9px}}.st-key-bp_right_rail [data-testid="stCheckbox"] input:checked+div{{background:#348557!important;animation:pop .25s ease-out}}[data-testid="stDialog"]>div{{max-width:720px!important;border-radius:25px!important;background:#f8faf7!important}}
{spin}@keyframes spin{{to{{transform:rotate(360deg)}}}}@keyframes pulse{{50%{{opacity:.3}}}}@keyframes pop{{50%{{transform:scale(1.25)}}}}@media(max-width:1100px){{.kpi-grid{{grid-template-columns:repeat(2,1fr)}}.st-key-bp_left_rail,.st-key-bp_center_pane,.st-key-bp_right_rail{{height:auto;min-height:0;border-radius:18px}}}}
</style>""", unsafe_allow_html=True)


def _render_list(title: str, values: Any, limitations: bool = False) -> None:
    rows = _clean(values, limitations)[:12]
    if not rows:
        return
    st.markdown(f'<div class="detail-heading">{html.escape(title)}</div><div class="insight-list">', unsafe_allow_html=True)
    for row in rows:
        st.markdown(f'<div class="insight">{html.escape(row)}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def _render_competitors(output: dict) -> None:
    competitors = _items(output.get("competitors")) or _items(output.get("competitor_matrix"))
    rows = []
    for item in competitors:
        if isinstance(item, dict):
            rows.append({"Competitor": item.get("name") or item.get("competitor") or "Unknown", "Type": item.get("type") or item.get("category") or "Unclassified", "What they do well": item.get("strengths") or item.get("customer_praise") or "Not evidenced", "Weakness / complaint": item.get("weaknesses") or item.get("customer_complaints") or "Not evidenced", "MVP / differentiator": item.get("mvp") or item.get("differentiator") or item.get("core_offer") or "Not evidenced", "Gap for this idea": item.get("gap") or item.get("opportunity") or "Not established"})
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.warning("A decision-grade competitor matrix has not been produced yet. Blueprint will not present directories, review sites, or research tools as competitors.")


def _render_verdict(output: dict, checkpoint: dict | None) -> None:
    score = _score(output); label = VERDICT_LABELS.get(str(output.get("verdict") or "WITHHELD").upper(), str(output.get("verdict") or "Withheld").replace("_", " ").title())
    explanation = str(output.get("explanation") or output.get("rationale") or "The decision explanation is not available yet.")
    st.markdown(f'<div class="verdict-hero"><strong>{html.escape(label)}</strong><p>{html.escape(explanation)}</p></div>', unsafe_allow_html=True)
    coverage = output.get("evidence_coverage", output.get("coverage")); coverage_text = "Unknown"
    if isinstance(coverage, (int, float)):
        coverage_text = f"{float(coverage) * 100 if float(coverage) <= 1 else float(coverage):.0f}%"
    status = str(output.get("score_status") or ("Decision capable" if output.get("decision_capable") else "Evidence incomplete")).replace("_", " ").title()
    st.markdown(f'<div class="score-row"><div class="score-cell"><b>{f"{score:.0f}/100" if score is not None else "Withheld"}</b><span>Viability score</span></div><div class="score-cell"><b>{coverage_text}</b><span>Evidence coverage</span></div><div class="score-cell"><b>{html.escape(status)}</b><span>Decision status</span></div></div>', unsafe_allow_html=True)
    dimensions = _dict(output.get("dimension_scores"))
    if dimensions:
        st.dataframe([{"Dimension": key.replace("_", " ").title(), "Score": value} for key, value in dimensions.items()], hide_index=True, use_container_width=True)
    _render_list("Evidence supporting the decision", output.get("supporting_signals") or output.get("observed_signals"))
    _render_list("What weakens the decision", output.get("critical_blockers") or output.get("risks"))
    _render_list("What would change this verdict", output.get("next_evidence_needed") or output.get("unknowns"))
    if checkpoint and st.button("Review decision and unlock the next stage", type="primary", use_container_width=True):
        _gate_dialog(checkpoint, output)


def _render_output(key: str, output: dict, checkpoint: dict | None) -> None:
    if key == "research_verdict":
        _render_verdict(output, checkpoint); return
    finding = output.get("executive_finding") or output.get("summary") or output.get("explanation")
    if finding:
        st.markdown(f'<div class="section-summary">{html.escape(str(finding))}</div>', unsafe_allow_html=True)
    if key == "competitor_intelligence":
        _render_competitors(output)
    for title, values in [("Problem and founder context", output.get("problem_hypothesis") or output.get("starting_position")), ("Evidence-supported signals", output.get("observed_signals")), ("Customer jobs and pains", output.get("customer_jobs") or output.get("pains")), ("Recommendations", output.get("recommendations")), ("Scenarios", output.get("scenarios")), ("Milestones", output.get("milestones")), ("Assumptions to test", output.get("assumptions")), ("Risks", output.get("risks")), ("Contradictions", output.get("contradictions")), ("Unknowns", output.get("unknowns")), ("Limitations", output.get("limitations"))]:
        _render_list(title, [values] if isinstance(values, dict) else values, title == "Limitations")
    if key == "foundation" and not any(_items(output.get(name)) for name in ("assumptions", "risks", "unknowns")):
        st.info("This older run has only a thin foundation. The research-quality pass will add the problem hypothesis, target-user boundary, founder constraints, riskiest assumptions, and unresolved unknowns.")


def _render_empty(key: str, state: tuple[str, str]) -> None:
    if state[0] == "running":
        st.markdown('<div class="state-banner"><div class="state-spinner"></div><div><b>Research is running</b><span>Blueprint is gathering, auditing, and reconciling evidence. Accepted results will appear here automatically.</span></div></div>', unsafe_allow_html=True); return
    stage = _stage_number(key)
    message = "The Supervisor has queued this specialist and will start it when its dependencies are ready." if state[0] == "ready" else "The failed output was not promoted. Open Background process for the safe next route." if state[0] == "error" else "Stage 1 must finish first. Open Research Verdict, review why it was reached, then choose a founder decision to unlock Stage 2." if stage == 2 else "Stage 2 evidence and Gate 2 approval are required before this advisory action blueprint can be created." if stage == 3 else "This stream has not started. If selected during onboarding, the Supervisor will schedule it automatically."
    st.markdown(f'<div class="empty-state"><div><b>{html.escape(state[1])}</b><p>{html.escape(message)}</p></div></div>', unsafe_allow_html=True)


def _render_chat(key: str) -> None:
    label = LABELS[key]; st.markdown('<div class="chat-divider"></div>', unsafe_allow_html=True)
    st.caption(f"Ask about {label}. Answers are restricted to this Blueprint and its accepted evidence.")
    chats = st.session_state.setdefault("bp_section_chats", {}); threads = st.session_state.setdefault("bp_section_threads", {}); history = chats.setdefault(key, [])
    for message in history[-8:]:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message.get("citations"): st.caption("Evidence: " + ", ".join(message["citations"]))
    if question := st.chat_input(f"Ask about {label.lower()}…", key=f"chat_{key}"):
        history.append({"role": "user", "content": question})
        try:
            result = ask_research(question, project_id=str(st.session_state["backend_project_id"]), run_id=str(st.session_state["backend_run_id"]), thread_id=threads.get(key), section_key=key)
            if result.get("thread_id"): threads[key] = result["thread_id"]
            history.append({"role": "assistant", "content": result.get("answer") or "UNKNOWN — this section does not contain enough accepted evidence.", "citations": _items(result.get("citations"))})
        except BackendError as exc:
            history.append({"role": "assistant", "content": str(exc), "citations": []})
        st.rerun()


def _render_right(key: str, task: dict | None, output: dict, sources: list[dict]) -> None:
    st.markdown('<div class="right-title">Section companion</div><div class="notepad"><div class="notepad-title">Founder actionables</div>', unsafe_allow_html=True)
    actions = _items(output.get("contextual_actions"))
    if actions:
        completed = st.session_state.setdefault("bp_completed_actionables", {}); scoped = set(_items(completed.get(key)))
        for index, action in enumerate(actions[:7]):
            text = _item_text(action); action_id = f"{key}:{index}:{text[:40]}"; checked = st.checkbox(text, value=action_id in scoped, key=f"action_{key}_{index}")
            scoped.add(action_id) if checked else scoped.discard(action_id)
        completed[key] = sorted(scoped)
    else:
        st.caption("Actionables appear after this section has a valid output.")
    st.markdown('</div>', unsafe_allow_html=True)
    with st.expander(f"Sources · {len(sources)}", expanded=False):
        if sources:
            for source in sources[:12]:
                title = source.get("source_title") or source.get("title") or source.get("source_domain") or "Evidence source"; url = source.get("source_url") or source.get("url")
                st.markdown(f"[{title}]({url})" if url else str(title))
        else: st.caption("No accepted source is attached yet.")
    with st.expander("Background process", expanded=False):
        if task:
            st.write(f"Status: **{str(task.get('status', 'PLANNED')).replace('_', ' ').title()}**"); st.caption(task.get("route_reason") or "Waiting for the dynamic Supervisor.")
        else: st.caption("This worker has not been planned yet.")
    if key in RESEARCH_RERUNS and task:
        if st.button("Rerun this research", key=f"rerun_{key}", use_container_width=True):
            try:
                st.session_state["bp_rerun_preview"] = preview_research_rerun(key, project_id=str(st.session_state["backend_project_id"]), source_run_id=str(st.session_state["backend_run_id"]), idempotency_key=make_idempotency_key()); st.session_state["bp_rerun_proposal"] = {"target_module": key}; st.rerun()
            except BackendError as exc: st.error(str(exc))
        preview = st.session_state.get("bp_rerun_preview")
        if preview and (st.session_state.get("bp_rerun_proposal") or {}).get("target_module") == key:
            st.warning(_dict(preview.get("impact")).get("explanation") or "Review the impact. Nothing has rerun yet."); approve, cancel = st.columns(2)
            if approve.button("Approve", type="primary", key=f"approve_{key}", use_container_width=True):
                try:
                    result = resolve_research_rerun(str(preview["rerun_request_id"]), int(preview["expected_source_state_version"]), "APPROVE"); st.session_state["backend_run_id"] = result["run_id"]
                    for name in ("backend_bundle", "bp_rerun_preview", "bp_rerun_proposal"): st.session_state.pop(name, None)
                    st.rerun()
                except BackendError as exc: st.error(str(exc))
            if cancel.button("Cancel", key=f"cancel_{key}", use_container_width=True):
                try: resolve_research_rerun(str(preview["rerun_request_id"]), int(preview["expected_source_state_version"]), "CANCEL")
                except BackendError as exc: st.error(str(exc)); return
                st.session_state.pop("bp_rerun_preview", None); st.session_state.pop("bp_rerun_proposal", None); st.rerun()


def _gate_dialog(checkpoint: dict, verdict_data: dict) -> None:
    @st.dialog("Decide what Blueprint should do next", width="large")
    def gate() -> None:
        raw = str(verdict_data.get("verdict") or checkpoint.get("title") or "WITHHELD").upper(); score = _score(verdict_data)
        st.markdown(f"### {VERDICT_LABELS.get(raw, raw.replace('_', ' ').title())}" + (f" · {score:.0f}/100" if score is not None else ""))
        st.write(verdict_data.get("explanation") or checkpoint.get("message") or "Review the completed research before continuing.")
        allowed = _items(checkpoint.get("allowed_decisions"))
        if not allowed: st.error("No safe decision is currently available. Refresh the run state."); return
        decision = st.radio("Choose the next route", allowed, format_func=lambda value: DECISION_LABELS.get(value, str(value).replace("_", " ").title())); note = st.text_area("Optional founder note", placeholder="Add context that Stage 2 should respect.")
        if st.button("Apply decision and start the next route", type="primary", use_container_width=True):
            with st.spinner("Applying your decision and returning control to the Supervisor…"):
                try: result = resolve_founder_checkpoint(str(checkpoint["checkpoint_id"]), int(checkpoint["state_version"]), str(decision), {"founder_note": note} if note else {})
                except BackendError as exc: st.error(str(exc)); return
            st.session_state.pop("backend_bundle", None); st.session_state["backend_last_refresh_at"] = 0; st.session_state["bp_gate1_approved"] = str(decision) in {"PROCEED", "CONTINUE_ANYWAY", "TARGETED_VALIDATION"}; st.session_state["bp_selected_section"] = "assumptions_risks" if st.session_state["bp_gate1_approved"] else "research_verdict"; st.session_state["bp_transition_notice"] = result.get("message") or DECISION_LABELS.get(str(decision), "Decision applied"); st.rerun()
    gate()


def _workspace_body() -> None:
    try: bundle = hydrate_current_run(force=True) or {}
    except BackendError as exc: st.error(str(exc)); st.caption("Completed data remains in Supabase. Blueprint will retry automatically."); return
    context = _dict(bundle.get("research_context")); dashboard = _dict(bundle.get("blueprint")); artifact = _dict(_dict(dashboard.get("current_version")).get("blueprint")); tasks = _task_map(bundle); control = _dict(bundle.get("control_panel"))
    checkpoints = [item for item in _items(control.get("panel_items")) if isinstance(item, dict) and item.get("item_type") == "HUMAN_CHECKPOINT"]; checkpoint = checkpoints[0] if checkpoints else None
    verdicts = [item for item in _items(dashboard.get("latest_verdicts")) if isinstance(item, dict)]; dashboard_verdict = next((item for item in verdicts if item.get("gate") == "RESEARCH_VERDICT"), {}); latest_verdict = _dict(context.get("latest_verdict")) or dashboard_verdict
    gate_1 = st.session_state.get("bp_gate1_approved", False) or any(key in tasks for key in ("assumptions_risks", "offer_pricing", "validation_proof", "operating_model", "financial_readiness", "execution_readiness")); gate_2 = any(key in tasks for key in ("launch_distribution", "growth_optimization", "action_blueprint")); states = {key: _section_state(tasks.get(key), _stage_number(key), gate_1, gate_2) for _, sections in STAGES for key, _ in sections}; _render_css([key for key, state in states.items() if state[0] == "running"])
    idea = _dict(context.get("project")).get("idea_text") or artifact.get("idea_text") or artifact.get("product_idea") or st.session_state.get("idea", "Your Blueprint"); title = _project_title(str(idea)); outputs = [_dict(task.get("output")) for task in tasks.values() if isinstance(task.get("output"), dict)]; risks = sum(len(_clean(output.get("risks"))) for output in outputs); score = _score(dashboard_verdict or latest_verdict); progress = [item for item in _items(dashboard.get("stage_progress")) if isinstance(item, dict)]; completion = round(sum(float(item.get("completion_percent") or 0) for item in progress) / max(1, len(progress))) if progress else round(100 * sum(state[0] == "done" for state in states.values()) / len(states)); coverage_value = (dashboard_verdict or latest_verdict).get("evidence_coverage"); coverage = round((float(coverage_value) * 100 if float(coverage_value) <= 1 else float(coverage_value))) if isinstance(coverage_value, (int, float)) else 0
    left, center, right = st.columns([1.1, 3.7, 1.35], gap="small"); selected = st.session_state.setdefault("bp_selected_section", "customer_demand")
    with left:
        with st.container(key="bp_left_rail"):
            st.markdown('<div class="bp-wordmark">Blueprint</div>', unsafe_allow_html=True)
            for stage_name, sections in STAGES:
                st.markdown(f'<div class="stage-label">{html.escape(stage_name)}</div>', unsafe_allow_html=True)
                for key, label in sections:
                    state = states[key]; icon = {"done": "✓", "running": "◌", "ready": "·", "error": "!", "locked": "⌁", "idle": "○"}.get(state[0], "○")
                    if st.button(f"{icon}  {label}\n{state[1]}", key=f"select_{key}", use_container_width=True, type="primary" if key == selected else "secondary"): st.session_state["bp_selected_section"] = key; st.rerun()
    selected = st.session_state.get("bp_selected_section", selected); task = tasks.get(selected); state = states[selected]; output = _extract_output(task, artifact, selected)
    if selected == "research_verdict": output = {**output, **dashboard_verdict, **latest_verdict}
    sources = _flatten_sources(output, context)
    with center:
        with st.container(key="bp_center_pane"):
            st.markdown(f'<div class="bp-project-title">{html.escape(title)}</div><div class="bp-goal">{html.escape(_goal_line(context))}</div>', unsafe_allow_html=True); score_text = f"{score:.0f}/100" if score is not None else "Pending"
            st.markdown(f'<div class="kpi-grid"><div class="kpi" style="--tint:#dcebdc"><b>{score_text}</b><span>Decision score</span></div><div class="kpi" style="--tint:#dce8ef"><b>{coverage}%</b><span>Evidence coverage</span></div><div class="kpi" style="--tint:#f2dfd2"><b>{risks}</b><span>Open risks</span></div><div class="kpi" style="--tint:#e8ebc9"><b>{completion}%</b><span>Blueprint progress</span></div></div>', unsafe_allow_html=True)
            if notice := st.session_state.pop("bp_transition_notice", None): st.success(str(notice))
            st.markdown(f'<div class="section-kicker">Stage {_stage_number(selected)} · {html.escape(state[1])}</div><div class="section-title">{html.escape(LABELS[selected])}</div>', unsafe_allow_html=True)
            _render_output(selected, output, checkpoint if selected == "research_verdict" else None) if output else _render_empty(selected, state); _render_chat(selected)
    with right:
        with st.container(key="bp_right_rail"):
            st.markdown('<div class="bp-live">Live evidence workspace</div>', unsafe_allow_html=True); _render_right(selected, task, output, sources)
    if checkpoint:
        seen = f"bp_gate_seen_{checkpoint.get('checkpoint_id')}"
        if not st.session_state.get(seen):
            st.session_state[seen] = True; _gate_dialog(checkpoint, {**_extract_output(tasks.get("research_verdict"), artifact, "research_verdict"), **dashboard_verdict, **latest_verdict})


@st.fragment(run_every=4)
def _live_workspace() -> None:
    _workspace_body()


def render_blueprint_workspace() -> None:
    if not st.session_state.get("backend_run_id"):
        st.info("Complete onboarding to create the first Blueprint run."); return
    _live_workspace()
