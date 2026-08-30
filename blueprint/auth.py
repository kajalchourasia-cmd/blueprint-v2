"""Invisible Supabase guest authentication for the Streamlit client.

Blueprint deliberately has no evaluator-facing sign-in screen.  A visitor is
still represented by a real, isolated Supabase ``authenticated`` user so the
existing row-level-security policies remain the ownership boundary.
"""

from __future__ import annotations

import time
from typing import Any

import requests
import streamlit as st

from blueprint.config import AppConfig, ConfigurationError, load_config


AUTH_STATE_KEY = "bp_auth_session"
SENSITIVE_SESSION_KEYS = {
    AUTH_STATE_KEY,
    "backend_project_id",
    "backend_run_id",
    "backend_start_result",
    "backend_bundle",
    "backend_last_refresh_at",
    "backend_idempotency_key",
    "profile",
    "plan",
    "reality",
    "ledger",
    "projects",
    "idea",
    "dialog_answers",
    "dialog_question",
    "show_questions",
    "generating_blueprint",
    "generation_error",
    "owned_blueprints",
    "owned_blueprints_error",
    "bp_research_chat",
    "bp_research_thread_id",
    "bp_rerun_proposal",
    "bp_rerun_preview",
    "bp_rerun_idempotency_key",
    "bp_section_chats",
    "bp_section_threads",
    "bp_selected_section",
}


class AuthenticationError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


def _auth_headers(config: AppConfig, access_token: str | None = None) -> dict[str, str]:
    headers = {"apikey": config.supabase_publishable_key, "Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers


def _safe_auth_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    technical = str(payload.get("msg") or payload.get("message") or payload.get("error_description") or "")
    lowered = technical.lower()
    if response.status_code == 400 and ("invalid login" in lowered or "credentials" in lowered):
        return "The email or password is incorrect."
    if "email not confirmed" in lowered:
        return "Confirm the email address before signing in."
    if response.status_code == 429:
        return "Too many sign-in attempts. Wait briefly and try again."
    if response.status_code >= 500:
        return "Authentication is temporarily unavailable. Try again shortly."
    return technical or "Authentication could not be completed safely."


def _normalize_session(payload: dict[str, Any]) -> dict[str, Any]:
    expires_in = max(60, int(payload.get("expires_in") or 3600))
    return {
        "access_token": str(payload.get("access_token") or ""),
        "refresh_token": str(payload.get("refresh_token") or ""),
        "token_type": str(payload.get("token_type") or "bearer"),
        "expires_at": int(payload.get("expires_at") or (time.time() + expires_in)),
        "user": payload.get("user") or {},
    }


def sign_in(email: str, password: str, config: AppConfig | None = None) -> dict[str, Any]:
    config = config or load_config()
    try:
        response = requests.post(
            f"{config.supabase_url}/auth/v1/token?grant_type=password",
            headers=_auth_headers(config),
            json={"email": email.strip(), "password": password},
            timeout=(5, config.request_timeout_seconds),
        )
    except requests.RequestException as exc:
        raise AuthenticationError("Could not reach the authentication service.") from exc
    if response.status_code != 200:
        raise AuthenticationError(_safe_auth_message(response), status_code=response.status_code)
    session = _normalize_session(response.json())
    if not session["access_token"] or not session["refresh_token"]:
        raise AuthenticationError("Supabase returned an incomplete authentication session.")
    st.session_state[AUTH_STATE_KEY] = session
    return session


def sign_up(email: str, password: str, config: AppConfig | None = None) -> dict[str, Any]:
    config = config or load_config()
    try:
        response = requests.post(
            f"{config.supabase_url}/auth/v1/signup",
            headers=_auth_headers(config),
            json={"email": email.strip(), "password": password},
            timeout=(5, config.request_timeout_seconds),
        )
    except requests.RequestException as exc:
        raise AuthenticationError("Could not reach the authentication service.") from exc
    if response.status_code not in {200, 201}:
        raise AuthenticationError(_safe_auth_message(response), status_code=response.status_code)
    payload = response.json()
    if payload.get("access_token"):
        session = _normalize_session(payload)
        st.session_state[AUTH_STATE_KEY] = session
        return {"signed_in": True, "session": session}
    return {
        "signed_in": False,
        "message": "Account created. Confirm the email if Supabase email confirmation is enabled, then sign in.",
    }


def sign_in_anonymously(config: AppConfig | None = None) -> dict[str, Any]:
    """Create a unique guest user without collecting identity information.

    Supabase anonymous users receive ordinary access/refresh tokens and use the
    ``authenticated`` Postgres role.  This is intentionally different from
    exposing database access with the public ``anon`` role.
    """
    config = config or load_config()
    try:
        response = requests.post(
            f"{config.supabase_url}/auth/v1/signup",
            headers=_auth_headers(config),
            json={},
            timeout=(5, config.request_timeout_seconds),
        )
    except requests.RequestException as exc:
        raise AuthenticationError("Blueprint could not create a private guest workspace.") from exc
    if response.status_code not in {200, 201}:
        message = _safe_auth_message(response)
        if "anonymous" in message.lower() and ("disabled" in message.lower() or "not enabled" in message.lower()):
            message = "Anonymous demo access is not enabled in Supabase yet."
        raise AuthenticationError(message, status_code=response.status_code)
    session = _normalize_session(response.json())
    if not session["access_token"] or not session["refresh_token"] or not (session.get("user") or {}).get("id"):
        raise AuthenticationError("Supabase returned an incomplete guest session.")
    st.session_state[AUTH_STATE_KEY] = session
    return session


def ensure_guest_session(config: AppConfig | None = None) -> dict[str, Any]:
    """Return the current owner session or create one invisibly."""
    session = get_auth_session()
    if session is not None:
        return session
    return sign_in_anonymously(config)


def refresh_auth_session(config: AppConfig | None = None) -> dict[str, Any] | None:
    config = config or load_config()
    existing = st.session_state.get(AUTH_STATE_KEY) or {}
    refresh_token = str(existing.get("refresh_token") or "")
    if not refresh_token:
        return None
    try:
        response = requests.post(
            f"{config.supabase_url}/auth/v1/token?grant_type=refresh_token",
            headers=_auth_headers(config),
            json={"refresh_token": refresh_token},
            timeout=(5, config.request_timeout_seconds),
        )
    except requests.RequestException:
        return None
    if response.status_code != 200:
        return None
    session = _normalize_session(response.json())
    st.session_state[AUTH_STATE_KEY] = session
    return session


def get_auth_session(*, refresh_if_needed: bool = True) -> dict[str, Any] | None:
    session = st.session_state.get(AUTH_STATE_KEY)
    if not isinstance(session, dict) or not session.get("access_token"):
        return None
    if refresh_if_needed and int(session.get("expires_at") or 0) <= int(time.time()) + 90:
        session = refresh_auth_session()
        if session is None:
            clear_local_session()
    return session


def clear_local_session() -> None:
    for key in SENSITIVE_SESSION_KEYS:
        st.session_state.pop(key, None)


def sign_out(config: AppConfig | None = None) -> None:
    session = st.session_state.get(AUTH_STATE_KEY) or {}
    token = str(session.get("access_token") or "")
    try:
        config = config or load_config(required=False)
        if token and config.supabase_url and config.supabase_publishable_key:
            requests.post(
                f"{config.supabase_url}/auth/v1/logout",
                headers=_auth_headers(config, token),
                timeout=(5, min(15, config.request_timeout_seconds)),
            )
    except requests.RequestException:
        pass
    finally:
        clear_local_session()


def handle_logout_query() -> None:
    if str(st.query_params.get("logout", "")) == "1":
        sign_out()
        st.query_params.clear()
        st.rerun()


def current_user_email() -> str:
    session = get_auth_session(refresh_if_needed=False) or {}
    return str((session.get("user") or {}).get("email") or "Guest founder")


def render_auth_gate() -> bool:
    try:
        ensure_guest_session(load_config())
        return True
    except ConfigurationError as exc:
        st.error(str(exc))
        st.caption("Use `.streamlit/secrets.toml` locally or Advanced settings → Secrets in Streamlit Community Cloud.")
        return False
    except AuthenticationError as exc:
        st.error("Blueprint could not open a private demo workspace.")
        st.caption(str(exc))
        if st.button("Retry demo workspace", type="primary"):
            st.rerun()
        return False


def require_auth() -> dict[str, Any]:
    session = get_auth_session()
    if session is None:
        try:
            session = ensure_guest_session()
        except (AuthenticationError, ConfigurationError):
            st.switch_page("app.py")
            st.stop()
    return session
