"""Supabase email/password authentication for the Streamlit client."""

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
    return str((session.get("user") or {}).get("email") or "Founder")


def render_auth_gate() -> bool:
    if get_auth_session() is not None:
        return True
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"]{background:radial-gradient(circle at 80% 10%,#fff,transparent 31%),linear-gradient(145deg,#f7f7f4,#e4e6e2)}
        main .block-container{max-width:560px;padding-top:9vh}.auth-brand{font:500 11px 'DM Mono',monospace;letter-spacing:.13em;text-transform:uppercase}.auth-title{margin:35px 0 12px;font:500 55px/.92 'Space Grotesk',sans-serif;letter-spacing:-.075em}.auth-copy{margin-bottom:28px;color:#68706b;font:14px/1.5 'Space Grotesk',sans-serif}
        </style><div class="auth-brand">Blueprint Evidence Dev</div><h1 class="auth-title">Your research needs an owner.</h1><p class="auth-copy">Sign in so every idea, source, checkpoint, Blueprint version, and rerun stays isolated to your account.</p>
        """,
        unsafe_allow_html=True,
    )
    try:
        config = load_config()
    except ConfigurationError as exc:
        st.error(str(exc))
        st.caption("Use `.streamlit/secrets.toml` locally or Advanced settings → Secrets in Streamlit Community Cloud.")
        return False

    sign_in_tab, create_tab = st.tabs(["Sign in", "Create account"])
    with sign_in_tab:
        with st.form("bp_sign_in", clear_on_submit=False):
            email = st.text_input("Email address", key="bp_login_email")
            password = st.text_input("Password", type="password", key="bp_login_password")
            submitted = st.form_submit_button("Sign in →", type="primary", use_container_width=True)
        if submitted:
            if not email.strip() or not password:
                st.error("Enter both the email address and password.")
            else:
                try:
                    sign_in(email, password, config)
                    st.rerun()
                except AuthenticationError as exc:
                    st.error(str(exc))
    with create_tab:
        with st.form("bp_sign_up", clear_on_submit=False):
            new_email = st.text_input("Email address", key="bp_signup_email")
            new_password = st.text_input("Password", type="password", key="bp_signup_password")
            confirm_password = st.text_input("Confirm password", type="password", key="bp_signup_confirm")
            created = st.form_submit_button("Create account →", use_container_width=True)
        if created:
            if not new_email.strip() or "@" not in new_email:
                st.error("Enter a valid email address.")
            elif len(new_password) < 8:
                st.error("Use a password with at least eight characters.")
            elif new_password != confirm_password:
                st.error("The passwords do not match.")
            else:
                try:
                    result = sign_up(new_email, new_password, config)
                    if result.get("signed_in"):
                        st.rerun()
                    st.success(result.get("message", "Account created."))
                except AuthenticationError as exc:
                    st.error(str(exc))
    return False


def require_auth() -> dict[str, Any]:
    session = get_auth_session()
    if session is None:
        st.switch_page("app.py")
        st.stop()
    return session
