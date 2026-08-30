"""Small functional UI components for the authenticated backend flow."""

from __future__ import annotations

import streamlit as st

from blueprint.backend import (
    BackendError,
    ask_research,
    hydrate_current_run,
    make_idempotency_key,
    preview_research_rerun,
    resolve_founder_checkpoint,
    resolve_research_rerun,
)


TERMINAL_STATUSES = {"COMPLETED", "PARTIAL", "HUMAN_REVIEW", "SAFE_FAILED", "CANCELLED"}


def render_backend_status_panel() -> None:
    if not st.session_state.get("backend_run_id"):
        return
    try:
        bundle = hydrate_current_run(force=st.button("Refresh research status", key="bp_refresh_backend")) or {}
    except BackendError as exc:
        st.warning(str(exc))
        return
    control = bundle.get("control_panel") or {}
    snapshot = bundle.get("snapshot") or {}
    run = snapshot.get("run") or {}
    status = str(control.get("run_status") or run.get("status") or "NEW")
    summary = control.get("summary") or {}
    completed = int(summary.get("completed") or 0)
    in_progress = int(summary.get("in_progress") or 0)
    attention = int(summary.get("needs_attention") or 0)
    st.info(
        f"Research run **{status.replace('_', ' ').title()}** · "
        f"{completed} completed · {in_progress} active · {attention} needing attention"
    )
    errors = bundle.get("errors") or {}
    if errors:
        retryable = [value["message"] for value in errors.values() if value.get("retryable")]
        if retryable:
            st.caption("Some dashboard projections are temporarily unavailable. Existing results remain preserved.")
    checkpoints = [
        item
        for item in (control.get("panel_items") or [])
        if item.get("item_type") == "HUMAN_CHECKPOINT"
    ]
    for checkpoint in checkpoints:
        with st.container(border=True):
            st.markdown(f"**{checkpoint.get('title', 'Your decision is required')}**")
            st.write(checkpoint.get("message", "Review the evidence before continuing."))
            allowed = checkpoint.get("allowed_decisions") or []
            if allowed:
                decision = st.selectbox(
                    "Decision",
                    allowed,
                    key=f"decision_{checkpoint.get('checkpoint_id')}",
                )
                note = st.text_input("Optional note", key=f"note_{checkpoint.get('checkpoint_id')}")
                if st.button("Apply decision", key=f"apply_{checkpoint.get('checkpoint_id')}"):
                    try:
                        resolve_founder_checkpoint(
                            str(checkpoint["checkpoint_id"]),
                            int(checkpoint["state_version"]),
                            str(decision),
                            {"founder_note": note} if note else {},
                        )
                        st.session_state.pop("backend_bundle", None)
                        st.success("Decision recorded. Blueprint will re-evaluate the route.")
                        st.rerun()
                    except BackendError as exc:
                        st.error(str(exc))
    if status not in TERMINAL_STATUSES:
        st.caption("Research continues in n8n. Use Refresh research status while this temporary integration panel is visible.")


SECTION_LABELS = {
    "foundation": "Foundation",
    "customer_demand": "Customer Research",
    "competitor_intelligence": "Competitor Research",
    "market_economics": "Market Research",
}


def _list(value):
    return value if isinstance(value, list) else []


def _render_section(section: dict) -> None:
    content = section.get("content") if isinstance(section.get("content"), dict) else {}
    finding = content.get("executive_finding") or content.get("summary") or "This section is still being prepared."
    st.markdown(f"#### {section.get('title') or SECTION_LABELS.get(section.get('section_key'), 'Research')}")
    st.write(finding)
    actionables = _list(section.get("actionables") or content.get("contextual_actions"))
    signals = _list(content.get("observed_signals"))
    risks = _list(content.get("risks"))
    unknowns = _list(content.get("unknowns"))
    evidence = _list(content.get("evidence_cards"))
    left, right = st.columns([1.7, 1])
    with left:
        if signals:
            st.markdown("**Evidence-supported signals**")
            for item in signals[:8]:
                claim = item.get("claim") if isinstance(item, dict) else str(item)
                if claim:
                    st.markdown(f"- {claim}")
        if evidence:
            st.markdown("**Sources**")
            for item in evidence[:12]:
                if not isinstance(item, dict):
                    continue
                title = item.get("source_title") or item.get("title") or item.get("source_domain") or "Source"
                url = item.get("source_url") or item.get("url")
                evidence_id = item.get("evidence_id") or item.get("id") or ""
                st.markdown(f"- [{title}]({url}) · `{evidence_id}`" if url else f"- {title} · `{evidence_id}`")
        if not signals and not evidence:
            st.caption("No audited external evidence is visible for this section yet.")
    with right:
        if actionables:
            st.markdown("**Founder actionables**")
            for item in actionables[:5]:
                if isinstance(item, dict):
                    st.markdown(f"- **{item.get('title', 'Next action')}** — {item.get('why', '')}")
                else:
                    st.markdown(f"- {item}")
        if risks:
            st.markdown("**Open risks**")
            for item in risks[:5]:
                st.markdown(f"- {item.get('risk') if isinstance(item, dict) else item}")
        if unknowns:
            st.markdown("**Unknowns**")
            for item in unknowns[:5]:
                st.markdown(f"- {item}")


def _render_rerun_approval() -> None:
    proposal = st.session_state.get("bp_rerun_proposal")
    preview = st.session_state.get("bp_rerun_preview")
    if proposal and not preview:
        target = str(proposal.get("target_module") or "")
        label = SECTION_LABELS.get(target, target.replace("_", " ").title())
        st.warning(f"A fresh {label} run was proposed. Nothing has been rerun yet.")
        if st.button("Review rerun impact", key="bp_preview_rerun"):
            try:
                preview = preview_research_rerun(
                    target,
                    project_id=str(st.session_state["backend_project_id"]),
                    source_run_id=str(st.session_state["backend_run_id"]),
                    idempotency_key=st.session_state.setdefault("bp_rerun_idempotency_key", make_idempotency_key()),
                )
                st.session_state["bp_rerun_preview"] = preview
                st.rerun()
            except BackendError as exc:
                st.error(str(exc))
    if preview:
        impact = preview.get("impact") or {}
        affected = [str(item).replace("_", " ").title() for item in _list(impact.get("affected_modules"))]
        with st.container(border=True):
            st.markdown("**Rerun impact preview**")
            st.write(impact.get("explanation") or "Review the affected modules before approving.")
            if affected:
                st.caption("Will refresh: " + " → ".join(affected))
            approve, cancel = st.columns(2)
            with approve:
                if st.button("Approve and rerun", type="primary", key="bp_approve_rerun", use_container_width=True):
                    try:
                        result = resolve_research_rerun(
                            str(preview["rerun_request_id"]),
                            int(preview["expected_source_state_version"]),
                            "APPROVE",
                        )
                        st.session_state["backend_run_id"] = result["run_id"]
                        st.session_state["backend_bundle"] = None
                        st.session_state["backend_last_refresh_at"] = 0
                        st.session_state.pop("bp_rerun_proposal", None)
                        st.session_state.pop("bp_rerun_preview", None)
                        st.session_state.pop("bp_rerun_idempotency_key", None)
                        st.success("Approved rerun queued through the dynamic Supervisor.")
                        st.rerun()
                    except BackendError as exc:
                        st.error(str(exc))
            with cancel:
                if st.button("Cancel rerun", key="bp_cancel_rerun", use_container_width=True):
                    try:
                        resolve_research_rerun(
                            str(preview["rerun_request_id"]),
                            int(preview["expected_source_state_version"]),
                            "CANCEL",
                        )
                    except BackendError as exc:
                        st.error(str(exc))
                        return
                    for key in ("bp_rerun_proposal", "bp_rerun_preview", "bp_rerun_idempotency_key"):
                        st.session_state.pop(key, None)
                    st.rerun()


def render_research_workspace() -> None:
    """Render canonical dynamic research before the existing dashboard redesign layer."""
    if not st.session_state.get("backend_run_id"):
        return
    try:
        bundle = hydrate_current_run() or {}
    except BackendError as exc:
        st.warning(str(exc))
        return
    blueprint_projection = bundle.get("blueprint") or {}
    current = blueprint_projection.get("current_version") or {}
    artifact = current.get("blueprint") if isinstance(current.get("blueprint"), dict) else {}
    sections = [item for item in _list(artifact.get("sections")) if isinstance(item, dict)]
    research_context = bundle.get("research_context") or {}
    if not sections:
        for task in _list(research_context.get("orchestration_tasks")):
            if not isinstance(task, dict) or task.get("module_key") not in SECTION_LABELS or not isinstance(task.get("output"), dict):
                continue
            sections.append({
                "section_key": task["module_key"],
                "title": SECTION_LABELS[task["module_key"]],
                "status": task.get("status"),
                "content": task["output"],
                "actionables": _list(task["output"].get("contextual_actions")),
            })
    verdict = artifact.get("verdict") if isinstance(artifact.get("verdict"), dict) else {}
    if not verdict and isinstance(research_context.get("latest_verdict"), dict):
        live_verdict = research_context["latest_verdict"]
        verdict = {
            "verdict": live_verdict.get("verdict"),
            "score": live_verdict.get("score"),
            "explanation": live_verdict.get("explanation"),
        }
    if sections or verdict:
        with st.container(border=True):
            st.markdown("### Live Evidence Blueprint")
            if verdict:
                cols = st.columns(4)
                cols[0].metric("Verdict", str(verdict.get("verdict") or "WITHHELD").replace("_", " ").title())
                score = verdict.get("score")
                cols[1].metric("Viability", f"{float(score):.0f}/100" if isinstance(score, (int, float)) else "Withheld")
                cols[2].metric("Open risks", len(_list(artifact.get("open_risks"))))
                cols[3].metric("Open assumptions", len(_list(artifact.get("open_assumptions"))))
                st.caption(verdict.get("explanation") or "The verdict remains withheld until evidence is decision-capable.")
            if sections:
                tabs = st.tabs([str(section.get("title") or SECTION_LABELS.get(section.get("section_key"), "Research")) for section in sections])
                for tab, section in zip(tabs, sections):
                    with tab:
                        _render_section(section)
    else:
        st.info("The original Blueprint is saved. Dynamic research sections will appear here as each specialist completes and the auditor accepts the evidence.")

    with st.expander("Ask this Research", expanded=True):
        st.caption("Grounded only in this project’s retrieved task outputs, immutable Blueprint, verdict, and audited evidence. It cannot contact people or perform external actions.")
        history = st.session_state.setdefault("bp_research_chat", [])
        for message in history[-10:]:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                if message.get("citations"):
                    st.caption("Evidence: " + ", ".join(message["citations"]))
        if question := st.chat_input("Ask about a finding, source, limitation, actionable, or request a research rerun", key="bp_research_chat_input"):
            history.append({"role": "user", "content": question})
            try:
                answer = ask_research(
                    question,
                    project_id=str(st.session_state["backend_project_id"]),
                    run_id=str(st.session_state["backend_run_id"]),
                    thread_id=st.session_state.get("bp_research_thread_id"),
                )
                if answer.get("thread_id"):
                    st.session_state["bp_research_thread_id"] = answer["thread_id"]
                history.append({
                    "role": "assistant",
                    "content": answer.get("answer") or "I could not answer that from accepted research.",
                    "citations": _list(answer.get("citations")),
                })
                command = answer.get("command") if isinstance(answer.get("command"), dict) else {}
                if answer.get("status") == "NEEDS_CONFIRMATION" and command.get("target_module"):
                    st.session_state["bp_rerun_proposal"] = {"target_module": command["target_module"]}
            except BackendError as exc:
                history.append({"role": "assistant", "content": str(exc), "citations": []})
            st.rerun()
        _render_rerun_approval()
