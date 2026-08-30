"""Shared floating navigation for Blueprint support pages."""

from __future__ import annotations

import streamlit as st


def render_app_navigation(active: str = "") -> None:
    items = [
        ("home", "/", "⌂", "Home"),
        ("dashboard", "/Your_Plan", "▦", "Dashboard"),
        ("blueprint", "/Your_Plan?view=blueprint", "⌘", "Full Blueprint"),
        ("inputs", "/Inputs", "≋", "User inputs"),
        ("data", "/Data_Library", "◫", "Data library"),
        ("case", "/Case_Study", "¶", "Case study"),
    ]
    links = "".join(
        f'<a class="{"active" if key == active else ""}" href="{href}" aria-label="{label}"><span class="nav-glyph">{icon}</span><small>{label}</small></a>'
        for key, href, icon, label in items
    )
    st.markdown(
        f"""
<style>
.bp-global-nav{{position:fixed;z-index:999;left:17px;top:50%;transform:translateY(-50%);width:54px;padding:8px 7px;border:1px solid rgba(35,39,36,.16);border-radius:28px;background:rgba(251,252,249,.84);backdrop-filter:blur(18px);box-shadow:0 18px 45px rgba(27,32,28,.13)}}.bp-global-nav a{{width:38px;height:38px;margin:3px 0;display:grid;place-items:center;position:relative;border-radius:50%;color:#818681;text-decoration:none;transition:.2s}}.bp-global-nav a:hover,.bp-global-nav a.active{{background:#202321;color:#fff}}.bp-global-nav .nav-glyph{{font:18px/1 Arial,sans-serif}}.bp-global-nav a small{{position:absolute;left:49px;padding:7px 9px;border-radius:9px;background:#202321;color:#fff;font:8px 'DM Mono',monospace;white-space:nowrap;opacity:0;transform:translateX(-4px);pointer-events:none;transition:.2s}}.bp-global-nav a:hover small{{opacity:1;transform:none}}@media(max-width:720px){{.bp-global-nav{{left:50%;top:auto;bottom:10px;transform:translateX(-50%);width:auto;display:flex;padding:5px 8px}}.bp-global-nav a{{margin:0 2px}}.bp-global-nav a small{{display:none}}}}
</style><nav class="bp-global-nav">{links}</nav>
""",
        unsafe_allow_html=True,
    )
