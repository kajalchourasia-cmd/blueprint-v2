"""Typed client boundary between Streamlit, n8n, and owner-scoped Supabase RPCs."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

import requests
import streamlit as st

from blueprint.auth import get_auth_session, refresh_auth_session
from blueprint.config import AppConfig, load_config


RESEARCH_MODULES = {
    "Customer research": "customer_demand",
    "Competitor research": "competitor_intelligence",
    "Market research": "market_economics",
}


@dataclass
class BackendError(RuntimeError):
    message: str
    code: str = "BACKEND_ERROR"
    status_code: int = 0
    retryable: bool = False

    def __str__(self) -> str:
        return self.message


def _json_or_empty(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {}


def _safe_error(response: requests.Response, default: str) -> BackendError:
    payload = _json_or_empty(response)
    if isinstance(payload, list) and payload:
        payload = payload[0]
    payload = payload if isinstance(payload, dict) else {}
    code = str(payload.get("error_code") or payload.get("code") or "BACKEND_ERROR")
    message = str(payload.get("message") or payload.get("hint") or default)
    if response.status_code == 401:
        message, code = "Your private demo session expired. Refresh once to continue.", "UNAUTHENTICATED"
    elif response.status_code == 403:
        message, code = "You do not have access to this Blueprint.", "FORBIDDEN"
    elif response.status_code == 429:
        message, code = "The research service is busy. Wait briefly and retry.", "RATE_LIMIT"
    elif response.status_code >= 500:
        message = default
    return BackendError(message, code=code, status_code=response.status_code, retryable=response.status_code in {408, 429, 500, 502, 503, 504})


def _auth_headers(config: AppConfig, token: str) -> dict[str, str]:
    return {
        "apikey": config.supabase_publishable_key,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _authenticated_request(
    method: str,
    url: str,
    *,
    config: AppConfig,
    json: dict[str, Any] | None = None,
    params: dict[str, str] | None = None,
    retry_auth: bool = True,
) -> requests.Response:
    session = get_auth_session()
    if session is None:
        raise BackendError("The private demo session is unavailable. Refresh once to continue.", code="UNAUTHENTICATED", status_code=401)
    try:
        response = requests.request(
            method,
            url,
            headers=_auth_headers(config, session["access_token"]),
            json=json,
            params=params,
            timeout=(5, config.request_timeout_seconds),
        )
    except requests.Timeout as exc:
        raise BackendError("The request timed out safely. Retry without changing your inputs.", code="TIMEOUT", retryable=True) from exc
    except requests.RequestException as exc:
        raise BackendError("Blueprint could not reach the backend service.", code="PROVIDER", retryable=True) from exc
    if response.status_code == 401 and retry_auth and refresh_auth_session(config):
        return _authenticated_request(method, url, config=config, json=json, params=params, retry_auth=False)
    return response


def make_idempotency_key() -> str:
    return f"streamlit-{uuid.uuid4()}"


def _n8n_webhook(config: AppConfig, leaf: str) -> str:
    """Keep all Blueprint webhooks on the same configured n8n public base."""
    base = config.n8n_start_webhook_url.rsplit("/", 1)[0]
    return f"{base}/{leaf.lstrip('/')}"


def normalize_research_selection(selection: list[str] | None) -> list[str]:
    selected = selection or list(RESEARCH_MODULES)
    modules = [RESEARCH_MODULES.get(item, item) for item in selected]
    allowed = set(RESEARCH_MODULES.values())
    return list(dict.fromkeys(module for module in modules if module in allowed)) or list(RESEARCH_MODULES.values())


def start_blueprint(
    profile: Any,
    answers: dict[str, Any],
    *,
    idempotency_key: str,
    config: AppConfig | None = None,
) -> dict[str, Any]:
    config = config or load_config()
    modules = normalize_research_selection(answers.get("research_selection"))
    success_goal_types = {
        "First paying customers": "PAID_CUSTOMERS",
        "Replace my current income": "REDUCE_FINANCIAL_BURDEN",
        "Reliable side income": "SIDE_INCOME",
        "Launch a working product": "LAUNCH_READINESS",
        "Reach a revenue target": "PAID_CUSTOMERS",
        "Create measurable impact": "CUSTOM",
        "Build an audience or community": "CUSTOM",
    }
    profile_goal_types = {
        "side_income": "SIDE_INCOME", "small_business": "PAID_CUSTOMERS",
        "raise_money": "FUNDRAISING_READINESS", "startup": "VALIDATE_DEMAND",
        "just_explore": "VALIDATE_DEMAND", "get_job": "CUSTOM",
    }
    goal_type = success_goal_types.get(str(answers.get("success_type") or "")) or profile_goal_types.get(str(getattr(profile, "goal", "")), "VALIDATE_DEMAND")
    structured_goal = {
        "type": goal_type,
        "label": str(answers.get("success_type") or answers.get("goal") or getattr(profile, "goal", "Validate demand")),
        "success_definition": getattr(profile, "success_definition", ""),
    }
    constraints = {
        "requested_research": modules,
        "goal": structured_goal,
        "success_definition": getattr(profile, "success_definition", ""),
        "target_customer": getattr(profile, "target_customer", ""),
        "hours_per_week": getattr(profile, "hours_per_week", 0),
        "available_budget": getattr(profile, "money_available", 0),
        "launch_timeline": getattr(profile, "launch_timeline", ""),
        "current_work": getattr(profile, "current_work", ""),
        "constraints": list(getattr(profile, "constraints", []) or []),
        "onboarding_answers": answers,
    }
    payload = {
        "idempotency_key": idempotency_key,
        "idea_text": getattr(profile, "idea", ""),
        "optional_industry": answers.get("industry") or answers.get("idea_type"),
        "geography": getattr(profile, "location", "") or None,
        "requested_research": modules,
        "constraints": constraints,
    }
    response = _authenticated_request("POST", config.n8n_start_webhook_url, config=config, json=payload)
    body = _json_or_empty(response)
    if response.status_code not in {200, 202} or not isinstance(body, dict) or not body.get("ok"):
        raise _safe_error(response, "Blueprint could not start safely. Your onboarding answers are still available.")
    if not body.get("project_id") or not body.get("run_id"):
        raise BackendError("The start response did not include a project and run identifier.", code="SCHEMA")
    return body


def supabase_rpc(name: str, payload: dict[str, Any], config: AppConfig | None = None) -> Any:
    config = config or load_config()
    response = _authenticated_request(
        "POST",
        f"{config.supabase_url}/rest/v1/rpc/{name}",
        config=config,
        json=payload,
    )
    if response.status_code not in {200, 201, 204}:
        raise _safe_error(response, f"Blueprint could not load {name.replace('_', ' ')} safely.")
    return _json_or_empty(response)


def _supabase_table_select(
    table: str,
    params: dict[str, str],
    config: AppConfig | None = None,
) -> list[dict[str, Any]]:
    config = config or load_config()
    response = _authenticated_request(
        "GET",
        f"{config.supabase_url}/rest/v1/{table}",
        config=config,
        params=params,
    )
    if response.status_code != 200:
        raise _safe_error(response, f"Blueprint could not load your {table} safely.")
    payload = _json_or_empty(response)
    if not isinstance(payload, list):
        raise BackendError(f"The {table} response was not valid.", code="SCHEMA")
    return [item for item in payload if isinstance(item, dict)]


def load_recent_blueprints(config: AppConfig | None = None) -> list[dict[str, Any]]:
    """Return only the signed-in owner's recent active projects and latest run."""
    config = config or load_config()
    projects = _supabase_table_select(
        "projects",
        {
            "select": "id,idea_text,optional_industry,geography,constraints,current_status,created_at,updated_at",
            "current_status": "eq.ACTIVE",
            "order": "updated_at.desc",
            "limit": "20",
        },
        config,
    )
    runs = _supabase_table_select(
        "runs",
        {
            "select": "id,project_id,status,created_at,updated_at",
            "order": "updated_at.desc",
            "limit": "100",
        },
        config,
    )
    latest_by_project: dict[str, dict[str, Any]] = {}
    for run in runs:
        project_id = str(run.get("project_id") or "")
        if project_id and project_id not in latest_by_project:
            latest_by_project[project_id] = run
    return [
        {**project, "latest_run": latest_by_project.get(str(project.get("id") or ""))}
        for project in projects
    ]


def load_run_bundle(project_id: str, run_id: str, config: AppConfig | None = None) -> dict[str, Any]:
    config = config or load_config()
    calls = {
        "control_panel": ("get_founder_control_panel", {"p_run_id": run_id}),
        "snapshot": ("get_orchestration_run_snapshot", {"p_run_id": run_id}),
        "blueprint": ("get_progressive_blueprint_dashboard", {"p_project_id": project_id}),
        "research_context": ("get_supervisor_context", {"p_run_id": run_id}),
        "observability": ("get_run_observability", {"p_run_id": run_id}),
    }
    bundle: dict[str, Any] = {"project_id": project_id, "run_id": run_id, "loaded_at": time.time(), "errors": {}}
    for key, (rpc, payload) in calls.items():
        try:
            bundle[key] = supabase_rpc(rpc, payload, config)
        except BackendError as exc:
            bundle[key] = None
            bundle["errors"][key] = {"code": exc.code, "message": exc.message, "retryable": exc.retryable}
    return bundle


def hydrate_current_run(*, force: bool = False, max_age_seconds: int = 3) -> dict[str, Any] | None:
    project_id = st.session_state.get("backend_project_id")
    run_id = st.session_state.get("backend_run_id")
    if not project_id or not run_id:
        return None
    existing = st.session_state.get("backend_bundle")
    age = time.time() - float(st.session_state.get("backend_last_refresh_at") or 0)
    if existing and not force and age < max_age_seconds:
        return existing
    bundle = load_run_bundle(str(project_id), str(run_id))
    st.session_state["backend_bundle"] = bundle
    st.session_state["backend_last_refresh_at"] = time.time()
    return bundle


def resume_stalled_run(bundle: dict[str, Any] | None = None, config: AppConfig | None = None) -> dict[str, Any]:
    """Return an expired internal task lease to BP-00 without creating a new run."""
    config = config or load_config()
    bundle = bundle or st.session_state.get("backend_bundle") or {}
    context = bundle.get("research_context") or {}
    project = context.get("project") or {}
    tasks = [task for task in (context.get("orchestration_tasks") or []) if isinstance(task, dict)]
    profile_versions = [int(task.get("profile_version") or 0) for task in tasks]
    selected = [
        str(task.get("module_key"))
        for task in tasks
        if str(task.get("module_key")) in RESEARCH_MODULES.values()
    ]
    payload = {
        "project_id": st.session_state.get("backend_project_id"),
        "run_id": st.session_state.get("backend_run_id"),
        "profile_version": max(profile_versions or [1]),
        "idea_text": project.get("idea_text") or st.session_state.get("idea", ""),
        "requested_research": normalize_research_selection(selected),
        "correlation_id": f"streamlit-stale-recovery-{uuid.uuid4()}",
    }
    response = _authenticated_request(
        "POST", _n8n_webhook(config, "resume"), config=config, json=payload
    )
    body = _json_or_empty(response)
    if response.status_code not in {200, 202} or not isinstance(body, dict) or not body.get("ok"):
        raise _safe_error(response, "Blueprint could not recover the expired task lease safely.")
    return body


def resolve_founder_checkpoint(
    checkpoint_id: str,
    expected_state_version: int,
    decision: str,
    decision_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve a gate and, when permitted, dispatch the next stage through BP-00."""
    config = load_config()
    bundle = st.session_state.get("backend_bundle") or {}
    snapshot = bundle.get("snapshot") or {}
    run = snapshot.get("run") or {}
    context = bundle.get("research_context") or {}
    project = context.get("project") or {}
    dashboard = bundle.get("blueprint") or {}
    current = (dashboard.get("current_version") or {}).get("blueprint") or {}
    stored_constraints = project.get("constraints") if isinstance(project.get("constraints"), dict) else {}
    answers = stored_constraints.get("onboarding_answers") if isinstance(stored_constraints.get("onboarding_answers"), dict) else {}
    answers = answers or st.session_state.get("dialog_answers") or {}
    starting_position = current.get("starting_position") if isinstance(current.get("starting_position"), dict) else {}
    goal = answers.get("goal") or stored_constraints.get("goal") or starting_position.get("goal")
    idea_text = project.get("idea_text") or current.get("product_idea") or st.session_state.get("idea", "")
    profile = {
        **starting_position,
        "idea_text": idea_text,
        "goal": goal,
        "goal_status": "CONFIRMED" if goal and str(goal).strip().lower() not in {"not sure", "unknown"} else "MISSING",
        "constraints": {**stored_constraints, "onboarding_answers": answers},
    }
    payload = {
        "checkpoint_id": checkpoint_id,
        "expected_state_version": int(expected_state_version),
        "decision": decision,
        "decision_payload": decision_payload or {},
        "project_id": st.session_state.get("backend_project_id"),
        "run_id": st.session_state.get("backend_run_id"),
        "profile_version": int(run.get("profile_version") or current.get("profile_version") or 1),
        "idea_text": idea_text,
        "profile": profile,
        "requested_research": normalize_research_selection(answers.get("research_selection")),
        "correlation_id": f"streamlit-checkpoint-{uuid.uuid4()}",
    }
    response = _authenticated_request(
        "POST", _n8n_webhook(config, "checkpoint"), config=config, json=payload
    )
    result = _json_or_empty(response)
    if response.status_code not in {200, 202} or not isinstance(result, dict) or not result.get("ok"):
        raise _safe_error(response, "Blueprint could not apply the gate decision safely.")
    return result


def ask_research(
    message: str,
    *,
    project_id: str,
    run_id: str,
    thread_id: str | None = None,
    section_key: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
    config: AppConfig | None = None,
) -> dict[str, Any]:
    """Ask only against the current owner's retrieved research context."""
    config = config or load_config()
    payload = {
        "message": message.strip(),
        "project_id": project_id,
        "run_id": run_id,
        "correlation_id": f"streamlit-chat-{uuid.uuid4()}",
        "confirmed_command": False,
        "section_key": section_key,
        "conversation_history": (conversation_history or [])[-8:],
    }
    if thread_id:
        payload["thread_id"] = thread_id
    response = _authenticated_request(
        "POST", _n8n_webhook(config, "chat"), config=config, json=payload
    )
    body = _json_or_empty(response)
    if response.status_code not in {200, 202} or not isinstance(body, dict):
        raise _safe_error(response, "Ask this Research could not answer safely.")
    return body


def preview_research_rerun(
    target_module: str,
    *,
    project_id: str,
    source_run_id: str,
    idempotency_key: str,
    config: AppConfig | None = None,
) -> dict[str, Any]:
    config = config or load_config()
    response = _authenticated_request(
        "POST",
        _n8n_webhook(config, "rerun"),
        config=config,
        json={
            "command": "PREVIEW",
            "project_id": project_id,
            "source_run_id": source_run_id,
            "target_module": target_module,
            "idempotency_key": idempotency_key,
            "correlation_id": f"streamlit-rerun-preview-{uuid.uuid4()}",
        },
    )
    body = _json_or_empty(response)
    if response.status_code != 200 or not isinstance(body, dict) or not body.get("ok"):
        raise _safe_error(response, "Blueprint could not create the rerun impact preview safely.")
    return body


def resolve_research_rerun(
    rerun_request_id: str,
    expected_source_state_version: int,
    decision: str,
    *,
    config: AppConfig | None = None,
) -> dict[str, Any]:
    config = config or load_config()
    response = _authenticated_request(
        "POST",
        _n8n_webhook(config, "rerun"),
        config=config,
        json={
            "command": decision.upper(),
            "rerun_request_id": rerun_request_id,
            "expected_source_state_version": int(expected_source_state_version),
            "correlation_id": f"streamlit-rerun-resolve-{uuid.uuid4()}",
        },
    )
    body = _json_or_empty(response)
    if response.status_code not in {200, 202} or not isinstance(body, dict) or not body.get("ok"):
        raise _safe_error(response, "Blueprint could not apply the rerun decision safely.")
    return body
