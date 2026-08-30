"""Public client configuration for Blueprint Evidence Dev.

Only the Supabase publishable key and public n8n webhook URLs belong here.
Provider and service-role secrets must remain in n8n credentials.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import streamlit as st


class ConfigurationError(RuntimeError):
    """Raised when a required public application setting is missing."""


@dataclass(frozen=True)
class AppConfig:
    supabase_url: str
    supabase_publishable_key: str
    n8n_start_webhook_url: str
    request_timeout_seconds: int = 35


def _setting(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, "")
    except Exception:
        # Streamlit raises a framework-specific exception when no secrets file
        # exists. Environment variables remain the supported local fallback.
        value = ""
    return str(value or os.getenv(name, default)).strip()


def load_config(*, required: bool = True) -> AppConfig:
    config = AppConfig(
        supabase_url=_setting("SUPABASE_URL").rstrip("/"),
        supabase_publishable_key=_setting("SUPABASE_PUBLISHABLE_KEY"),
        n8n_start_webhook_url=_setting(
            "N8N_START_WEBHOOK_URL",
            "http://localhost:5679/webhook/blueprint/start",
        ),
        request_timeout_seconds=max(5, int(_setting("REQUEST_TIMEOUT_SECONDS", "35") or 35)),
    )
    missing = [
        name
        for name, value in (
            ("SUPABASE_URL", config.supabase_url),
            ("SUPABASE_PUBLISHABLE_KEY", config.supabase_publishable_key),
            ("N8N_START_WEBHOOK_URL", config.n8n_start_webhook_url),
        )
        if not value
    ]
    if required and missing:
        raise ConfigurationError(
            "Blueprint is not configured yet. Add these public settings privately: "
            + ", ".join(missing)
            + "."
        )
    return config
