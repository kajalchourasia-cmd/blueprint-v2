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


def _render_css(states: dict[str, tuple[str, str]], selected: str) -> None:
    rail_rules = []
    for key, (kind, _) in states.items():
        selector = f".st-key-select_{key} button"
        if kind == "running":
            rail_rules.append(f"{selector}:before{{content:'';width:10px;height:10px;border:2px solid #b9d4c2;border-top-color:#27764a;border-radius:50%;animation:spin .8s linear infinite;position:absolute;right:12px;top:17px}}")
        elif kind == "done":
            rail_rules.append(f"{selector}:before{{content:'✓';display:grid;place-items:center;width:17px;height:17px;border-radius:50%;background:#2f8252;color:#fff;font:600 9px 'DM Mono';position:absolute;right:9px;top:14px}}")
        elif kind == "error":
            rail_rules.append(f"{selector}:before{{content:'!';display:grid;place-items:center;width:17px;height:17px;border-radius:50%;background:#f5d5cf;color:#9c3d31;font:600 9px 'DM Mono';position:absolute;right:9px;top:14px}}")
        elif kind in {"locked", "idle"}:
            rail_rules.append(f"{selector}:before{{content:'';width:8px;height:8px;border-radius:50%;background:#c7cbc8;position:absolute;right:13px;top:18px}}")
        else:
            rail_rules.append(f"{selector}:before{{content:'';width:8px;height:8px;border-radius:50%;background:#dfad56;box-shadow:0 0 0 4px #f8eedc;position:absolute;right:13px;top:18px}}")
        if kind in {"locked", "idle"}:
            rail_rules.append(f"{selector}{{background:#f0f1ef!important;color:#939994!important}}")
        elif kind == "done":
            rail_rules.append(f"{selector}{{color:#315a40!important}}")
        elif kind == "running":
            rail_rules.append(f"{selector}{{background:#f0f7f2!important;color:#244b33!important}}")
        elif kind == "error":
            rail_rules.append(f"{selector}{{background:#fcf1ee!important;color:#874038!important}}")
    rail_rules.append(f".st-key-select_{selected} button{{box-shadow:inset 3px 0 0 #2f8051,0 0 0 1px #cddbd0!important;background:#e5efe7!important;color:#1c3b28!important}}")
    state_css = "".join(rail_rules)
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600&display=swap');
:root{{--ink:#172019;--muted:#727a74;--line:#e2e5e2;--panel:#fff;--deep:#193f2a;--green:#2c7a4b;--ui:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}}
[data-testid="stAppViewContainer"],[data-testid="stHeader"]{{background:#fff}}[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stSidebar"],[data-testid="stSidebarNav"],#MainMenu,footer{{display:none!important}}[data-testid="stAppViewContainer"]>.main{{margin-left:0!important}}main .block-container{{width:100%!important;max-width:none!important;padding:0!important}}.st-key-bp_left_rail *,.st-key-bp_center_pane *,.st-key-bp_right_rail *{{font-family:var(--ui)!important}}[data-testid="stIconMaterial"],.material-symbols-rounded{{font-family:'Material Symbols Rounded'!important}}
.bp-wordmark{{display:flex;align-items:center;gap:9px;font:650 18px/1 var(--ui);letter-spacing:-.03em;margin:6px 4px 34px}}.bp-wordmark:before{{content:'';width:10px;height:10px;border-radius:50%;background:var(--green);box-shadow:0 0 0 5px rgba(44,122,75,.09)}}
.bp-project-title{{font:650 clamp(32px,3.1vw,48px)/1.02 var(--ui);letter-spacing:-.045em;margin:15px 0 7px;color:var(--ink)}}.bp-goal{{font:12px/1.45 var(--ui);color:var(--muted)}}.bp-live{{display:inline-flex;align-items:center;gap:7px;padding:7px 10px;border-radius:18px;background:#eef6f0;color:#356447;font:600 10px/1 var(--ui)}}.bp-live:before{{content:'';width:7px;height:7px;border-radius:50%;background:#43a467;animation:pulse 1.7s infinite}}
.kpi-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:22px 0 27px;background:transparent}}.kpi{{min-width:0;padding:13px 14px 12px;border:1px solid #e4e7e4;border-radius:12px;background:#fff;box-shadow:0 4px 14px rgba(24,34,27,.035)}}.kpi-label{{display:block;margin-bottom:6px;color:#687069;font:500 11px/1.2 var(--ui)}}.kpi-value-row{{display:flex;align-items:center;gap:7px;min-height:28px}}.kpi-value-row b{{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#172019;font:650 24px/1 var(--ui);letter-spacing:-.035em}}.kpi-badge{{display:inline-flex;align-items:center;gap:3px;flex:0 0 auto;padding:4px 7px;border-radius:9px;background:#e6f4ea;color:#287546;font:650 8px/1 var(--ui);text-transform:uppercase}}.kpi-badge:before{{content:'↗';font-size:8px}}.kpi-badge.watch{{background:#fff0e5;color:#a55228}}.kpi-badge.watch:before{{content:'!'}}.kpi-badge.neutral{{background:#f0f1f0;color:#707671}}.kpi-badge.neutral:before{{content:'·'}}.kpi-meta{{display:block;margin-top:6px;color:#989e99;font:9px/1.25 var(--ui)}}
.st-key-bp_left_rail,.st-key-bp_center_pane,.st-key-bp_right_rail{{height:100vh;min-height:720px;overflow-y:auto}}.st-key-bp_left_rail{{border:0;border-right:1px solid #e2e4e2;border-radius:0;padding:20px 14px 35px!important;background:#f7f7f6}}.st-key-bp_center_pane{{border:0;border-radius:0;padding:28px 34px 120px!important;background:#fff}}.st-key-bp_right_rail{{height:calc(100vh - 48px);min-height:0;margin:24px 18px 24px 0;padding:17px 15px!important;border:1px solid #e2e5e2;border-radius:18px;background:#fbfbfa;box-shadow:0 14px 38px rgba(25,36,28,.08)}}
.rail-heading{{margin:0 4px 18px;font:650 22px/1.02 var(--ui);letter-spacing:-.04em;color:#202722}}.rail-heading span{{color:#9aa09b}}.rail-heading small{{display:block;margin-bottom:8px;color:#7b837d;font:600 9px/1 var(--ui);letter-spacing:.02em;text-transform:uppercase}}
.rail-summary{{padding:12px 10px 11px;border:0;border-radius:11px;background:#fff}}.rail-summary-head{{display:flex;justify-content:space-between;align-items:center;font:500 10px/1.2 var(--ui);color:#59625b}}.rail-progress{{height:4px;margin:10px 0 9px;border-radius:8px;background:#e5e8e5;overflow:hidden}}.rail-progress i{{display:block;height:100%;border-radius:8px;background:#2f8051;transition:width .35s ease}}.rail-legend{{display:flex;gap:8px;flex-wrap:wrap;font:500 9px/1.2 var(--ui);color:#858c86}}.rail-legend span{{display:flex;align-items:center;gap:4px}}.rail-legend i{{width:6px;height:6px;border-radius:50%;background:#c8ccc9}}.rail-legend .live i{{background:#4a9b68;animation:pulse 1.6s infinite}}.rail-legend .done i{{background:#2f8051}}.st-key-bp_left_rail [data-testid="stExpander"]{{margin-top:14px;border:0!important;border-radius:0!important;background:transparent!important}}.st-key-bp_left_rail [data-testid="stExpander"] details{{border:0!important}}.st-key-bp_left_rail [data-testid="stExpander"] summary{{min-height:32px!important;padding:0 4px!important;color:#777e78!important;font:650 10px/1 var(--ui)!important;text-transform:uppercase}}.st-key-bp_left_rail [data-testid="stExpanderDetails"]{{padding:3px 0 2px!important}}.st-key-bp_left_rail [data-testid="stButton"]{{width:max-content;max-width:100%;margin:2px 0!important}}.st-key-bp_left_rail [data-testid="stButton"] button{{position:relative;width:auto!important;min-width:145px!important;min-height:36px!important;padding:7px 28px 7px 10px!important;border:0!important;border-radius:9px!important;background:transparent!important;color:#39423b!important;text-align:left!important;justify-content:flex-start!important;white-space:normal!important;font:500 12px/1.25 var(--ui)!important;box-shadow:none!important;transition:background .18s ease,transform .18s ease}}.st-key-bp_left_rail [data-testid="stButton"] button:hover{{transform:translateX(2px);background:#e9ece9!important}}
.plan-shortcuts{{display:grid;grid-template-columns:1fr;gap:8px;margin:10px 0 17px}}.plan-shortcut{{display:block;padding:13px;border:1px solid #e0e4e0;border-radius:13px;background:#fff;color:#253029;text-decoration:none!important;transition:.2s}}.plan-shortcut:hover{{transform:translateY(-2px);border-color:#c7d4ca;box-shadow:0 8px 20px rgba(30,48,36,.07)}}.plan-shortcut i{{display:inline-grid;place-items:center;width:24px;height:24px;border-radius:8px;background:#edf4ee;color:#2f754b;font:normal 12px var(--ui)}}.plan-shortcut b{{display:block;margin-top:10px;font:650 12px/1.2 var(--ui)}}.plan-shortcut small{{display:block;margin-top:3px;color:#808782;font:9px/1.35 var(--ui)}}
.section-kicker{{font:600 10px/1.2 var(--ui);color:#79827a;text-transform:uppercase}}.section-title{{font:650 31px/1.08 var(--ui);letter-spacing:-.035em;margin:7px 0 2px}}.section-summary{{margin:13px 0 21px;padding:16px 18px;border-left:3px solid var(--green);border-radius:0 12px 12px 0;background:#f1f6f1;font:14px/1.55 var(--ui)}}.state-banner{{display:flex;gap:13px;margin:22px 0;padding:18px;border:1px solid var(--line);border-radius:14px;background:#f6f8f5}}.state-spinner{{width:25px;height:25px;border:3px solid #cfdbd1;border-top-color:#267749;border-radius:50%;animation:spin .8s linear infinite}}.state-banner b{{display:block;font:600 14px var(--ui)}}.state-banner span{{font:11px/1.4 var(--ui);color:var(--muted)}}
.detail-heading{{margin:23px 0 9px;font:500 9px 'DM Mono';text-transform:uppercase;color:#6e776f}}.insight-list{{display:grid;gap:8px}}.insight{{padding:11px 13px;border:1px solid #e1e5e1;border-radius:12px;background:#fff;font:12px/1.48 'Space Grotesk'}}.empty-state{{display:grid;place-items:center;min-height:260px;text-align:center;color:#737d75}}.empty-state b{{display:block;font:500 22px 'Space Grotesk';color:#2a352d}}.empty-state p{{max-width:500px;font:12px/1.5 'Space Grotesk'}}
.verdict-hero{{margin:17px 0;padding:22px;border-radius:20px;background:linear-gradient(135deg,#193f2a,#286345);color:#f2f8f3}}.verdict-hero strong{{font:500 25px 'Space Grotesk'}}.verdict-hero p{{color:#c8dbce;font:12px/1.5 'Space Grotesk'}}.score-row{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}}.score-cell{{padding:12px;border:1px solid var(--line);border-radius:13px;background:#fff}}.score-cell b{{display:block;font:500 18px 'Space Grotesk'}}.score-cell span{{font:8px 'DM Mono';text-transform:uppercase;color:#7c857e}}
.st-key-empty_idea_composer{{position:relative;overflow:hidden;margin-top:22px;padding:27px 28px 22px!important;border:1px solid #dce3dd;border-radius:18px;background:#f7faf7;box-shadow:0 10px 30px rgba(35,65,45,.055)}}.st-key-empty_idea_composer:after{{content:'';position:absolute;z-index:0;right:-92px;top:-108px;width:260px;height:260px;border-radius:50%;border:1px solid rgba(48,126,78,.1);box-shadow:inset 0 0 0 42px rgba(48,126,78,.025),inset 0 0 0 84px rgba(48,126,78,.02);pointer-events:none}}.st-key-empty_idea_composer>*{{position:relative;z-index:1}}.st-key-empty_idea_composer.idea-attention{{animation:ideaFocus 1.05s ease}}.empty-eyebrow{{font:650 10px/1.2 var(--ui);text-transform:uppercase;color:#477157}}.empty-composer-title{{max-width:650px;margin:10px 0 8px;font:650 clamp(31px,3.5vw,48px)/1.02 var(--ui);letter-spacing:-.045em}}.empty-composer-copy{{max-width:690px;margin:0 0 17px;color:#617067;font:13px/1.55 var(--ui)}}.empty-steps{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:17px}}.empty-step{{padding:11px;border:1px solid #e0e5e0;border-radius:11px;background:#fff;font:10px/1.4 var(--ui);color:#657069}}.empty-step b{{display:block;margin-bottom:4px;color:#2e6042;font:650 9px var(--ui)}}.st-key-empty_idea_composer [data-testid="stForm"]{{border:0!important;padding:0!important}}.st-key-empty_idea_composer [data-testid="stTextAreaRootElement"]{{border:1px solid #cbd8ce!important;border-radius:12px!important;background:#fff!important;box-shadow:none!important}}.st-key-empty_idea_composer textarea{{min-height:112px!important;font:14px/1.5 var(--ui)!important}}.st-key-empty_idea_composer [data-testid="stFormSubmitButton"]{{display:flex!important;justify-content:flex-start!important}}.st-key-empty_idea_composer [data-testid="stFormSubmitButton"] button{{width:auto!important;min-width:205px!important;height:42px!important;padding:0 18px!important;border:0!important;border-radius:11px!important;background:#1d4c31!important;color:#fff!important;font:650 10px var(--ui)!important}}.empty-right-card{{margin-top:10px;padding:14px;border:1px solid #e3e6e3;border-radius:13px;background:#fff}}.empty-right-card h4{{margin:0 0 11px;font:650 13px var(--ui)}}.empty-right-row{{display:flex;gap:9px;align-items:flex-start;padding:9px 0;border-top:1px solid #edf0ed;color:#727b74;font:10px/1.4 var(--ui)}}.empty-right-row i{{flex:0 0 18px;height:18px;display:grid;place-items:center;border-radius:50%;background:#edf3ee;color:#397753;font:650 8px var(--ui)}}
.chat-divider{{margin:30px 0 12px;border-top:1px solid var(--line)}}.chat-guide{{margin:6px 0 10px;padding:14px 15px;border:1px solid #dbe2dc;border-radius:16px;background:linear-gradient(135deg,#f7faf7,#eef4ef)}}.chat-guide b{{display:block;font:500 14px 'Space Grotesk';letter-spacing:-.025em}}.chat-guide span{{display:block;margin-top:4px;color:#707a72;font:9px/1.45 'DM Mono'}}[class*="st-key-chat_starter_"] button{{min-height:36px!important;border:1px solid #d7dfd8!important;border-radius:13px!important;background:#fff!important;color:#405047!important;font:500 8px 'DM Mono'!important;box-shadow:none!important}}[class*="st-key-chat_starter_"] button:hover{{border-color:#6b9276!important;background:#edf5ef!important}}.st-key-bp_center_pane [data-testid="stChatInput"]{{position:sticky!important;bottom:0;z-index:20;background:#fbfcf9;padding-top:12px}}.stChatMessage{{background:#f3f6f2!important;border:1px solid #e1e6e1!important;border-radius:15px!important}}.chat-grounding{{margin-top:7px;color:#7b847d;font:7px 'DM Mono';letter-spacing:.05em;text-transform:uppercase}}.right-title{{font:500 9px 'DM Mono';text-transform:uppercase;margin:10px 4px}}[class*="st-key-bp_action_card_"]{{padding:15px 13px 11px!important;border:1px solid #dfe4df;border-radius:18px;background:#fff;box-shadow:0 10px 26px rgba(31,48,36,.06)}}.action-head{{display:flex;align-items:center;justify-content:space-between;gap:8px}}.action-head b{{font:600 13px 'Space Grotesk'}}.action-head span{{font:8px 'DM Mono';color:#8b918c}}.action-progress{{height:6px;margin:12px 0 10px;border-radius:8px;background:#e7e9e7;overflow:hidden}}.action-progress i{{display:block;height:100%;border-radius:8px;background:linear-gradient(90deg,#173b28,#3e9160);transition:width .35s ease}}[class*="st-key-bp_action_card_"] [data-testid="stCheckbox"]{{margin:0!important}}[class*="st-key-bp_action_card_"] [data-testid="stCheckbox"] label{{padding:7px 1px!important;align-items:flex-start!important;font:11px/1.4 'Space Grotesk'!important}}[class*="st-key-bp_action_card_"] [data-testid="stCheckbox"] label p{{font-size:11px!important}}[class*="st-key-bp_action_card_"] [data-testid="stCheckbox"] label:has(input:checked) p{{color:#9ba09c!important;text-decoration:line-through;text-decoration-thickness:1px}}[class*="st-key-bp_action_card_"] [data-testid="stCheckbox"] label:has(input:checked)>div:first-child{{animation:pop .25s ease-out}}.action-empty{{padding:10px 0;color:#8a908b;font:10px/1.45 'Space Grotesk'}}.st-key-bp_right_rail [data-testid="stExpander"]{{border:1px solid var(--line)!important;border-radius:14px!important;background:#fff!important;margin-top:9px}}.st-key-bp_right_rail [data-testid="stCheckbox"] input:checked+div{{background:#348557!important;animation:pop .25s ease-out}}[data-testid="stDialog"]>div{{max-width:720px!important;border-radius:25px!important;background:#f8faf7!important}}
{state_css}@keyframes spin{{to{{transform:rotate(360deg)}}}}@keyframes pulse{{50%{{opacity:.3}}}}@keyframes pop{{50%{{transform:scale(1.25)}}}}@keyframes ideaFocus{{0%,100%{{box-shadow:0 10px 30px rgba(35,65,45,.055)}}35%{{border-color:#58a274;box-shadow:0 0 0 6px rgba(54,139,87,.13),0 14px 36px rgba(35,65,45,.1)}}}}@media(max-width:1100px){{.kpi-grid{{grid-template-columns:repeat(2,1fr)}}.st-key-bp_left_rail,.st-key-bp_center_pane,.st-key-bp_right_rail{{height:auto;min-height:0}}.st-key-bp_right_rail{{margin:14px;border-radius:16px}}}}@media(max-width:620px){{.kpi-grid,.empty-steps{{grid-template-columns:1fr}}.st-key-bp_center_pane{{padding:22px 18px 100px!important}}}}
</style>""", unsafe_allow_html=True)


def _render_kpi_strip(score: float | None, coverage: int, risks: int, completion: int) -> None:
    if score is None:
        score_value, score_status, score_tone = "—", "Awaiting", "neutral"
    elif score >= 60:
        score_value, score_status, score_tone = f"{score:.0f}/100", "Proceed", ""
    elif score >= 40:
        score_value, score_status, score_tone = f"{score:.0f}/100", "Review", "watch"
    else:
        score_value, score_status, score_tone = f"{score:.0f}/100", "Rethink", "watch"
    coverage_status = "Strong" if coverage >= 70 else "Growing" if coverage >= 35 else "Sparse"
    coverage_tone = "" if coverage >= 70 else "watch" if coverage else "neutral"
    risk_status, risk_tone = ("Clear", "") if risks == 0 else ("Review", "watch")
    progress_status = "Complete" if completion >= 100 else "Active" if completion else "Starting"
    progress_tone = "" if completion else "neutral"
    metrics = (
        ("Decision score", score_value, score_status, score_tone, "Evidence-weighted verdict"),
        ("Evidence coverage", f"{coverage}%", coverage_status, coverage_tone, "Accepted research coverage"),
        ("Open risks", str(risks), risk_status, risk_tone, "Items needing resolution"),
        ("Blueprint progress", f"{completion}%", progress_status, progress_tone, "Current roadmap completion"),
    )
    cards = "".join(
        f'<div class="kpi"><span class="kpi-label">{html.escape(label)}</span><div class="kpi-value-row"><b>{html.escape(value)}</b>'
        f'<span class="kpi-badge {tone}">{html.escape(status)}</span></div><span class="kpi-meta">{html.escape(meta)}</span></div>'
        for label, value, status, tone, meta in metrics
    )
    st.markdown(f'<div class="kpi-grid">{cards}</div>', unsafe_allow_html=True)


def _render_left_rail(states: dict[str, tuple[str, str]], selected: str, *, interactive: bool) -> None:
    st.markdown('<div class="bp-wordmark">Blueprint</div><div class="rail-heading"><small>Your decision path</small>Roadmap <span>&amp; Progress</span></div>', unsafe_allow_html=True)
    done_count = sum(state[0] == "done" for state in states.values())
    running_count = sum(state[0] == "running" for state in states.values())
    waiting_count = len(states) - done_count - running_count
    rail_percent = round(100 * done_count / max(1, len(states)))
    st.markdown(
        f'<div class="rail-summary"><div class="rail-summary-head"><span>Overall progress</span><span>{done_count} of {len(states)}</span></div>'
        f'<div class="rail-progress"><i style="width:{rail_percent}%"></i></div><div class="rail-legend">'
        f'<span class="live"><i></i>{running_count} processing</span><span class="done"><i></i>{done_count} done</span><span><i></i>{waiting_count} waiting</span></div></div>',
        unsafe_allow_html=True,
    )
    for stage_number, (stage_name, sections) in enumerate(STAGES, 1):
        selected_in_stage = any(key == selected for key, _ in sections)
        with st.expander(stage_name, expanded=stage_number == 1 or selected_in_stage):
            for key, label in sections:
                state = states[key]
                if st.button(label, key=f"select_{key}", help=f"Status: {state[1]}"):
                    if interactive:
                        st.session_state["bp_selected_section"] = key
                    else:
                        st.session_state["bp_focus_idea"] = True
                    st.rerun()


def _render_plan_shortcuts() -> None:
    st.markdown(
        '<div class="right-title">Complete plan</div><div class="plan-shortcuts">'
        '<a class="plan-shortcut" href="/Your_Plan?view=blueprint" target="_self"><i>⌘</i><b>Open full Blueprint</b><small>Every stage, dependency, and unresolved decision.</small></a>'
        '<a class="plan-shortcut" href="/Your_Plan?view=financial" target="_self"><i>$</i><b>Financial plan</b><small>Capital, costs, pricing evidence, and readiness.</small></a></div>',
        unsafe_allow_html=True,
    )


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
    label = LABELS[key]
    st.markdown('<div class="chat-divider"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="chat-guide"><b>Ask Blueprint about {html.escape(label)}</b><span>Get a plain-language explanation, trace the supporting evidence, or turn an existing actionable into practical steps.</span></div>', unsafe_allow_html=True)
    chats = st.session_state.setdefault("bp_section_chats", {})
    threads = st.session_state.setdefault("bp_section_threads", {})
    history = chats.setdefault(key, [])
    for message in history[-8:]:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message.get("citations"):
                st.caption("Evidence references: " + ", ".join(message["citations"]))
            if message.get("suggested_actions"):
                st.caption("Suggested next move: " + " · ".join(_item_text(action) for action in message["suggested_actions"][:3]))
            if message.get("grounding_status"):
                st.markdown(f'<div class="chat-grounding">{html.escape(str(message["grounding_status"]).replace("_", " "))}</div>', unsafe_allow_html=True)
    starter_question = None
    if not history:
        starters = ("Explain this simply", "What evidence supports this?", "What should I do next?")
        starter_cols = st.columns(3)
        for index, (column, starter) in enumerate(zip(starter_cols, starters)):
            if column.button(starter, key=f"chat_starter_{key}_{index}", use_container_width=True):
                starter_question = starter
    typed_question = st.chat_input(f"Ask about {label.lower()}…", key=f"chat_{key}")
    question = typed_question or starter_question
    if question:
        conversation = [{"role": item["role"], "content": str(item["content"])} for item in history[-8:]]
        history.append({"role": "user", "content": question})
        try:
            with st.spinner("Blueprint is reading this section and its evidence…"):
                result = ask_research(
                    question,
                    project_id=str(st.session_state["backend_project_id"]),
                    run_id=str(st.session_state["backend_run_id"]),
                    thread_id=threads.get(key),
                    section_key=key,
                    conversation_history=conversation,
                )
            if result.get("thread_id"):
                threads[key] = result["thread_id"]
            history.append({
                "role": "assistant",
                "content": result.get("answer") or "I could not produce a safe answer from the available section context. Try asking what is missing or which evidence would resolve it.",
                "citations": _items(result.get("citations")),
                "suggested_actions": _items(result.get("suggested_actions")),
                "grounding_status": result.get("grounding_status"),
            })
        except BackendError as exc:
            history.append({"role": "assistant", "content": str(exc), "citations": []})
        st.rerun()


def _render_right(key: str, task: dict | None, output: dict, sources: list[dict]) -> None:
    st.markdown('<div class="right-title">Section companion</div>', unsafe_allow_html=True)
    actions = _items(output.get("contextual_actions"))
    completed = st.session_state.setdefault("bp_completed_actionables", {})
    scoped = set(_items(completed.get(key)))
    entries = []
    for index, action in enumerate(actions[:7]):
        text = _item_text(action)
        action_id = f"{key}:{index}:{text[:40]}"
        widget_key = f"action_{key}_{index}"
        checked = bool(st.session_state.get(widget_key, action_id in scoped))
        entries.append((checked, index, text, action_id, widget_key))
    completed_count = sum(item[0] for item in entries)
    total = len(entries)
    percent = round(100 * completed_count / total) if total else 0
    with st.container(key=f"bp_action_card_{key}"):
        st.markdown(f'<div class="action-head"><b>Actionables</b><span>{completed_count} of {total}</span></div><div class="action-progress"><i style="width:{percent}%"></i></div>', unsafe_allow_html=True)
        if entries:
            for checked_before, index, text, action_id, widget_key in sorted(entries, key=lambda item: item[0]):
                checked = st.checkbox(text, value=checked_before, key=widget_key)
                scoped.add(action_id) if checked else scoped.discard(action_id)
        else:
            st.markdown('<div class="action-empty">No founder action is required until this section has a valid result.</div>', unsafe_allow_html=True)
    completed[key] = sorted(scoped)
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
    gate_1 = st.session_state.get("bp_gate1_approved", False) or any(key in tasks for key in ("assumptions_risks", "offer_pricing", "validation_proof", "operating_model", "financial_readiness", "execution_readiness")); gate_2 = any(key in tasks for key in ("launch_distribution", "growth_optimization", "action_blueprint")); states = {key: _section_state(tasks.get(key), _stage_number(key), gate_1, gate_2) for _, sections in STAGES for key, _ in sections}; selected = st.session_state.setdefault("bp_selected_section", "customer_demand"); _render_css(states, selected)
    idea = _dict(context.get("project")).get("idea_text") or artifact.get("idea_text") or artifact.get("product_idea") or st.session_state.get("idea", "Your Blueprint"); title = _project_title(str(idea)); outputs = [_dict(task.get("output")) for task in tasks.values() if isinstance(task.get("output"), dict)]; risks = sum(len(_clean(output.get("risks"))) for output in outputs); score = _score(dashboard_verdict or latest_verdict); progress = [item for item in _items(dashboard.get("stage_progress")) if isinstance(item, dict)]; completion = round(sum(float(item.get("completion_percent") or 0) for item in progress) / max(1, len(progress))) if progress else round(100 * sum(state[0] == "done" for state in states.values()) / len(states)); coverage_value = (dashboard_verdict or latest_verdict).get("evidence_coverage"); coverage = round((float(coverage_value) * 100 if float(coverage_value) <= 1 else float(coverage_value))) if isinstance(coverage_value, (int, float)) else 0
    left, center, right = st.columns([1.05, 3.8, 1.35], gap=None)
    with left:
        with st.container(key="bp_left_rail"):
            _render_left_rail(states, selected, interactive=True)
    selected = st.session_state.get("bp_selected_section", selected); task = tasks.get(selected); state = states[selected]; output = _extract_output(task, artifact, selected)
    if selected == "research_verdict": output = {**output, **dashboard_verdict, **latest_verdict}
    sources = _flatten_sources(output, context)
    with center:
        with st.container(key="bp_center_pane"):
            st.markdown('<div class="bp-live">Live evidence workspace</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bp-project-title">{html.escape(title)}</div><div class="bp-goal">{html.escape(_goal_line(context))}</div>', unsafe_allow_html=True)
            _render_kpi_strip(score, coverage, risks, completion)
            if notice := st.session_state.pop("bp_transition_notice", None): st.success(str(notice))
            st.markdown(f'<div class="section-kicker">Stage {_stage_number(selected)} · {html.escape(state[1])}</div><div class="section-title">{html.escape(LABELS[selected])}</div>', unsafe_allow_html=True)
            _render_output(selected, output, checkpoint if selected == "research_verdict" else None) if output else _render_empty(selected, state); _render_chat(selected)
    with right:
        with st.container(key="bp_right_rail"):
            _render_plan_shortcuts()
            _render_right(selected, task, output, sources)
    if checkpoint:
        seen = f"bp_gate_seen_{checkpoint.get('checkpoint_id')}"
        if not st.session_state.get(seen):
            st.session_state[seen] = True; _gate_dialog(checkpoint, {**_extract_output(tasks.get("research_verdict"), artifact, "research_verdict"), **dashboard_verdict, **latest_verdict})


def _empty_workspace() -> None:
    states = {
        key: (("idle", "Not started") if stage_number == 1 else ("locked", "Waiting for prior gate"))
        for stage_number, (_, sections) in enumerate(STAGES, 1)
        for key, _ in sections
    }
    _render_css(states, "no_active_section")
    highlight_idea = bool(st.session_state.pop("bp_focus_idea", False))
    left, center, right = st.columns([1.05, 3.8, 1.35], gap=None)
    with left:
        with st.container(key="bp_left_rail"):
            _render_left_rail(states, "no_active_section", interactive=False)
    with center:
        with st.container(key="bp_center_pane"):
            st.markdown('<div class="bp-live">Ready when you are</div>', unsafe_allow_html=True)
            st.markdown('<div class="bp-project-title">Build your first Blueprint</div><div class="bp-goal">Start with the unfinished idea. Blueprint will ask for the context it needs.</div>', unsafe_allow_html=True)
            _render_kpi_strip(None, 0, 0, 0)
            if highlight_idea:
                st.markdown('<style>.st-key-empty_idea_composer{animation:ideaFocus 1.05s ease}</style>', unsafe_allow_html=True)
            with st.container(key="empty_idea_composer"):
                st.markdown('<div class="empty-eyebrow">Start here · one rough sentence is enough</div><div class="empty-composer-title">What are you trying to make real?</div><div class="empty-composer-copy">Describe the product, service, or business you are considering. After this, the short onboarding will capture your audience, goal, time, budget, and constraints before any research begins.</div>', unsafe_allow_html=True)
                with st.form("empty_dashboard_idea", border=False):
                    idea = st.text_area("Your idea", placeholder="For example: I want to build a fitness tracking app for busy professionals…", label_visibility="collapsed")
                    begin = st.form_submit_button("CONTINUE TO ONBOARDING  →", type="primary", use_container_width=False)
                st.markdown('<div class="empty-steps"><div class="empty-step"><b>01 · IDEA</b>Give Blueprint the unfinished version.</div><div class="empty-step"><b>02 · CONTEXT</b>Choose your goal, audience, and constraints.</div><div class="empty-step"><b>03 · RESEARCH</b>Customer, competitor, and market work begins.</div></div>', unsafe_allow_html=True)
            if begin:
                clean_idea = idea.strip()
                if len(clean_idea) < 10:
                    st.warning("Describe the idea in at least one clear sentence.")
                else:
                    for key in ("backend_idempotency_key", "generation_error", "backend_project_id", "backend_run_id", "backend_bundle"):
                        st.session_state.pop(key, None)
                    st.session_state["idea"] = clean_idea
                    st.session_state["dialog_answers"] = {"idea": clean_idea}
                    st.session_state["dialog_question"] = 0
                    st.session_state["show_questions"] = True
                    st.session_state["generating_blueprint"] = False
                    st.switch_page("app.py", query_params={"idea": clean_idea, "start": "1"})
    with right:
        with st.container(key="bp_right_rail"):
            _render_plan_shortcuts()
            st.markdown('<div class="right-title">What happens next</div><div class="empty-right-card"><h4>Your workspace will fill itself</h4><div class="empty-right-row"><i>1</i><span>Selected research streams appear as processing in the left rail.</span></div><div class="empty-right-row"><i>2</i><span>Completed sections become readable while other work continues.</span></div><div class="empty-right-row"><i>3</i><span>Sources, actionables, risks, and the verdict stay attached to their section.</span></div></div>', unsafe_allow_html=True)
            with st.expander("Sources · 0", expanded=False):
                st.caption("Sources appear after evidence has been accepted.")
            with st.expander("Background process", expanded=False):
                st.caption("No research run has started yet.")


def _map_node_content(output: dict, state: tuple[str, str], label: str) -> tuple[str, list[str]]:
    finding = output.get("executive_finding") or output.get("summary") or output.get("explanation")
    if finding:
        summary = re.sub(r"\s+", " ", str(finding)).strip()[:260]
    elif state[0] == "running":
        summary = "Evidence is being gathered and audited. Accepted findings will appear here automatically."
    elif state[0] == "error":
        summary = "The latest output was not promoted. This node needs input, retry, or human review."
    else:
        summary = f"{label} has not been identified yet. Its dependencies or evidence are not ready."
    details: list[str] = []
    for field in ("observed_signals", "recommendations", "milestones", "assumptions", "risks", "unknowns", "contextual_actions"):
        for item in _clean(output.get(field)):
            if item not in details:
                details.append(item[:150])
            if len(details) == 3:
                return summary, details
    return summary, details


def _render_full_blueprint_css() -> None:
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600&display=swap');
[data-testid="stAppViewContainer"],[data-testid="stHeader"]{background:#080b09;color:#eef4ef}[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stSidebar"],[data-testid="stSidebarNav"],#MainMenu,footer{display:none!important}[data-testid="stAppViewContainer"]>.main{margin-left:0!important}main .block-container{width:100%!important;max-width:1840px!important;padding:25px 44px 70px!important}
.map-shell{position:relative;min-height:100vh;color:#edf3ee;font-family:'Space Grotesk',sans-serif}.map-shell:before{content:'';position:fixed;inset:0;pointer-events:none;background-image:radial-gradient(circle,rgba(154,191,164,.18) 1px,transparent 1.2px);background-size:24px 24px;mask-image:linear-gradient(to bottom,#000,transparent 88%)}
.map-top{position:relative;z-index:2;display:flex;align-items:center;justify-content:space-between;padding-bottom:16px;border-bottom:1px solid #273029}.map-brand{font:500 9px 'DM Mono';letter-spacing:.12em;color:#b5c2b8}.map-brand b{color:#c8ff58}.map-actions{display:flex;gap:8px}.map-actions a{padding:10px 14px;border:1px solid #38433b;border-radius:18px;color:#c8d1ca;text-decoration:none;font:500 8px 'DM Mono';letter-spacing:.05em;transition:.2s}.map-actions a:hover{border-color:#b8ee52;color:#d8ff8a;transform:translateY(-1px)}.map-actions a.primary{border-color:#edf3ee;background:#edf3ee;color:#111713}
.map-hero{position:relative;z-index:1;display:grid;grid-template-columns:1.35fr .65fr;gap:50px;align-items:end;padding:43px 0 28px}.map-eyebrow{font:500 8px 'DM Mono';letter-spacing:.14em;color:#84a18b}.map-hero h1{margin:12px 0 0;font:500 clamp(48px,6vw,92px)/.88 'Space Grotesk';letter-spacing:-.082em}.map-hero h1 span{color:#758079}.map-intro{max-width:570px;margin:0;color:#a5afa7;font:13px/1.55 'Space Grotesk'}.map-intro b{color:#d4f579;font-weight:500}.map-metrics{position:relative;z-index:1;display:grid;grid-template-columns:repeat(4,1fr);gap:1px;margin-bottom:26px;border:1px solid #29332c;border-radius:18px;overflow:hidden;background:#29332c}.map-metric{padding:15px 17px;background:#111612}.map-metric b{display:block;font:500 22px 'Space Grotesk';letter-spacing:-.045em}.map-metric span{font:7px 'DM Mono';text-transform:uppercase;color:#78847a}
.map-lane{position:relative;z-index:1;margin-top:18px;padding:20px;border:1px solid #29332c;border-radius:25px;background:rgba(15,20,16,.86);overflow:hidden}.map-lane:before{content:'';position:absolute;left:44px;right:44px;top:116px;border-top:1px dashed #354138}.lane-head{display:flex;align-items:end;justify-content:space-between;gap:25px;margin-bottom:18px}.lane-index{color:#9dc065;font:500 8px 'DM Mono';letter-spacing:.12em}.lane-head h2{margin:6px 0 0;font:500 27px 'Space Grotesk';letter-spacing:-.055em}.lane-head p{max-width:520px;margin:0;color:#7f8b81;font:10px/1.45 'DM Mono'}.map-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px}.map-node{position:relative;min-height:236px;padding:17px;border:1px solid #303b33;border-radius:19px;background:#141a15;color:#e9f0ea;text-decoration:none!important;animation:nodeIn .42s both;transition:transform .22s ease,border-color .22s ease,background .22s ease}.map-node:not(:nth-child(3n)):after{content:'→';position:absolute;z-index:4;right:-14px;top:50%;width:14px;color:#9eb2a2;font:13px 'DM Mono';text-align:center}.map-node:hover{z-index:3;transform:translateY(-4px);border-color:#738979;background:#182019}.map-node:before{content:'';position:absolute;left:17px;top:-1px;width:38px;height:3px;border-radius:0 0 5px 5px;background:#59645c}.map-node.identified:before{background:#b9ed57}.map-node.processing:before{background:#75c3ff;animation:linePulse 1.25s infinite}.map-node.review:before{background:#ff927e}.map-node.unidentified{border-style:dashed;color:#a4ada6;background:#111512}.node-top{display:flex;align-items:center;justify-content:space-between}.node-number{font:8px 'DM Mono';color:#707b72}.node-status{display:inline-flex;align-items:center;gap:6px;font:7px 'DM Mono';letter-spacing:.06em;text-transform:uppercase;color:#869188}.node-status:before{content:'';width:7px;height:7px;border-radius:50%;background:#59635b}.identified .node-status{color:#b8d982}.identified .node-status:before{background:#a6dd47;box-shadow:0 0 0 4px rgba(166,221,71,.08)}.processing .node-status{color:#9dd4fa}.processing .node-status:before{background:#70c2fb;animation:mapPulse 1.3s infinite}.review .node-status{color:#f7aa9b}.review .node-status:before{background:#ee7e68}.map-node h3{margin:26px 0 8px;font:500 20px 'Space Grotesk';letter-spacing:-.045em;color:#f2f6f2}.map-node p{min-height:58px;margin:0;color:#929d94;font:10px/1.48 'Space Grotesk'}.node-points{display:grid;gap:5px;margin-top:15px}.node-point{display:flex;gap:7px;padding-top:6px;border-top:1px solid #252d27;color:#b9c2bb;font:8px/1.38 'DM Mono'}.node-point:before{content:'↳';color:#8fb859}.node-awaiting{margin-top:16px;padding:9px 10px;border:1px dashed #303832;border-radius:10px;color:#6e7870;font:8px/1.4 'DM Mono'}
.finance-strip{position:relative;z-index:1;display:grid;grid-template-columns:1.2fr repeat(3,.55fr);gap:1px;margin-top:18px;border:1px solid #3a3630;border-radius:23px;overflow:hidden;background:#3a3630}.finance-lead,.finance-cell{padding:22px;background:linear-gradient(145deg,#191b18,#221f1a)}.finance-lead{background:linear-gradient(125deg,#39251f,#6f4635)}.finance-lead small,.finance-cell small{font:7px 'DM Mono';letter-spacing:.08em;text-transform:uppercase;color:#beab9c}.finance-lead h2{margin:22px 0 6px;font:500 25px 'Space Grotesk';letter-spacing:-.055em}.finance-lead p{margin:0;color:#cfbcae;font:10px/1.5 'DM Mono'}.finance-cell b{display:block;margin-top:25px;font:500 22px 'Space Grotesk';letter-spacing:-.045em}.finance-cell span{display:block;margin-top:5px;color:#8f9890;font:8px/1.4 'DM Mono'}.finance-link{display:inline-block;margin-top:14px;color:#e4f2dd;font:8px 'DM Mono'}
.map-legend{display:flex;gap:18px;flex-wrap:wrap;margin:24px 0 0;color:#7c877e;font:8px 'DM Mono'}.map-legend span{display:flex;align-items:center;gap:7px}.map-legend i{width:8px;height:8px;border-radius:50%;background:#59635b}.map-legend .l1 i{background:#a6dd47}.map-legend .l2 i{background:#70c2fb}.map-legend .l3 i{background:#ee7e68}
@keyframes nodeIn{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}@keyframes mapPulse{50%{opacity:.25;box-shadow:0 0 0 6px rgba(112,194,251,.08)}}@keyframes linePulse{50%{opacity:.3}}
@media(max-width:1000px){main .block-container{padding:18px!important}.map-hero{grid-template-columns:1fr}.map-grid{grid-template-columns:repeat(2,1fr)}.map-node:not(:nth-child(3n)):after{display:none}.finance-strip{grid-template-columns:1fr 1fr}.map-metrics{grid-template-columns:repeat(2,1fr)}}@media(max-width:650px){.map-grid,.finance-strip{grid-template-columns:1fr}.map-hero h1{font-size:48px}.map-actions a:not(.primary){display:none}}
</style>""", unsafe_allow_html=True)


def render_full_blueprint() -> None:
    """Render a separate, dynamic system map of the founder's entire Blueprint."""
    _render_full_blueprint_css()
    bundle: dict = {}
    load_error = ""
    if st.session_state.get("backend_run_id"):
        try:
            bundle = hydrate_current_run(force=True) or {}
        except BackendError as exc:
            load_error = str(exc)
    context = _dict(bundle.get("research_context"))
    dashboard = _dict(bundle.get("blueprint"))
    artifact = _dict(_dict(dashboard.get("current_version")).get("blueprint"))
    tasks = _task_map(bundle)
    gate_1 = any(key in tasks for key in ("assumptions_risks", "offer_pricing", "validation_proof", "operating_model", "financial_readiness", "execution_readiness"))
    gate_2 = any(key in tasks for key in ("launch_distribution", "growth_optimization", "action_blueprint"))
    states = {key: _section_state(tasks.get(key), _stage_number(key), gate_1, gate_2) for _, sections in STAGES for key, _ in sections}
    project = _dict(context.get("project"))
    idea = project.get("idea_text") or artifact.get("idea_text") or artifact.get("product_idea") or st.session_state.get("idea", "Your Product Idea")
    title = _project_title(str(idea))
    outputs = {key: _extract_output(tasks.get(key), artifact, key) for _, sections in STAGES for key, _ in sections}
    discovered = sum(bool(output) or states[key][0] == "done" for key, output in outputs.items())
    processing = sum(state[0] == "running" for state in states.values())
    unresolved = len(states) - discovered
    constraints = _dict(project.get("constraints"))
    answers = _dict(constraints.get("onboarding_answers")) or _dict(st.session_state.get("dialog_answers"))
    capital = answers.get("budget") or answers.get("capital_available") or "Not identified"
    revenue = answers.get("revenue_model") or "Not identified"
    pricing = outputs.get("offer_pricing", {}).get("pricing_model") or outputs.get("offer_pricing", {}).get("recommendation") or "Not identified"
    status_map = {
        "done": ("identified", "Identified"),
        "running": ("processing", "Processing"),
        "error": ("review", "Needs review"),
        "ready": ("unidentified", "Not identified"),
        "locked": ("unidentified", "Not identified"),
        "idle": ("unidentified", "Not identified"),
    }
    stage_descriptions = {
        1: "Establish the customer, market, competitive reality, and the first evidence-backed verdict.",
        2: "Turn accepted research into assumptions, an offer, validation design, operating logic, and financial boundaries.",
        3: "Translate proven decisions into an advisory MVP, distribution path, growth prerequisites, and final action map.",
    }
    sequence = 0
    lanes: list[str] = []
    for stage_number, (stage_name, sections) in enumerate(STAGES, 1):
        cards: list[str] = []
        for key, label in sections:
            sequence += 1
            kind, status_label = status_map.get(states[key][0], ("unidentified", "Not identified"))
            summary, details = _map_node_content(outputs[key], states[key], label)
            detail_html = "".join(f'<div class="node-point">{html.escape(item)}</div>' for item in details)
            if not detail_html:
                detail_html = '<div class="node-awaiting">Awaiting accepted evidence and the required prior decision.</div>'
            cards.append(
                f'<a class="map-node {kind}" style="animation-delay:{sequence * 0.035:.3f}s" href="/Your_Plan?section={html.escape(key)}" target="_self">'
                f'<div class="node-top"><span class="node-number">{sequence:02d}</span><span class="node-status">{status_label}</span></div>'
                f'<h3>{html.escape(label)}</h3><p>{html.escape(summary)}</p><div class="node-points">{detail_html}</div></a>'
            )
        clean_name = stage_name.split("·", 1)[-1].strip()
        lanes.append(
            f'<section class="map-lane"><div class="lane-head"><div><div class="lane-index">STAGE {stage_number:02d} / {html.escape(clean_name.upper())}</div>'
            f'<h2>{html.escape(clean_name)}</h2></div><p>{html.escape(stage_descriptions[stage_number])}</p></div><div class="map-grid">{"".join(cards)}</div></section>'
        )
    load_notice = f'<div class="node-awaiting">Live data could not refresh: {html.escape(load_error)}</div>' if load_error else ""
    st.markdown(
        f'''<main class="map-shell"><header class="map-top"><div class="map-brand"><b>⌘</b> BLUEPRINT / CONNECTED DECISION PATH</div><div class="map-actions"><a href="/" target="_self">HOME</a><a class="primary" href="/Your_Plan" target="_self">DASHBOARD</a></div></header>
        <section class="map-hero"><div><div class="map-eyebrow">IDEA → EVIDENCE → DECISION → ADVISORY PLAN</div><h1>{html.escape(title)} <span>Blueprint</span></h1></div><p class="map-intro"><b>Follow the connected path.</b> Identified cards contain accepted work from this run. Gray cards are deliberately marked as not identified until their evidence or decision gate exists.</p></section>
        <div class="map-metrics"><div class="map-metric"><b>{discovered}/{len(states)}</b><span>Parts identified</span></div><div class="map-metric"><b>{processing}</b><span>Processing now</span></div><div class="map-metric"><b>{unresolved}</b><span>Still unidentified</span></div><div class="map-metric"><b style="font:500 12px/1.3 'DM Mono'">{html.escape(_goal_line(context).replace("Goal: ", ""))}</b><span>Founder goal</span></div></div>{load_notice}{"".join(lanes)}
        <section class="finance-strip"><div class="finance-lead"><small>Financial plan / evidence boundary</small><h2>Know the cost of the next commitment.</h2><p>Blueprint separates founder inputs from researched evidence and never invents revenue, pricing, conversion, or willingness to pay.</p><a class="finance-link" href="/Your_Plan?view=financial" target="_self">OPEN FINANCIAL PLAN →</a></div><div class="finance-cell"><small>Capital available</small><b>{html.escape(str(capital))}</b><span>Founder-provided constraint</span></div><div class="finance-cell"><small>Revenue model</small><b>{html.escape(str(revenue))}</b><span>Unidentified until provided or supported</span></div><div class="finance-cell"><small>Pricing direction</small><b>{html.escape(_item_text(pricing)[:80])}</b><span>Requires customer or market evidence</span></div></section>
        <div class="map-legend"><span class="l1"><i></i>Identified from the current Blueprint</span><span class="l2"><i></i>Processing now</span><span class="l3"><i></i>Needs input or review</span><span><i></i>Not identified yet</span></div></main>''',
        unsafe_allow_html=True,
    )


def render_financial_plan() -> None:
    """Render the founder's financial boundaries without fabricating commercial proof."""
    bundle: dict = {}
    if st.session_state.get("backend_run_id"):
        try:
            bundle = hydrate_current_run(force=True) or {}
        except BackendError:
            bundle = {}
    context = _dict(bundle.get("research_context"))
    tasks = _task_map(bundle)
    output = _dict(_dict(tasks.get("financial_readiness")).get("output"))
    project = _dict(context.get("project"))
    answers = _dict(_dict(project.get("constraints")).get("onboarding_answers")) or _dict(st.session_state.get("dialog_answers"))
    idea = project.get("idea_text") or st.session_state.get("idea", "Your Product Idea")
    fields = [
        ("Capital available", answers.get("budget") or answers.get("capital_available"), "Founder-provided constraint"),
        ("Time available", answers.get("time_available") or answers.get("weekly_time"), "Founder-provided constraint"),
        ("Revenue model", answers.get("revenue_model") or output.get("revenue_model"), "Requires an explicit business-model decision"),
        ("Pricing evidence", output.get("pricing_model") or output.get("pricing_direction"), "Requires customer or market evidence"),
        ("Runway", output.get("runway") or output.get("runway_months"), "Calculated only from provided costs and capital"),
        ("Readiness", output.get("readiness") or output.get("status"), "Current financial decision state"),
    ]
    cards = "".join(
        f'<article class="fp-card"><small>{html.escape(label)}</small><b>{html.escape(_item_text(value)[:110]) if value not in (None, "", []) else "Not identified"}</b><span>{html.escape(note)}</span></article>'
        for label, value, note in fields
    )
    sections = []
    for title, field in (("Cost assumptions", "assumptions"), ("Scenarios", "scenarios"), ("Financial risks", "risks"), ("Next decisions", "recommendations")):
        values = _clean(output.get(field))[:6]
        rows = "".join(f'<li>{html.escape(value)}</li>' for value in values) or '<li class="unknown">Not identified yet — this will fill after Stage 2 has accepted inputs and evidence.</li>'
        sections.append(f'<article class="fp-section"><small>{html.escape(title)}</small><ul>{rows}</ul></article>')
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600&display=swap');
[data-testid="stAppViewContainer"],[data-testid="stHeader"]{background:linear-gradient(145deg,#e8eeea,#f1dfd4 62%,#cf9f87);color:#262b27}[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stSidebar"],[data-testid="stSidebarNav"],#MainMenu,footer{display:none!important}[data-testid="stAppViewContainer"]>.main{margin-left:0!important}main .block-container{width:100%!important;max-width:1500px!important;padding:28px 48px 80px!important}.fp-shell{font-family:'Space Grotesk',sans-serif}.fp-top{display:flex;align-items:center;justify-content:space-between;padding-bottom:17px;border-bottom:1px solid rgba(45,53,47,.2)}.fp-brand{font:500 9px 'DM Mono';letter-spacing:.1em}.fp-top a{padding:10px 14px;border:1px solid rgba(37,46,39,.25);border-radius:18px;color:#29322b;text-decoration:none;font:8px 'DM Mono'}.fp-hero{display:grid;grid-template-columns:1.2fr .8fr;gap:45px;padding:58px 0 35px}.fp-hero small,.fp-card small,.fp-section small{font:500 8px 'DM Mono';letter-spacing:.1em;text-transform:uppercase;color:#6a766e}.fp-hero h1{margin:13px 0 8px;font:500 clamp(55px,7vw,100px)/.86 'Space Grotesk';letter-spacing:-.085em}.fp-hero h1 span{color:#8f7770}.fp-hero p{align-self:end;margin:0;color:#626d65;font:14px/1.55 'Space Grotesk'}.fp-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.fp-card{position:relative;overflow:hidden;min-height:165px;padding:20px;border:1px solid rgba(49,59,51,.2);border-radius:22px;background:rgba(255,255,255,.45);backdrop-filter:blur(16px);transition:.22s}.fp-card:hover{transform:translateY(-3px);background:rgba(255,255,255,.62);box-shadow:0 18px 35px rgba(74,52,43,.08)}.fp-card:after{content:'';position:absolute;right:-32px;bottom:-45px;width:110px;height:110px;border-radius:50%;background:rgba(173,116,88,.1)}.fp-card b{position:relative;z-index:1;display:block;margin-top:31px;font:500 23px/1.08 'Space Grotesk';letter-spacing:-.055em}.fp-card span{position:relative;z-index:1;display:block;margin-top:8px;color:#727c74;font:9px/1.45 'DM Mono'}.fp-sections{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:18px}.fp-section{min-height:190px;padding:22px;border:1px solid rgba(49,59,51,.18);border-radius:22px;background:rgba(247,247,241,.62)}.fp-section ul{display:grid;gap:8px;margin:19px 0 0;padding:0;list-style:none}.fp-section li{padding:10px 12px;border-radius:12px;background:rgba(255,255,255,.55);font:11px/1.45 'Space Grotesk'}.fp-section li:before{content:'↳';margin-right:8px;color:#8c5f4b}.fp-section li.unknown{color:#7f8880;font-family:'DM Mono';font-size:9px}.fp-rule{margin-top:18px;padding:17px 20px;border-radius:17px;background:#28342c;color:#eaf0eb;font:10px/1.5 'DM Mono'}.fp-rule b{color:#d7f483}.fp-actions{display:flex;gap:8px;margin-top:18px}.fp-actions a{padding:12px 15px;border-radius:16px;background:#26342b;color:#f0f4f1;text-decoration:none;font:8px 'DM Mono'}.fp-actions a.secondary{border:1px solid rgba(39,50,42,.24);background:rgba(255,255,255,.4);color:#29342c}@media(max-width:850px){main .block-container{padding:20px!important}.fp-hero{grid-template-columns:1fr}.fp-grid,.fp-sections{grid-template-columns:1fr}.fp-hero h1{font-size:58px}}
</style>""", unsafe_allow_html=True)
    st.markdown(
        f'''<main class="fp-shell"><header class="fp-top"><div class="fp-brand">BLUEPRINT / FINANCIAL PLAN</div><a href="/Your_Plan" target="_self">BACK TO DASHBOARD</a></header><section class="fp-hero"><div><small>Founder constraints → evidence → financial decision</small><h1>Financial <span>Plan</span></h1></div><p>Financial readiness for <b>{html.escape(_project_title(str(idea)))}</b>. Blank evidence stays visibly unidentified; Blueprint does not turn estimates into facts.</p></section><div class="fp-grid">{cards}</div><div class="fp-sections">{"".join(sections)}</div><div class="fp-rule"><b>Evidence boundary:</b> projected revenue, conversion, willingness to pay, and runway are withheld until the required founder inputs or accepted research exist.</div><div class="fp-actions"><a href="/Your_Plan?section=financial_readiness" target="_self">OPEN FINANCIAL READINESS →</a><a class="secondary" href="/Your_Plan?view=blueprint" target="_self">VIEW FULL BLUEPRINT</a></div></main>''',
        unsafe_allow_html=True,
    )


@st.fragment(run_every=4)
def _live_workspace() -> None:
    _workspace_body()


def render_blueprint_workspace() -> None:
    if not st.session_state.get("backend_run_id"):
        _empty_workspace(); return
    _live_workspace()
