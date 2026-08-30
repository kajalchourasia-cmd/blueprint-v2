"""Small functional UI components for the authenticated backend flow."""

from __future__ import annotations

import streamlit as st

from blueprint.backend import BackendError, hydrate_current_run, resolve_founder_checkpoint


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
