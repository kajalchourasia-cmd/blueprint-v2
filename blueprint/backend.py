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
        message, code = "Your session has expired. Sign in again.", "UNAUTHENTICATED"
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
        raise BackendError("Sign in before continuing.", code="UNAUTHENTICATED", status_code=401)
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
    constraints = {
        "requested_research": modules,
        "goal": getattr(profile, "goal", None),
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


def resolve_founder_checkpoint(
    checkpoint_id: str,
    expected_state_version: int,
    decision: str,
    decision_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = supabase_rpc(
        "resolve_founder_checkpoint",
        {
            "p_checkpoint_id": checkpoint_id,
            "p_expected_state_version": int(expected_state_version),
            "p_decision": decision,
            "p_decision_payload": decision_payload or {},
        },
    )
    if not isinstance(result, dict):
        raise BackendError("The checkpoint response was not valid.", code="SCHEMA")
    return result
