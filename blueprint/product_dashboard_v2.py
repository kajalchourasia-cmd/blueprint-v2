"""Interactive Blueprint dashboard backed by profile, plan, and evidence CSV data."""

from __future__ import annotations

import csv
import html
import re
from pathlib import Path
from typing import Any

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]


def _get(source: Any, key: str, default: Any = None) -> Any:
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def _rows(name: str) -> list[dict[str, str]]:
    path = ROOT / "data" / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _title(idea: str) -> str:
    clean = re.sub(r"\s+", " ", idea.strip()).rstrip(".!?")
    clean = re.sub(r"^(i\s+(?:want|would like|plan|hope)\s+to|my idea is to|we want to)\s+", "", clean, flags=re.I)
    clean = re.sub(r"^(build|create|launch|start|open)\s+(?:an?\s+)?", "", clean, flags=re.I)
    return " ".join(clean.split()[:6]).title() or "Plant Analyzer App"


def _archetype(profile: Any, idea: str) -> str:
    idea_type = str(_get(profile, "idea_type", "other"))
    if idea_type in {"saas", "ai_product", "marketplace", "creator", "consumer_product"} or any(word in idea.lower() for word in ("app", "software", "platform", "ai ")):
        return "digital_product"
    return "online_business"


def _matched_idea(idea: str) -> dict[str, str]:
    """Return the closest planning prior without treating it as observed evidence."""
    words = set(re.findall(r"[a-z0-9]+", idea.lower()))
    rows = _rows("blueprint_idea_master.csv")
    if not rows:
        return {}
    return max(
        rows,
        key=lambda row: len(words & set(re.findall(r"[a-z0-9]+", f'{row["idea_title"]} {row["idea_description"]}'.lower()))),
    )


def _number(value: str | int | float | None, default: float = 0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def _default_steps() -> list[dict[str, Any]]:
    return [
        {"number": 1, "name": "Define the customer problem", "what_to_do": "Turn the idea into one falsifiable statement about who has the problem, when it occurs, and what they do today.", "why_it_matters": "A precise problem statement prevents solution-first interviews.", "done_criteria": "One sentence names the user, trigger, current workaround, and measurable pain.", "estimated_time_days": 3, "estimated_hours": 4, "step_type": "research"},
        {"number": 2, "name": "Interview 10 target users", "what_to_do": "Recruit ten people who recently experienced the problem and ask about the last real occurrence.", "why_it_matters": "Past behavior is stronger evidence than opinions about a future product.", "done_criteria": "Ten notes capture triggers, workarounds, cost, frequency, and exact customer language.", "estimated_time_days": 7, "estimated_hours": 8, "step_type": "interview"},
        {"number": 3, "name": "Map competing alternatives", "what_to_do": "Compare direct products, manual workarounds, and doing nothing across cost, effort, trust, and outcome.", "why_it_matters": "Your real competition is often an existing habit, not another startup.", "done_criteria": "A comparison shows one underserved segment and why current options fail it.", "estimated_time_days": 4, "estimated_hours": 5, "step_type": "research"},
        {"number": 4, "name": "Build the smallest test", "what_to_do": "Create a concierge, clickable, or manual test that delivers only the core promise.", "why_it_matters": "It tests behavior before engineering effort hides weak demand.", "done_criteria": "Five target users can attempt the core job and the result is observable.", "estimated_time_days": 6, "estimated_hours": 9, "step_type": "build"},
        {"number": 5, "name": "Test willingness to pay", "what_to_do": "Present two price points and ask for a deposit, preorder, or signed pilot commitment.", "why_it_matters": "Interest without sacrifice is not demand.", "done_criteria": "At least three qualified users make a binding commitment or the pricing belief is revised.", "estimated_time_days": 5, "estimated_hours": 6, "step_type": "sell"},
        {"number": 6, "name": "Choose the business loop", "what_to_do": "Map acquisition, activation, delivery, retention, revenue, and cost as one repeatable loop.", "why_it_matters": "A useful product can still fail if reaching and serving customers is uneconomic.", "done_criteria": "The loop has one owner, metric, cost, and failure threshold at every stage.", "estimated_time_days": 3, "estimated_hours": 4, "step_type": "measure"},
        {"number": 7, "name": "Launch to the first cohort", "what_to_do": "Release to one narrow group and track activation, repeated use, referrals, and support burden.", "why_it_matters": "A controlled cohort exposes retention and delivery problems without creating broad noise.", "done_criteria": "The cohort reaches the predefined activation and repeat-use threshold.", "estimated_time_days": 10, "estimated_hours": 12, "step_type": "launch"},
    ]


JOURNEY_EXTENSIONS = [
    {"phase_order": "8", "phase_name": "Financial readiness", "focus": "Protect runway and fund only evidence-backed work", "completion_signal": "A staged budget with reserve and stop rules", "accent": "blue"},
    {"phase_order": "9", "phase_name": "Launch & distribution", "focus": "Prepare release, distribution, support, and launch gates", "completion_signal": "A narrow launch can be operated and measured safely", "accent": "peach"},
    {"phase_order": "10", "phase_name": "Growth & optimization", "focus": "Improve the proven loop without hiding weak retention", "completion_signal": "One repeatable growth loop with healthy economics", "accent": "green"},
]

ACTION_EXTENSIONS = [
    {"phase_order": "8", "action_order": "1", "phase_name": "Financial readiness", "action_title": "Build the evidence budget", "action_description": "Assign capital to proof-producing work, operating reserve, and explicit stop conditions.", "target_people": "Founder and one financially literate reviewer", "recruiting_channel": "Private working session", "outreach_script": "Review which expense buys evidence and which only creates irreversible commitment.", "framework": "Evidence-gated budget", "deliverable": "Staged allocation with release conditions", "pass_signal": "Every spend has an evidence condition", "fail_signal": "Capital is allocated before the relevant uncertainty is tested", "estimated_days": "2", "estimated_hours": "3", "estimated_cash": "0"},
    {"phase_order": "8", "action_order": "2", "phase_name": "Financial readiness", "action_title": "Model runway and funding gap", "action_description": "Compare available capital, expected burn, reserve, and the time to the next proof.", "target_people": "Founder", "recruiting_channel": "Financial worksheet", "outreach_script": "Not applicable", "framework": "Runway model", "deliverable": "Base, lean, and stop-case runway", "pass_signal": "The next proof fits inside available capital and reserve", "fail_signal": "The plan depends on funding that is not available", "estimated_days": "2", "estimated_hours": "3", "estimated_cash": "0"},
    {"phase_order": "8", "action_order": "3", "phase_name": "Financial readiness", "action_title": "Choose the funding trigger", "action_description": "Define what evidence must exist before bootstrapping more, borrowing, or raising capital.", "target_people": "Founder and potential finance adviser", "recruiting_channel": "Decision review", "outreach_script": "Which proof would justify the next capital commitment?", "framework": "Funding gate", "deliverable": "Written fund, wait, or stop threshold", "pass_signal": "Funding is tied to observed evidence", "fail_signal": "Funding is treated as proof of demand", "estimated_days": "1", "estimated_hours": "2", "estimated_cash": "0"},
    {"phase_order": "9", "action_order": "1", "phase_name": "Launch & distribution", "action_title": "Prepare launch requirements", "action_description": "List product, legal, privacy, payments, analytics, support, and distribution requirements.", "target_people": "Founder and delivery owner", "recruiting_channel": "Launch review", "outreach_script": "What must work on day one, and what can wait?", "framework": "Launch readiness checklist", "deliverable": "Must-have launch checklist with owners", "pass_signal": "Every non-negotiable requirement has an owner and test", "fail_signal": "Critical launch work is still implicit", "estimated_days": "3", "estimated_hours": "5", "estimated_cash": "50"},
    {"phase_order": "9", "action_order": "2", "phase_name": "Launch & distribution", "action_title": "Prove one distribution path", "action_description": "Test the actual route to customers, including app-store, community, partner, outbound, or local distribution.", "target_people": "Twenty qualified prospects", "recruiting_channel": "Primary launch channel", "outreach_script": "I am opening a narrow first cohort for people currently dealing with this problem.", "framework": "Distribution test", "deliverable": "Qualified reach and conversion log", "pass_signal": "One channel reliably reaches the intended segment", "fail_signal": "Reach is broad but qualified response is weak", "estimated_days": "7", "estimated_hours": "7", "estimated_cash": "100"},
    {"phase_order": "9", "action_order": "3", "phase_name": "Launch & distribution", "action_title": "Run the launch rehearsal", "action_description": "Simulate onboarding, delivery, support, failure handling, and measurement before release.", "target_people": "Five rehearsal users and the operating owner", "recruiting_channel": "Private rehearsal", "outreach_script": "Use the experience as if this were launch day and report every point of confusion.", "framework": "Launch rehearsal", "deliverable": "Resolved launch blockers and rollback plan", "pass_signal": "Critical paths complete without founder rescue", "fail_signal": "Delivery depends on undocumented manual intervention", "estimated_days": "3", "estimated_hours": "6", "estimated_cash": "50"},
    {"phase_order": "10", "action_order": "1", "phase_name": "Growth & optimization", "action_title": "Find the retained cohort", "action_description": "Separate users who repeat the core behavior from users who only tried once.", "target_people": "First launched cohort", "recruiting_channel": "Product and follow-up data", "outreach_script": "What caused you to return, or what stopped the second use?", "framework": "Retention cohort", "deliverable": "Cohort retention and reason table", "pass_signal": "A specific cohort repeats the core behavior", "fail_signal": "Acquisition hides weak repeat use", "estimated_days": "14", "estimated_hours": "6", "estimated_cash": "0"},
    {"phase_order": "10", "action_order": "2", "phase_name": "Growth & optimization", "action_title": "Optimize the proven bottleneck", "action_description": "Improve the single weakest proven stage instead of adding unrelated features.", "target_people": "Users affected by the bottleneck", "recruiting_channel": "Behavioral segment", "outreach_script": "What prevented the next intended action?", "framework": "Constraint experiment", "deliverable": "One before-and-after bottleneck test", "pass_signal": "The target behavior improves without harming quality", "fail_signal": "The change improves vanity activity only", "estimated_days": "7", "estimated_hours": "8", "estimated_cash": "100"},
    {"phase_order": "10", "action_order": "3", "phase_name": "Growth & optimization", "action_title": "Set the next operating cadence", "action_description": "Define the weekly evidence, financial, support, and growth review that keeps decisions honest.", "target_people": "Founder and operating team", "recruiting_channel": "Operating review", "outreach_script": "Which decision will each metric change?", "framework": "Operating cadence", "deliverable": "Weekly decision review with owners", "pass_signal": "Every recurring metric has an owner and decision", "fail_signal": "Reporting grows without changing action", "estimated_days": "2", "estimated_hours": "3", "estimated_cash": "0"},
]


def _journey_phases(archetype: str) -> list[dict[str, str]]:
    rows = [row for row in _rows("phase_library.csv") if row["archetype"] == archetype]
    if not rows:
        rows = [row for row in _rows("phase_library.csv") if row["archetype"] == "universal"]
    rows = [
        {
            **row,
            **(
                {"phase_name": "Validation & proof", "focus": "Run a controlled cohort and test repeat behavior", "completion_signal": "Observed activation and repeat-use evidence"}
                if int(row["phase_order"]) == 7
                else {}
            ),
        }
        for row in rows
    ]
    existing = {int(row["phase_order"]) for row in rows}
    rows.extend({**row, "archetype": archetype} for row in JOURNEY_EXTENSIONS if int(row["phase_order"]) not in existing)
    return sorted(rows, key=lambda row: int(row["phase_order"]))


def _journey_actions(archetype: str) -> list[dict[str, str]]:
    rows = [row for row in _rows("blueprint_phase_actions.csv") if row["archetype"] in {archetype, "universal"}]
    rows.extend({**row, "archetype": archetype, "resource_type": "Blueprint worksheet", "resource_url": "#"} for row in ACTION_EXTENSIONS)
    return rows


def _phase_for(step_type: str, index: int) -> int:
    if step_type == "interview": return 2
    if step_type == "research": return 1 if index == 0 else 3
    if step_type == "validate": return 4 if index < 5 else 7
    if step_type in {"build", "learn_skill"}: return 6
    if step_type == "sell": return 5
    if step_type == "operate": return 8
    if step_type == "launch": return 9
    if step_type == "measure": return 10 if index > 7 else 7
    return 1


def _calendar(uid: str, commitment: str, hours: int) -> str:
    months = [
        ("July 2026", [29,30,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,1,2]),
        ("August 2026", [27,28,29,30,31,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30]),
        ("September 2026", [31,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,1,2,3,4]),
    ]
    controls = []
    grids = []
    for index, (name, days) in enumerate(months):
        checked = " checked" if index == 1 else ""
        controls.append(f'<input class="month-radio" type="radio" name="month-{uid}" id="month-{uid}-{index}"{checked}>')
        cells = "".join(f'<span class="{"today" if (index == 1 and day == 16) else ""}">{day}</span>' for day in days)
        grids.append(f'<div class="month-view month-{index}"><b>{name}</b><div class="calendar-grid">{cells}</div></div>')
    return "".join(controls) + f'<div class="calendar-head"><h3>Plan calendar</h3><div><label for="month-{uid}-0">‹</label><label for="month-{uid}-1">•</label><label for="month-{uid}-2">›</label></div></div><div class="weekdays"><span>M</span><span>T</span><span>W</span><span>T</span><span>F</span><span>S</span><span>S</span></div>' + "".join(grids) + f'<div class="commitment"><small>NEXT COMMITMENT</small><h4>{html.escape(commitment)}</h4><p>Protect {hours} focused hours and record the evidence before moving forward.</p></div>'


def _financial_panel(archetype: str, money: int) -> str:
    rows = [row for row in _rows("blueprint_financial_models.csv") if row["archetype"] == archetype]
    if not rows:
        rows = [row for row in _rows("blueprint_financial_models.csv") if row["archetype"] == "universal"]
    allocations = []
    for row in rows[:5]:
        percent = int(row["allocation_percent"])
        amount = round(money * percent / 100)
        funded_percent = percent if money > 0 else 0
        allocations.append(
            f'<div class="allocation"><div><b>{html.escape(row["bucket"])}</b><small>{html.escape(row["release_condition"])}</small></div>'
            f'<span>${amount:,}</span><i class="{"unfunded" if money <= 0 else ""}" style="--allocation:{funded_percent}%"></i></div>'
        )
    return (
        '<summary><div class="finance-hero"><div class="finance-top"><span class="wallet-icon">$</span><small>CAPITAL AVAILABLE</small>'
        '<a class="finance-edit" href="/?edit_step=4" aria-label="Edit available capital"><span class="material-symbols-rounded">edit</span></a></div>'
        f'<strong>${money:,}</strong></div>'
        '<div class="finance-copy"><h3>Financial plan</h3><span>BREAKDOWN <i></i></span></div></summary>'
        f'<div class="finance-expanded"><div class="allocations">{"".join(allocations)}</div></div>'
    )


def render_product_dashboard_v2() -> None:
    st.markdown("""<style>[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stSidebar"],[data-testid="stSidebarNav"],[data-testid="collapsedControl"],#MainMenu,footer{display:none!important}html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]{margin:0!important;background:#070707!important}.main .block-container,[data-testid="stMainBlockContainer"]{width:100%!important;max-width:none!important;padding:0!important}[data-testid="stVerticalBlock"]{gap:0!important}</style>""", unsafe_allow_html=True)

    requested_phase = int(st.query_params.get("phase", st.session_state.get("dashboard_view", 0)) or 0)
    completion_key = str(st.query_params.get("complete", "") or "")
    undo_key = str(st.query_params.get("undo", "") or "")
    if completion_key or undo_key:
        completed_steps = {str(item) for item in st.session_state.get("completed_steps", set())}
        if completion_key:
            completed_steps.add(completion_key)
        if undo_key:
            completed_steps.discard(undo_key)
        st.session_state["completed_steps"] = completed_steps
        st.session_state["dashboard_view"] = requested_phase
        st.query_params.clear()
        st.rerun()

    profile, plan, reality, ledger = (st.session_state.get(key) for key in ("profile", "plan", "reality", "ledger"))
    dialog_idea = (st.session_state.get("dialog_answers", {}) or {}).get("idea", "")
    idea = str(_get(profile, "idea", "") or st.session_state.get("idea", "") or dialog_idea or "Your Product Idea")
    project_title = _title(idea)
    archetype = _archetype(profile, idea)
    action_archetype = "digital_product" if archetype == "digital_product" and any(word in idea.lower() for word in ("plant", "garden", "nursery")) else "universal"
    idea_prior = _matched_idea(idea)
    idea_id = idea_prior.get("idea_id", "")
    evidence_events = [row for row in _rows("blueprint_evidence_events.csv") if not idea_id or row.get("idea_id") == idea_id]
    phases = _journey_phases(archetype)
    resources = {row["step_type"]: row for row in _rows("evidence_resources.csv")}
    action_library = _journey_actions(action_archetype)
    raw_steps = list(_get(plan, "steps", []) or _default_steps())
    steps = []
    for index, step in enumerate(raw_steps):
        step_type = str(_get(step, "step_type", "validate"))
        steps.append({
            "number": int(_get(step, "number", index + 1)), "name": str(_get(step, "name", f"Milestone {index+1}")),
            "what": str(_get(step, "what_to_do", "Complete the evidence-producing action.")), "why": str(_get(step, "why_it_matters", "This reduces a material uncertainty.")),
            "done": str(_get(step, "done_criteria", "Record the result and decision.")), "days": int(_get(step, "estimated_time_days", 4)),
            "hours": int(_get(step, "estimated_hours", 5)), "type": step_type, "phase": _phase_for(step_type, index),
            "resources": list(_get(step, "resources", []) or []),
        })
    completed = {str(item) for item in (st.session_state.get("completed_steps", set()) or st.session_state.get("done_steps", set()))}
    target_customer = str(_get(profile, "target_customer", "") or "")
    background = str(_get(profile, "background", "") or "")
    success_definition = str(_get(profile, "success_definition", "") or "")
    current_work = str(_get(profile, "current_work", "") or "")
    constraints = list(_get(profile, "constraints", []) or _get(profile, "life_context", []) or [])
    input_checks = [
        bool(idea and idea != "Your Product Idea"), bool(target_customer), bool(str(_get(profile, "goal", "")) or success_definition),
        bool(background or current_work), bool(constraints), _get(profile, "hours_per_week", None) is not None,
        _get(profile, "money_available", None) is not None, bool(str(_get(profile, "launch_timeline", ""))),
    ]
    input_count = sum(input_checks)
    profile_strength = round(input_count / len(input_checks) * 100)
    execution_completion = round(len(completed) / max(len(steps), 1) * 100)
    completion = round((input_count + len(completed)) / (len(input_checks) + max(len(steps), 1)) * 100)
    assumptions = len(list(_get(reality, "specific_delusions", []) or [])) or int(_number(idea_prior.get("assumption_count"), 0))
    observed_positives = sum(1 for row in evidence_events if row.get("signal_direction", "").lower() == "positive")
    risks = len(list(_get(reality, "critical_gaps", []) or [])) or int(_number(idea_prior.get("risk_count"), 0))
    money = int(_get(profile, "money_available", _get(ledger, "cash_dollars", 0)) or 0)
    weekly_hours = int(_get(profile, "hours_per_week", 0) or 0)
    total_days = int(_get(plan, "total_estimated_days", sum(step["days"] for step in steps)) or 0)
    estimated_cash = max(1, int(_number(idea_prior.get("estimated_cash_cost"), 1)))
    prior_actions = 0 if not current_work or "Nothing yet" in current_work else len([item for item in current_work.split(",") if item.strip()])
    positives = observed_positives
    clarity = profile_strength
    input_labels = ("Idea", "Target customer", "Goal and outcome", "Founder context", "Constraints", "Weekly time", "Budget", "Launch horizon")
    captured_inputs = [label for label, complete in zip(input_labels, input_checks) if complete]
    strongest_signal = (captured_inputs[-1] if captured_inputs else "Idea", 100 if captured_inputs else 0)
    readiness = execution_completion

    delusions = list(_get(reality, "specific_delusions", []) or [])
    assumption_items = []
    for item in delusions:
        belief = item.get("belief", "Untested belief") if isinstance(item, dict) else str(item)
        assumption_items.append((belief, "OPEN"))
    assumption_candidates = [
        (f'{target_customer or "The intended customer"} experiences this problem often enough to act', "TO TEST"),
        ("Recent behavior—not stated interest—shows the problem is urgent", "TO TEST"),
        ("A reachable channel can recruit qualified users without broad paid acquisition", "TO TEST"),
        ("The promised outcome is meaningfully better than the current workaround", "TO TEST"),
        (f'The founder can sustain delivery within {weekly_hours} hours each week', "TO TEST"),
        ("A manual or concierge version can deliver the core outcome before a full build", "TO TEST"),
        ("Qualified users will make a binding payment or pilot commitment", "TO TEST"),
        ("The delivery cost leaves enough margin to repeat the model", "TO TEST"),
        ("Users will return or repeat the core behavior without repeated prompting", "TO TEST"),
        ("The product can define a safe boundary for cases it should not handle", "TO TEST"),
    ]
    for candidate in assumption_candidates:
        if len(assumption_items) >= assumptions:
            break
        if candidate[0] not in {item[0] for item in assumption_items}:
            assumption_items.append(candidate)
    assumption_items = assumption_items[:assumptions]
    gap_items = list(_get(reality, "critical_gaps", []) or [])
    risk_items = [(str(item), "OPEN") for item in gap_items]
    risk_candidates = [
        ("The first customer segment may be too broad to show a repeated pain pattern", "OPEN"),
        (f'Distribution may require more access than the current {idea_prior.get("distribution_risk", "medium")} planning prior assumes', "OPEN"),
        (f'Technical delivery carries {idea_prior.get("technical_risk", "medium")} prior risk before a manual test', "OPEN"),
        ("Interest may not convert into a payment, deposit, or signed pilot", "OPEN"),
        ("Support effort may make the first delivery model uneconomic", "OPEN"),
        ("Repeat use may fall after the first problem is solved", "OPEN"),
        ("The launch cohort may be too mixed to diagnose why activation fails", "OPEN"),
    ]
    for candidate in risk_candidates:
        if len(risk_items) >= risks:
            break
        if candidate[0] not in {item[0] for item in risk_items}:
            risk_items.append(candidate)
    risk_items = risk_items[:risks]

    def tooltip(items: list[tuple[str, Any]]) -> str:
        return "".join(f'<li><span>{html.escape(label)}</span><b>{html.escape(str(value))}</b></li>' for label, value in items)

    phase_progress: dict[int, tuple[int, int]] = {}
    for phase in phases:
        order = int(phase["phase_order"])
        phase_steps = [step for step in steps if step["phase"] == order]
        matching_actions = [row for row in action_library if row["archetype"] == action_archetype and int(row["phase_order"]) == order]
        total = max(1, len(phase_steps), len(matching_actions))
        done = (
            sum(1 for row in matching_actions if f'{order}-{row["action_order"]}' in completed)
            if matching_actions
            else sum(1 for step in phase_steps if str(step["number"]) in completed)
        )
        phase_progress[order] = (done, total)
    roadmap_done = sum(done for done, _ in phase_progress.values())
    roadmap_total = sum(total for _, total in phase_progress.values())
    completion = round((input_count + roadmap_done) / max(len(input_checks) + roadmap_total, 1) * 100)
    active_phase_order = next((int(phase["phase_order"]) for phase in phases if phase_progress[int(phase["phase_order"])][0] < phase_progress[int(phase["phase_order"])][1]), int(phases[-1]["phase_order"]) if phases else 1)
    dot_columns = []
    tracked_days = 84
    projected_days = min(tracked_days, round(tracked_days * completion / 100))
    progress_pattern = (1, 2, 1, 3, 5, 2, 4, 7, 3, 2, 6, 4, 2, 5, 3, 1, 4, 6, 2, 3, 7, 5, 2, 4, 1, 3, 6, 4, 2, 5, 7, 3, 1, 4, 6, 2, 5, 3, 7, 4, 2, 5)
    for day in range(tracked_days):
        column_height = progress_pattern[day % len(progress_pattern)]
        cells = []
        for row_index in range(7):
            from_bottom = 6 - row_index
            state = "expected" if from_bottom < column_height else ""
            user_height = max(1, round(column_height * max(profile_strength, 20) / 100))
            if day < projected_days and from_bottom < user_height:
                state = "actual"
            elif day == projected_days and from_bottom == 0:
                state = "today"
            cells.append(f'<i class="{state}"></i>')
        tooltip_text = f'Day {day + 1}: gray is the reference path; orange is your projected path from current inputs and completed actions'
        dot_columns.append(f'<span class="dot-column" title="{html.escape(tooltip_text)}">{"".join(cells)}</span>')
    dot_tracker = "".join(dot_columns)

    overview_checked = " checked" if requested_phase == 0 else ""
    nav = [f'<input class="view-radio" type="radio" name="view" id="view-0"{overview_checked}><label class="overview" for="view-0"><span class="overview-icon" aria-hidden="true"><i></i><i></i><i></i><i></i></span><span>Overview</span><i>›</i></label>']
    for phase in phases:
        order = int(phase["phase_order"])
        phase_done, phase_total = phase_progress[order]
        checked = " checked" if requested_phase == order else ""
        nav.append(f'<input class="view-radio" type="radio" name="view" id="view-{order}"{checked}><label class="phase-nav {phase["accent"]}" for="view-{order}"><span>{order}</span><b>{html.escape(phase["phase_name"])}</b><small>{phase_done}/{phase_total}</small><i>›</i></label>')

    def step_markup(items: list[dict[str, Any]], view_id: int) -> str:
        output = []
        for index, step in enumerate(items):
            resource = resources.get(step["type"], resources.get("validate", {}))
            action_key = f'{step["phase"]}-1' if view_id == 0 else f'{view_id}-{step["number"]}'
            is_done = action_key in completed
            state = "done" if is_done else ("active" if index == 0 else "")
            completion_label = "Completed" if is_done else "Mark complete"
            completion_param = "undo" if is_done else "complete"
            completion_control = f'<a class="completion-action" href="/Your_Plan?{completion_param}={action_key}&phase={view_id}" aria-label="{completion_label}: {html.escape(step["name"])}"><i></i><span>{completion_label}</span></a>'
            extra_resources = "".join(f"<li>{html.escape(str(item))}</li>" for item in step["resources"][:2])
            output.append(f'''<details class="road-step {state}" {'open' if index == 0 and view_id != 0 else ''}><summary><span class="node">{step['number']}</span><div><b>{html.escape(step['name'])}</b><small>{html.escape(step['type'].replace('_',' ').title())} · {step['hours']} hours</small></div>{completion_control}<span class="chevron" aria-hidden="true"></span></summary><div class="step-detail"><div><small>WHAT YOU WILL DO</small><p>{html.escape(step['what'])}</p></div><div><small>WHY IT MATTERS</small><p>{html.escape(step['why'])}</p></div><div class="learning"><small>FRAMEWORK & LEARNING</small><b>{html.escape(resource.get('framework_title','Evidence test'))}</b><p>{html.escape(resource.get('usage_note','Use the framework to record evidence and make a decision.'))}</p><a href="{html.escape(resource.get('url','#'))}" target="_blank">Open {html.escape(resource.get('resource_title','resource'))} ↗</a></div><div><small>DONE WHEN</small><p>{html.escape(step['done'])}</p>{'<ul>'+extra_resources+'</ul>' if extra_resources else ''}</div></div></details>''')
        return "".join(output)

    def signal_markup(view_id: int, phase: dict[str, str] | None, phase_steps: list[dict[str, Any]]) -> str:
        phase_name = phase["phase_name"] if phase else "Whole blueprint"
        phase_events = evidence_events if not view_id else [row for row in evidence_events if row.get("phase_name") == phase_name]
        def card(label: str, value: str, icon: str, numerator: float, denominator: float, note: str, tone: str, status: str, visual: str = "wave") -> str:
            icon = {
                "hourglass_top": "timeline", "history": "update", "route": "alt_route",
                "rule": "checklist", "conversion_path": "alt_route", "schedule": "calendar_today",
                "query_stats": "monitoring", "person_check": "person_search",
            }.get(icon, icon)
            ratio = 0 if denominator <= 0 else min(1, max(0, numerator / denominator))
            filled = round(ratio * 12)
            if visual == "dots":
                graphic = '<div class="signal-dots">' + "".join(f'<i class="{"filled" if index < filled else ""}"></i>' for index in range(24)) + '</div>'
            elif visual == "range":
                graphic = f'<div class="signal-range"><i style="left:{round(ratio*100)}%"></i><span></span></div>'
            elif visual == "ring":
                graphic = f'<div class="signal-ring" style="--value:{round(ratio*360)}deg"><b>{round(ratio*100)}%</b></div>'
            elif visual == "text":
                graphic = '<div class="signal-action">NEXT DECISION →</div>'
            else:
                heights = (28, 54, 35, 72, 46, 84, 38, 63, 31, 77, 52, 68)
                graphic = '<div class="signal-wave">' + "".join(f'<i class="{"filled" if index < filled else ""}" style="height:{height}%"></i>' for index, height in enumerate(heights)) + '</div>'
            return f'<article class="signal fact-card {tone}"><div class="signal-title"><span class="material-symbols-rounded signal-glyph">{html.escape(icon)}</span><b>{html.escape(label)}</b></div><em class="signal-status">{html.escape(status)}</em><strong>{html.escape(value)}</strong><small>{html.escape(note)}</small>{graphic}</article>'

        cards = []
        if phase_events:
            icons = ["query_stats", "person_check", "payments", "schedule", "conversion_path", "warning"]
            for index, event in enumerate(phase_events[-6:]):
                value = f'{event["metric_value"]}{"%" if event["metric_unit"] == "percent" else ""}'
                note = f'{event["sample_size"]} observed · {event["confidence"]} confidence'
                numerator = _number(event.get("metric_value"), 0)
                denominator = _number(event.get("threshold_high"), 100 if event.get("metric_unit") == "percent" else 10)
                direction = event.get("signal_direction", "observed").lower()
                tone = "green" if direction == "positive" else "red" if direction == "negative" else "neutral"
                cards.append(card(event["metric_name"].replace("_", " ").title(), value, icons[index % len(icons)], numerator, denominator, note, tone, direction.upper(), ("wave", "dots", "range", "ring")[index % 4]))
        else:
            if view_id:
                benchmarks = [row for row in _rows("blueprint_signal_benchmarks.csv") if row["phase_name"].lower() == phase_name.lower() and row["archetype"] in {archetype, "universal"}]
                phase_specs = {
                    1: [("Risky beliefs ordered", "5 target", "rule", 5, 5, "Five assumptions must be ranked before research", "violet", "PLAN TARGET", "dots"), ("Founder limits mapped", "4 areas", "fact_check", 4, 4, "Time, capital, skills, and life constraints", "blue", "USER + PLAN", "range"), ("Stop rules written", "3 gates", "warning", 3, 5, "Desirability, feasibility, and viability gates", "red", "PLAN TARGET", "wave")],
                    2: [("Qualified interviews", "10 target", "person_check", 10, 10, "Recent behavior from reachable target users", "blue", "TARGET — NOT OBSERVED", "dots"), ("Customer segments", "3 planned", "route", 3, 5, "Contrast segments instead of averaging everyone", "violet", "PLAN DATA", "range"), ("Repeated pain gate", "5 patterns", "query_stats", 5, 10, "Independent users must repeat the same problem", "green", "TARGET — NOT OBSERVED", "wave")],
                    3: [("Alternatives compared", "5 target", "route", 5, 5, "Products, workarounds, and doing nothing", "blue", "PLAN TARGET", "dots"), ("Review sample", "50 target", "query_stats", 50, 50, "Complaints are coded before choosing a wedge", "amber", "TARGET — NOT OBSERVED", "wave"), ("Reachable channels", "2 tests", "conversion_path", 2, 4, "A channel must recruit qualified users", "violet", "PLAN TARGET", "range")],
                    4: [("Test participants", "5 target", "person_check", 5, 5, "Use a manual or concierge core promise", "blue", "TARGET — NOT OBSERVED", "dots"), ("Core action gate", "≥ 60%", "fact_check", 60, 100, "Users must complete the intended behavior", "green", "BENCHMARK TARGET", "ring"), ("Repeat behavior", "14 days", "history", 14, 21, "Look for a voluntary second use", "violet", "PLAN TARGET", "wave")],
                    5: [("Binding commitments", "3 target", "payments", 3, 8, "Payment, deposit, preorder, or signed pilot", "green", "TARGET — NOT OBSERVED", "dots"), ("Qualified sample", "8 people", "person_check", 8, 8, "Ask only users who completed the core test", "blue", "PLAN TARGET", "wave"), ("Price anchors", "2 tests", "payments", 2, 3, "Compare real choices without discounting", "amber", "PLAN TARGET", "range")],
                    6: [("Business loop stages", "6 mapped", "conversion_path", 6, 6, "Acquisition through cost and retention", "blue", "PLAN TARGET", "wave"), ("Metric owners", "1 each", "rule", 6, 6, "Every stage needs an owner and failure threshold", "violet", "PLAN TARGET", "dots"), ("Delivery boundary", "1 gate", "warning", 1, 3, "Define when the model must defer or stop", "red", "PLAN TARGET", "range")],
                    7: [("Launch cohort", "20 target", "person_check", 20, 20, "One narrow group through a validated channel", "blue", "TARGET — NOT OBSERVED", "dots"), ("Repeat-use gate", "≥ 35%", "history", 35, 100, "Retention decides whether launch broadens", "green", "BENCHMARK TARGET", "ring"), ("Decision thresholds", "5 written", "rule", 5, 5, "Pass, pause, and stop before results arrive", "amber", "PLAN TARGET", "wave")],
                    8: [("Planned investment", f"${money:,}", "payments", money, max(estimated_cash, 1), "Capital available for evidence-gated work", "neutral", "USER INPUT", "range"), ("Funding gap", f"${max(0, estimated_cash-money):,}", "warning", max(0, estimated_cash-money), max(estimated_cash, 1), "Difference between the planning prior and available capital", "red" if money < estimated_cash else "green", "PLANNING PRIOR", "ring"), ("Runway gate", "Not modeled" if money <= 0 else "Ready to model", "hourglass_top", 1 if money > 0 else 0, 1, "Requires an expected monthly burn before runway is defensible", "neutral", "HONEST STATE", "text")],
                    9: [("Launch requirements", "3 groups", "fact_check", 3, 3, "Product, operations, and measurement must be ready", "neutral", "PLAN TARGET", "dots"), ("Distribution paths", "1 to prove", "route", 0, 1, "App store, community, partner, outbound, or local channel", "neutral", "TARGET — NOT OBSERVED", "range"), ("Launch blockers", str(risks), "warning", risks, max(risks, 5), "Open risks that could prevent a controlled release", "red", "OPEN", "ring")],
                    10: [("Retained cohort", "Not observed", "history", 0, 1, "Growth begins only after voluntary repeat behavior", "neutral", "HONEST EMPTY STATE", "ring"), ("Growth bottleneck", "To identify", "query_stats", 0, 1, "Optimize one proven constraint instead of adding features", "neutral", "TARGET — NOT OBSERVED", "text"), ("Operating cadence", "1 weekly", "schedule", 1, 1, "Evidence, finance, support, and growth decisions", "neutral", "PLAN TARGET", "dots")],
                }
                cards = [card(*spec) for spec in phase_specs.get(view_id, [])]
                cards.append(card("Executable actions", str(len(phase_steps)), "route", len(phase_steps), max(len(phase_steps), 1), "Each action includes a person, channel, script, deliverable, and gate", "blue", "PLAN DATA", "dots"))
                for benchmark in benchmarks[:2]:
                    if benchmark["signal_label"] not in {"Repeated pain patterns", "Binding commitments", "Retained or repeated usage"}:
                        cards.append(card(benchmark["signal_label"], benchmark["strong_threshold"], "query_stats", 0, 1, f'Measure with {benchmark["collection_method"]}; minimum sample {benchmark["minimum_sample"]}', "green", "TARGET — NOT OBSERVED", "range"))
            else:
                first_step_days = phase_steps[0]["days"] if phase_steps else 0
                customer_events = [event for event in evidence_events if "customer" in event.get("phase_name", "").lower()]
                revenue_done, revenue_total = phase_progress.get(5, (0, 1))
                validation_confidence = round((len(evidence_events) / max(len(evidence_events) + assumptions, 1)) * 100)
                next_proof = next((step["name"] for step in steps if f'{step["phase"]}-1' not in completed), steps[-1]["name"] if steps else "Define the next proof")
                facts = [
                    card("Validation confidence", f"{validation_confidence}%", "fact_check", validation_confidence, 100, "Observed evidence compared with open assumptions", "green" if validation_confidence >= 60 else "neutral", "OBSERVED + OPEN", "ring"),
                    card("Customer evidence", str(len(customer_events)), "person_check", len(customer_events), 10, "Behavioral customer observations attached to this Blueprint", "neutral", "OBSERVED", "dots"),
                    card("Revenue readiness", f"{revenue_done}/{revenue_total}", "payments", revenue_done, revenue_total, "Pricing and commitment actions completed", "green" if revenue_done == revenue_total else "neutral", "ACTION STATE", "range"),
                    card("Critical open risks", str(risks), "warning", risks, max(risks, 5), "High-impact risks that can materially change the plan", "red", "INSPECTABLE", "ring"),
                    card("Assumption exposure", str(assumptions), "rule", assumptions, max(assumptions, 10), "Core beliefs still waiting for falsifiable evidence", "neutral", "PLANNING PRIOR", "dots"),
                    card("Next proof", next_proof, "route", 0, 1, f"Planned first proof window: {first_step_days} days", "amber", "ACTION", "text"),
                ]
                cards = facts
        return "".join(cards)

    views = []
    all_view_specs: list[tuple[int, dict[str, str] | None]] = [(0, None)] + [(int(phase["phase_order"]), phase) for phase in phases]
    for view_id, phase in all_view_specs:
        phase_steps = steps if view_id == 0 else [step for step in steps if step["phase"] == view_id]
        if view_id:
            library_rows = [row for row in action_library if row["archetype"] == action_archetype and int(row["phase_order"]) == view_id]
            if not library_rows:
                library_rows = [row for row in action_library if row["archetype"] == "universal" and int(row["phase_order"]) == view_id]
            if library_rows:
                phase_steps = [{
                    "number": int(row["action_order"]), "name": row["action_title"], "what": row["action_description"],
                    "why": f'Target: {row["target_people"]}. Recruit through {row["recruiting_channel"]}. Script: {row["outreach_script"]}',
                    "done": f'{row["deliverable"]}. Pass: {row["pass_signal"]}. Stop or revise: {row["fail_signal"]}.',
                    "days": int(row["estimated_days"]), "hours": int(row["estimated_hours"]), "type": "interview" if view_id == 2 else "validate",
                    "phase": view_id, "resources": [row["framework"], f'Estimated cash: ${row["estimated_cash"]}'],
                } for row in library_rows]
        if not phase_steps:
            phase_steps = [steps[min(view_id - 1, len(steps) - 1)]]
        heading = "Your roadmap" if phase is None else phase["phase_name"]
        subheading = "The evidence path already planned for this idea." if phase is None else phase["focus"]
        commitment = phase_steps[0]["name"]
        phase_note = "All phases" if phase is None else phase["completion_signal"]
        signal_source = "Observed evidence attached to this Blueprint" if evidence_events else "Your recorded inputs — facts only, not market validation"
        signal_heading = "Key signals"
        signal_description = (
            f"Observed evidence attached to {heading.lower()}."
            if evidence_events
            else (
                "A factual baseline from your inputs. Complete evidence actions to replace these starting facts with market signals."
                if view_id == 0
                else "Declared targets and planning rules for this phase. These are not observed market results."
            )
        )
        views.append(f'''<section class="dashboard-view view-{view_id}"><div class="work-grid"><article class="roadmap-card"><div class="roadmap-head"><div><span>{html.escape(phase_note)}</span><h2>{html.escape(heading)}</h2><p>{html.escape(subheading)}</p></div><em>{len(phase_steps)} actions</em></div><div class="roadmap-list">{step_markup(phase_steps, view_id)}</div></article><aside class="side-stack"><a class="side-blueprint" href="/Your_Plan?view=blueprint"><span class="material-symbols-rounded">account_tree</span><b>Open full Blueprint</b><small>See every phase, dependency, decision gate, and return path.</small><i>VIEW SYSTEM MAP →</i></a><details class="finance-card">{_financial_panel(archetype, money)}</details></aside></div><div class="signal-head"><div><h2>{signal_heading}</h2><p>{html.escape(signal_description)}</p></div></div><div class="signals">{signal_markup(view_id, phase, phase_steps)}</div></section>''')

    page = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL@20,400,0');
*{box-sizing:border-box}html,body{margin:0;background:#070707;color:#191919;font-family:-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif}.app{width:calc(100vw - 12px);min-height:calc(100vh - 12px);margin:6px;padding:24px 27px 34px;background:#ececeb;border-radius:29px;overflow:hidden}.topbar{height:53px;display:flex;align-items:center;justify-content:space-between}.brand{font-size:18px;font-weight:760;letter-spacing:-.055em}.account{display:flex;align-items:center;gap:14px}.account select{appearance:none;border:0;background:transparent;padding:8px 21px 8px 5px;color:#575757;font-size:11px}.avatar{width:34px;height:34px;border:1px solid #b6b6b6;border-radius:50%;display:grid;place-items:center;background:#fafafa;font-size:10px;font-weight:700;transition:.25s}.avatar:hover{transform:translateY(-2px);border-color:#111;box-shadow:0 8px 18px rgba(0,0,0,.09)}.layout{display:grid;grid-template-columns:218px minmax(0,1fr);gap:31px}.rail-title{height:69px;display:flex;align-items:baseline;gap:3px;white-space:nowrap}.rail-title strong,.rail-title span{font-size:27px;font-weight:400;letter-spacing:-.06em}.rail-title span{color:#aaa}.rail-title em{font-size:20px;font-style:normal;color:#9c9c9c;margin-right:0}.view-radio{position:absolute;opacity:0;pointer-events:none}.overview,.phase-nav{cursor:pointer;transition:.22s ease}.overview{height:54px;padding:0 14px;display:grid;grid-template-columns:28px 1fr auto;align-items:center;background:#fff;border-radius:28px;font-size:12px}.grid-icon{line-height:7px;color:#888;font-size:8px}.phase-list{margin-top:10px;border-top:1px solid #d8d8d8}.phase-nav{height:57px;padding:0 13px;display:grid;grid-template-columns:27px 1fr auto;align-items:center;border-bottom:1px solid #d8d8d8;border-radius:25px}.phase-nav>span{width:21px;height:21px;display:grid;place-items:center;border:1px solid #aaa;border-radius:50%;font-size:10px}.phase-nav b{font-size:12px;font-weight:400}.phase-nav i{font-style:normal;color:#888;opacity:0}.phase-nav:hover{transform:translateX(3px);background:rgba(255,255,255,.55)}.view-radio:checked+.phase-nav{margin:5px 0;background:#fff;border-color:transparent}.view-radio:checked+.phase-nav i{opacity:1}.view-radio:checked+.phase-nav.blue>span{background:#b9d9ff}.view-radio:checked+.phase-nav.peach>span{background:#ffc99f}.view-radio:checked+.phase-nav.lilac>span{background:#d9c8ff}.view-radio:checked+.phase-nav.pink>span{background:#ffc0d8}.view-radio:checked+.phase-nav.yellow>span{background:#f5e78b}.view-radio:checked+.phase-nav.violet>span{background:#c9b8ec}.view-radio:checked+.phase-nav.green>span{background:#b9e6b4}.workspace{min-width:0}.hero{display:grid;grid-template-columns:minmax(0,1fr) 292px;gap:20px}.title{margin:4px 0 20px;font-size:46px;font-weight:400;letter-spacing:-.075em;line-height:1}.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}.kpi{height:58px;display:flex;align-items:center;justify-content:flex-start;gap:8px}.kpi b{font:400 36px "Courier New",monospace;letter-spacing:-.1em}.kpi span{align-self:flex-start;margin-top:4px;padding:5px 8px;border-radius:12px;background:#fff;color:#777;font-size:8px}.kpi:nth-child(1) span{background:#dfff00;color:#344000}.kpi:nth-child(2) b{color:#6c61b9}.kpi:nth-child(3) b{color:#2787b7}.kpi:nth-child(4) b{color:#d36c50}.clarity{height:68px;position:relative;border-radius:35px;background:linear-gradient(90deg,#b9d9ff 0%,#d9c8ff 36%,#ffc99f 69%,#b9e6b4 100%);overflow:hidden;background-size:160% 100%;animation:gradient-shift 12s ease-in-out infinite}.clarity:after{content:"";position:absolute;inset:0;background-image:radial-gradient(circle,rgba(255,255,255,.75) 1.2px,transparent 1.4px);background-size:29px 12px;opacity:.45}.clarity-marker{position:absolute;z-index:2;left:calc(__CLARITY__% - 103px);top:8px;width:206px;height:52px;padding:10px 16px;border-radius:27px;background:rgba(255,255,255,.9);box-shadow:0 8px 22px rgba(30,30,30,.08);animation:breathe 3.6s ease-in-out infinite}.clarity-marker b{display:block;font-size:11px}.clarity-marker small{display:block;margin-top:5px;color:#888;font-size:8px}.position-wrap{position:relative}.open-blueprint{height:31px;display:flex;align-items:center;justify-content:flex-end;color:#292929;font-size:10px;text-decoration:none}.position{height:115px;padding:15px 17px;border-radius:25px;background:rgba(255,255,255,.8)}.position-head{display:flex;align-items:center;justify-content:space-between}.position-head h3{margin:0;font-size:12px}.edit{border:0;background:transparent;color:#777;font-size:16px}.position-row{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:14px}.position-row label{color:#999;font-size:7px}.position-row input{width:100%;display:block;margin-top:4px;padding:0 0 4px;border:0;border-bottom:1px solid #ddd;background:transparent;font:12px "Courier New",monospace;color:#222}.position-row input:focus{outline:0;border-color:#222}.dashboard-view{display:none}.app:has(#view-0:checked) .view-0,.app:has(#view-1:checked) .view-1,.app:has(#view-2:checked) .view-2,.app:has(#view-3:checked) .view-3,.app:has(#view-4:checked) .view-4,.app:has(#view-5:checked) .view-5,.app:has(#view-6:checked) .view-6,.app:has(#view-7:checked) .view-7{display:block;animation:view-in .38s ease both}.work-grid{display:grid;grid-template-columns:minmax(0,1fr) 292px;gap:20px;margin-top:20px}.roadmap-card,.calendar-card{border-radius:29px;background:rgba(255,255,255,.78);box-shadow:0 1px 0 rgba(255,255,255,.7) inset}.roadmap-card{min-height:440px;padding:23px 25px}.roadmap-head{display:flex;justify-content:space-between;padding-bottom:17px;border-bottom:1px solid #ddd}.roadmap-head span{display:inline-block;margin-bottom:5px;color:#777;font-size:8px;text-transform:uppercase;letter-spacing:.07em}.roadmap-head h2{margin:0;font-size:25px;font-weight:400;letter-spacing:-.05em}.roadmap-head p{margin:5px 0 0;color:#999;font-size:9px}.roadmap-head em{height:28px;padding:9px 11px;border-radius:15px;background:#eee;font-size:8px;font-style:normal}.road-step{border-bottom:1px solid #e3e3e3;transition:.25s}.road-step summary{min-height:47px;display:grid;grid-template-columns:31px 1fr auto 23px;gap:11px;align-items:center;cursor:pointer;list-style:none}.road-step summary::-webkit-details-marker{display:none}.node{width:29px;height:29px;display:grid;place-items:center;border:1px solid #aaa;border-radius:50%;font:10px "Courier New",monospace;transition:.25s}.road-step summary b{display:block;font-size:11px}.road-step summary small{display:block;margin-top:3px;color:#999;font-size:8px}.duration{color:#999;font-size:8px}.chevron{transition:.25s}.road-step[open]{margin:7px 0;border:1px solid #ddd;border-radius:20px;background:#fff;box-shadow:0 12px 28px rgba(0,0,0,.055);overflow:hidden}.road-step[open] summary{padding:0 13px}.road-step[open] .chevron{transform:rotate(180deg)}.road-step.active .node{background:#dfff00;border-color:#dfff00;box-shadow:0 0 0 4px rgba(223,255,0,.18)}.step-detail{padding:15px 55px 18px;display:grid;grid-template-columns:1fr 1fr;gap:14px;border-top:1px solid #eee}.step-detail>div{padding:12px;border-radius:14px;background:#f5f5f3}.step-detail small{font-size:7px;color:#929292;letter-spacing:.05em}.step-detail p{margin:6px 0 0;font-size:9px;line-height:1.45}.step-detail ul{margin:7px 0 0;padding-left:15px;font-size:8px}.learning{background:linear-gradient(135deg,#eef5ff,#f5edff)!important}.learning b{display:block;margin-top:6px;font-size:10px}.learning a{display:inline-block;margin-top:8px;color:#485085;font-size:8px}.calendar-card{min-height:440px;padding:22px}.calendar-head{display:flex;align-items:center;justify-content:space-between}.calendar-head h3{margin:0;font-size:13px}.calendar-head label{display:inline-grid;width:25px;height:25px;place-items:center;border-radius:50%;background:#f1f1f1;cursor:pointer;margin-left:3px}.month-radio{position:absolute;opacity:0}.weekdays,.calendar-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:7px;text-align:center}.weekdays{margin:20px 0 9px;color:#aaa;font-size:7px}.month-view{display:none}.calendar-card:has(input[id$="-0"]:checked) .month-0,.calendar-card:has(input[id$="-1"]:checked) .month-1,.calendar-card:has(input[id$="-2"]:checked) .month-2{display:block;animation:view-in .25s ease}.month-view>b{display:block;margin:-29px 80px 16px 0;text-align:right;color:#888;font-size:8px;font-weight:400}.calendar-grid span{height:24px;display:grid;place-items:center;border-radius:50%;font-size:8px}.calendar-grid .today{background:#dfff00}.commitment{margin-top:23px;padding-top:17px;border-top:1px solid #ddd}.commitment small{color:#999;font-size:7px}.commitment h4{margin:7px 0 4px;font-size:11px}.commitment p{margin:0;color:#777;font-size:8px;line-height:1.45}.signal-head{margin:26px 0 13px}.signal-head h2{margin:0;font-size:24px;font-weight:400;letter-spacing:-.05em}.signal-head p{margin:4px 0 0;color:#999;font-size:9px}.signals{display:grid;grid-template-columns:repeat(6,1fr);gap:11px}.signal{min-height:168px;padding:16px;border-radius:23px;background:#fff;position:relative;overflow:hidden;transition:.28s}.signals:has(.signal:nth-child(4):last-child){grid-template-columns:repeat(4,1fr)}.signal:hover{transform:translateY(-5px);box-shadow:0 16px 30px rgba(0,0,0,.08)}.signal.blue{background:#e5f1ff}.signal.peach{background:#ffe8d7}.signal.lilac{background:#eee7ff}.signal.pink{background:#ffe3ee}.signal.yellow{background:#fff7c9}.signal.green{background:#e1f3df}.signal small{color:#747474;font-size:8px}.signal>b{display:block;margin-top:27px;font:400 27px "Courier New",monospace}.signal>span{display:block;color:#8f8f8f;font-size:8px}.signal>div{position:absolute;left:15px;right:15px;bottom:15px;height:29px;display:flex;align-items:end;gap:4px}.signal i{flex:1;display:block;border-radius:4px 4px 1px 1px;background:rgba(55,55,55,.28);animation:signal-pulse 2.8s ease-in-out infinite}.signal i:nth-child(2n){animation-delay:.35s}.rail-note{margin-top:18px;padding:15px;border-radius:20px;background:linear-gradient(145deg,#fff,#f4efff)}.rail-note b{font-size:10px}.rail-note p{margin:6px 0 0;color:#888;font-size:8px;line-height:1.45}@keyframes view-in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}@keyframes gradient-shift{0%,100%{background-position:0 50%}50%{background-position:100% 50%}}@keyframes breathe{0%,100%{transform:translateY(0)}50%{transform:translateY(-2px)}}@keyframes signal-pulse{0%,100%{opacity:.45}50%{opacity:.9}}@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}@media(max-width:1180px){.layout{grid-template-columns:195px 1fr;gap:20px}.hero,.work-grid{grid-template-columns:1fr}.position-wrap{display:none}.calendar-card{min-height:auto}.signals{grid-template-columns:repeat(3,1fr)}}@media(max-width:760px){.app{width:100%;margin:0;border-radius:0;padding:16px}.layout{display:block}.rail{display:none}.title{font-size:36px}.kpis{grid-template-columns:1fr 1fr}.signals,.signals:has(.signal:nth-child(4):last-child){grid-template-columns:1fr 1fr}.step-detail{grid-template-columns:1fr;padding:12px}.account select{display:none}}
.weekdays{color:#888!important}.month-view>b{color:#555!important;font-weight:500!important}.calendar-grid span{color:#444}
.account select{display:none!important}.avatar{font-size:0!important;background:transparent!important;border:0!important;box-shadow:none!important;position:relative}.avatar:before{content:"";position:absolute;left:12px;top:5px;width:8px;height:8px;border:1.6px solid #222;border-radius:50%}.avatar:after{content:"";position:absolute;left:7px;bottom:5px;width:18px;height:10px;border:1.6px solid #222;border-bottom:0;border-radius:12px 12px 0 0}.avatar:hover{transform:none!important}.view-radio:checked+.phase-nav>span{background:transparent!important}.phase-nav{color:#333}.kpi:nth-child(n) b{color:#222}.clarity{background:#f5f5f4!important;animation:none!important;border:1px solid #e5e5e3}.clarity:before{content:"";position:absolute;left:0;top:0;bottom:0;width:__CLARITY__%;background:linear-gradient(90deg,rgba(189,211,226,.18),rgba(189,211,226,.58));border-radius:34px}.clarity:after{background-image:radial-gradient(circle,#aaa 1px,transparent 1.2px)!important;opacity:.34!important}.clarity-marker{animation:breathe 6s ease-in-out infinite!important}.position{height:115px}.position-row{grid-template-columns:1fr 1fr!important;gap:9px 17px!important;margin-top:11px!important}.position-row label{display:flex;align-items:end;justify-content:space-between;font-size:8px!important}.position-row input{width:68px!important;margin:0!important;text-align:right;font-size:10px!important}.edit{font-size:13px!important}.roadmap-card,.finance-card{border-radius:29px;background:rgba(255,255,255,.8)}.roadmap-head h2{font-size:28px}.roadmap-head p{font-size:11px}.road-step summary{min-height:52px}.road-step summary b{font-size:13px}.road-step summary small,.duration{font-size:9px}.step-detail small{font-size:8px}.step-detail p{font-size:10px}.learning b{font-size:11px}.learning a{font-size:9px}.finance-card{min-height:440px;padding:16px;overflow:hidden}.finance-hero{height:190px;padding:18px;position:relative;border-radius:24px;color:#fff;background:radial-gradient(circle at 70% 65%,#729eb4 0,#456f86 28%,transparent 55%),radial-gradient(circle at 20% 80%,#b97249 0,#735b56 34%,transparent 58%),linear-gradient(135deg,#708ea2,#d1b58a);box-shadow:0 18px 36px rgba(69,92,105,.16)}.finance-top{display:flex;justify-content:space-between;align-items:center}.wallet-icon{width:35px;height:35px;display:grid;place-items:center;border:1px solid rgba(255,255,255,.35);border-radius:50%;font-size:12px}.finance-arrow{width:38px;height:38px;display:grid;place-items:center;border-radius:50%;background:#fff;color:#222;font-size:17px}.finance-hero p{margin:20px 0 4px;font-size:12px}.finance-hero strong{font:400 31px "Courier New",monospace}.commitment-scale{position:absolute;right:18px;bottom:25px;width:126px;height:26px;display:flex;align-items:center;gap:10px}.commitment-scale:before{content:"";position:absolute;left:0;right:0;top:12px;height:1px;background:rgba(255,255,255,.65)}.commitment-scale>*{z-index:1;width:9px;height:9px;border-radius:50%;background:#fff}.commitment-scale span{width:7px;height:7px}.commitment-scale i:nth-of-type(1){width:18px;height:18px;background:#b6c8dd}.commitment-scale b{margin-left:auto;width:27px;height:27px}.finance-copy{padding:17px 5px 9px}.finance-copy h3{margin:0;font-size:15px}.finance-copy p{margin:5px 0 0;color:#888;font-size:9px}.allocations{padding:0 5px}.allocation{height:40px;display:grid;grid-template-columns:1fr auto;align-items:center;position:relative;border-bottom:1px solid #e2e2e2}.allocation div b{display:block;font-size:10px}.allocation div small{display:block;max-width:150px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#aaa;font-size:7px}.allocation>span{font:10px "Courier New",monospace}.allocation>i{position:absolute;left:0;bottom:-1px;width:var(--allocation);height:2px;background:#222}.signal-head h2{font-size:27px}.signal-head p{font-size:10px}.signals{gap:13px}.signal{min-height:206px!important;padding:18px!important;background:#fff!important;border-radius:27px!important;box-shadow:0 1px 0 rgba(255,255,255,.8) inset}.signal-title{position:static!important;height:auto!important;display:flex!important;align-items:center!important;gap:9px!important}.signal-title>span{width:29px;height:29px;display:grid;place-items:center;border:1px solid #cfcfcf;border-radius:50%;font-size:13px}.signal-title>b{font-size:11px;font-weight:500}.signal>strong{display:block;margin-top:34px;font:400 35px "Courier New",monospace;letter-spacing:-.08em}.signal>small{display:block;margin-top:3px;color:#999;font-size:9px}.signal>div[class^="visual-"]{position:absolute!important;left:18px!important;right:18px!important;bottom:18px!important;height:39px!important;display:flex!important;align-items:end!important;gap:5px!important}.signal>div[class^="visual-"] i{animation:none;display:block;flex:1;background:#c9c9c9}.visual-evidence i{width:2px!important;flex:none!important}.visual-evidence i:nth-child(5){height:100%!important;background:#222!important}.visual-pain{border-bottom:1px solid #aaa}.visual-pain:after{content:"";position:absolute;left:5px;bottom:6px;width:80%;height:24px;border-top:2px solid #777;border-radius:50%;transform:rotate(-4deg)}.visual-pain i{display:none!important}.visual-competition{align-items:center!important}.visual-competition:before{content:"";position:absolute;left:0;right:0;top:19px;height:1px;background:#aaa}.visual-competition i{z-index:1;flex:none!important;width:7px!important;height:7px!important;border-radius:50%!important;background:#fff!important;border:1px solid #777}.visual-competition i:nth-child(5){width:18px!important;height:18px!important;background:#cad8e8!important;border:0}.visual-competition i:last-child{margin-left:auto;width:23px!important;height:23px!important;background:#222!important}.visual-difference{display:grid!important;grid-template-columns:repeat(6,1fr)!important;gap:4px!important}.visual-difference i{height:5px!important;border-radius:50%!important}.visual-difference i:nth-child(3n){background:#222!important}.visual-pricing{border-bottom:1px solid #bbb}.visual-pricing:after{content:"";position:absolute;left:7%;bottom:2px;width:78%;height:28px;border-top:2px solid #555;border-radius:50%}.visual-pricing i{display:none!important}.visual-readiness{height:5px!important;bottom:28px!important;background:#ddd;border-radius:5px}.visual-readiness:after{content:"";width:__READY__%;height:100%;background:#222;border-radius:5px}.visual-readiness i{display:none!important}.rail-note{background:#fff!important}.signals:has(.signal:nth-child(4):last-child){grid-template-columns:repeat(4,1fr)}
.visual-evidence i{height:34%!important;width:2px!important;flex:none!important}.visual-evidence i:nth-child(2){height:52%!important}.visual-evidence i:nth-child(3){height:28%!important}.visual-evidence i:nth-child(4){height:64%!important}.visual-evidence i:nth-child(6){height:48%!important}.visual-evidence i:nth-child(7){height:24%!important}.visual-evidence i:nth-child(8){height:55%!important}.visual-evidence i:nth-child(9){height:38%!important}.visual-evidence i:nth-child(10){height:70%!important}.visual-evidence i:nth-child(11){height:31%!important}.rail-note a{display:inline-block;margin-top:9px;color:#222;font-size:8px}
.material-symbols-rounded{font-family:'Material Symbols Rounded';font-weight:normal;font-style:normal;font-size:18px;line-height:1;letter-spacing:normal;text-transform:none;display:inline-block;white-space:nowrap;word-wrap:normal;direction:ltr;font-feature-settings:'liga'}.brand{color:#191919;text-decoration:none}.workspace{padding-top:0}.rail-title,.title{height:69px!important;display:flex!important;align-items:center!important}.title{margin:0!important;font-size:42px!important}.kpis{height:58px;margin:0 0 24px!important}.kpi{height:58px!important;position:relative;cursor:default}.kpi-popover{position:absolute;left:0;top:56px;z-index:40;width:300px;max-height:340px;overflow:auto;padding:14px;border:1px solid #dededb;border-radius:17px;background:#fff;box-shadow:0 18px 40px rgba(0,0,0,.13);opacity:0;visibility:hidden;transform:translateY(5px);transition:.18s}.kpi:hover .kpi-popover{opacity:1;visibility:visible;transform:none}.kpi-popover h4{margin:0 0 8px;font-size:11px}.kpi-popover p{margin:8px 0 0;color:#777;font-size:9px;line-height:1.4}.kpi-popover ul{margin:0;padding:0;list-style:none}.kpi-popover li{display:flex;justify-content:space-between;gap:12px;padding:7px 0;border-top:1px solid #eee;font-size:9px;line-height:1.3}.kpi-popover li span{margin:0;padding:0;background:none!important;color:#666;font-size:9px}.kpi-popover li b{font:500 10px 'Courier New',monospace!important;letter-spacing:0!important}.kpi-label{display:flex!important;align-items:center;gap:5px}.status-dot{width:6px;height:6px;padding:0!important;border-radius:50%;background:#8f9691!important}.status-dot.good{background:#2c9b5c!important}.status-dot.warn{background:#e47d5d!important}.status-dot.info{background:#6486aa!important}.progress-card{min-height:105px;padding:14px 17px 12px;border:1px solid #dcdedb;border-radius:22px;background:#f8f8f6}.progress-head{display:flex;align-items:center;justify-content:space-between}.progress-head span{font-size:10px}.progress-head b{font:500 11px 'Courier New',monospace}.progress-path{display:flex;align-items:flex-start;margin-top:13px}.progress-segment{flex:1;min-width:0;position:relative;padding-top:11px}.progress-segment:before{content:'';position:absolute;left:0;right:0;top:4px;height:2px;background:#d6d9d5}.progress-segment:first-child:before{left:50%}.progress-segment:last-child:before{right:50%}.progress-segment i{position:absolute;left:50%;top:0;width:10px;height:10px;margin-left:-5px;border:2px solid #c3c7c2;border-radius:50%;background:#f8f8f6;z-index:2}.progress-segment.done:before,.progress-segment.done i{background:#2b8752;border-color:#2b8752}.progress-segment.current i{border-color:#2b8752;box-shadow:0 0 0 4px rgba(43,135,82,.13)}.progress-segment small,.progress-segment b{display:block;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.progress-segment small{color:#8b908c;font:7px 'Courier New',monospace}.progress-segment b{margin-top:2px;color:#777;font-size:7px;font-weight:400}.progress-card>small{display:block;margin-top:8px;color:#777;font-size:8px}.position-wrap{padding-top:73px!important}.position{height:118px!important;padding:15px 18px!important}.position-head h3{font-size:13px!important}.position-row{margin-top:13px!important}.position-row label{font-size:8px!important}.position-row input{font-size:9px!important}.work-grid{margin-top:22px!important;align-items:start}.finance-card{height:472px!important;min-height:0!important;align-self:start;position:sticky;top:12px}.finance-hero{height:156px!important}.finance-top{gap:9px!important}.finance-top small{font-size:7px;letter-spacing:.08em;margin-right:auto}.wallet-icon{width:auto!important;height:auto!important;border:0!important;border-radius:0!important;font:500 18px "Courier New",monospace!important;background:transparent!important}.finance-edit{display:inline-grid;place-items:center;margin-left:4px;background:transparent;color:inherit;text-decoration:none;vertical-align:middle}.finance-edit span{font-size:13px}.finance-hero p{margin-top:18px!important}.finance-caption{position:absolute;left:18px;bottom:17px;font-size:8px;color:rgba(255,255,255,.72)}.finance-copy{padding-top:14px!important}.finance-empty{margin:0 18px 8px;padding:10px;border:1px dashed #d6d8d5;border-radius:13px;color:#777;font-size:8px;line-height:1.4}.allocation{height:38px!important}.allocation>i.unfunded:after{background:#dfe1de!important}.signal-head{margin-top:30px!important}.signal>strong{font-size:28px!important;letter-spacing:-.04em!important}.signal>small{line-height:1.35;max-width:95%;font-size:9px!important}.avatar:before,.avatar:after{display:none!important}.avatar .material-symbols-rounded{font-size:20px}.rail-blueprint{display:block;margin-top:14px;padding:15px;border-radius:21px;background:#222a25;color:#fff;text-decoration:none;transition:.2s}.rail-blueprint:hover{transform:translateY(-3px);background:#171d19}.rail-blueprint span{font-size:20px;color:#dfff00}.rail-blueprint b{display:block;margin-top:18px;font-size:11px;font-weight:500}.rail-blueprint small{display:block;margin-top:5px;color:#9ca49e;font-size:8px;line-height:1.4}.rail-blueprint i{display:flex;align-items:center;gap:4px;margin-top:12px;color:#dfff00;font:8px 'Courier New',monospace;font-style:normal}
.signal.no-data>div[class^="visual-"]{opacity:.12!important}.signal.no-data>strong{font-family:-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif!important;font-size:20px!important;letter-spacing:-.03em!important}
.utility-links{display:grid;gap:2px;margin-top:13px;padding-top:11px;border-top:1px solid #d1d3d0}.utility-links a{height:30px;padding:0 9px;display:flex;align-items:center;gap:8px;border-radius:11px;color:#666;text-decoration:none;font-size:9px}.utility-links a:hover{background:#fff;color:#1b1d1c}.utility-links .material-symbols-rounded{font-size:15px}.signal.signal-evidence{background:#e8f2ff!important}.signal.signal-pricing{background:#fff0df!important}.signal.signal-difference{background:#eee8ff!important}.signal.signal-pain{background:#ffe8ef!important}.signal.signal-readiness{background:#e7f4e4!important}.signal.signal-competition{background:#fff6cc!important}
.overview{background:transparent!important;grid-template-columns:28px 1fr 18px!important}.overview i{font-style:normal;color:#888;opacity:0}.view-radio:checked+.overview{background:#fff!important}.view-radio:checked+.overview i{opacity:1}.phase-nav{grid-template-columns:27px minmax(0,1fr) auto 18px!important}.phase-nav small{color:#9a9d9a;font:8px 'Courier New',monospace}.view-radio:checked+.phase-nav small{color:#2b8752}.signal.fact-card{min-height:190px!important;background:#fff!important;border:1px solid #e2e3e0;opacity:1!important}.signal.fact-card .signal-title{display:grid!important;grid-template-columns:30px minmax(0,1fr) auto!important}.signal-status{font:7px 'Courier New',monospace;font-style:normal;letter-spacing:.05em;color:#7d827e}.signal.fact-card>strong{margin-top:25px!important}.fact-meter{position:absolute!important;left:18px!important;right:18px!important;bottom:17px!important;height:39px!important;display:flex!important;align-items:end!important;gap:5px!important}.fact-meter i{flex:1!important;background:#e2e4e1!important;border-radius:4px 4px 1px 1px!important;animation:none!important}.fact-card.blue .fact-meter i.filled,.fact-card.blue .signal-title>span{color:#426f9e;background:#dcebf8!important}.fact-card.green .fact-meter i.filled,.fact-card.green .signal-title>span{color:#26764b;background:#dbeee2!important}.fact-card.amber .fact-meter i.filled,.fact-card.amber .signal-title>span{color:#a55f20;background:#f5e2c8!important}.fact-card.violet .fact-meter i.filled,.fact-card.violet .signal-title>span{color:#715a9b;background:#e8e0f5!important}.fact-card.red .fact-meter i.filled,.fact-card.red .signal-title>span{color:#a44f43;background:#f3deda!important}.fact-card .signal-title>span{border:0!important}.fact-card.red .signal-status{color:#a44f43}.fact-card.green .signal-status{color:#26764b}.fact-card.amber .signal-status{color:#a55f20}
.progress-card{height:118px!important;min-height:0!important;padding:10px 16px 9px!important;overflow:hidden}.progress-head span{font-size:10px}.progress-head b{font-size:10px}.dot-tracker{height:88px;margin-top:0;display:grid;grid-template-columns:repeat(42,minmax(4px,1fr));gap:3px}.dot-column{height:88px;display:grid;grid-template-rows:repeat(7,1fr);gap:3px;cursor:default}.dot-column i{display:block;border-radius:2px;background:#e4e6e3;transition:.18s}.dot-column i.filled{background:#343a36}.dot-column i.current{background:#ef6f2f;box-shadow:0 0 0 2px rgba(239,111,47,.15)}.dot-column:hover i{filter:brightness(.94)}.tracker-labels{display:flex;justify-content:space-between;margin-top:4px;color:#8a8f8b;font:7px 'Courier New',monospace;letter-spacing:.06em}.position-wrap{padding-top:0!important}
</style>
<main class="app"><header class="topbar"><a class="brand" href="/">blueprint</a><div class="account"><a class="avatar" href="/Profile_Settings" aria-label="Profile"><span class="material-symbols-rounded">account_circle</span></a><a class="avatar" href="/?logout=1" aria-label="Sign out"><span class="material-symbols-rounded">logout</span></a></div></header><div class="layout"><aside class="rail"><div class="rail-title"><strong>Roadmap</strong><em>&amp;</em><span>Progress</span></div>__NAV__<div class="phase-list"></div><details class="rail-notes"><summary><span>⌑</span><b>Quick note</b></summary><form action="/Your_Plan"><textarea name="working_note" maxlength="1200" placeholder="A thought to revisit…">__WORKING_NOTE__</textarea><button type="submit">SAVE NOTE</button></form></details></aside><section class="workspace"><div class="hero"><div><h1 class="title">__TITLE__</h1><div class="kpis"><div class="kpi"><b>__COMP__%</b><span class="kpi-label">Completion</span><div class="kpi-popover"><h4>How completion is calculated</h4><ul><li><span>Meaningful setup points</span><b>__INPUT_COUNT__/__INPUT_TOTAL__</b></li><li><span>Roadmap actions</span><b>__DONE_COUNT__/__STEP_COUNT__</b></li><li><span>Total completed points</span><b>__TOTAL_DONE__/__TOTAL_POINTS__</b></li></ul><p>Setup context and completed actions contribute equally. Observed market proof is tracked separately.</p></div></div><div class="kpi"><b>__ASSUME__</b><span class="kpi-label">Open assumptions</span><div class="kpi-popover"><h4>All open assumptions</h4><ul>__ASSUME_TIP__</ul></div></div><div class="kpi"><b>__POS__</b><span class="kpi-label">Positive signals</span><div class="kpi-popover"><h4>All observed positive signals</h4><ul>__POS_TIP__</ul><p>__POS_FEEDBACK__</p></div></div><div class="kpi"><b>__RISK__</b><span class="kpi-label"><i class="risk-dot"></i>Open risks</span><div class="kpi-popover"><h4>All open risks</h4><ul>__RISK_TIP__</ul></div></div></div><div class="progress-card"><div class="dot-tracker">__DOT_TRACKER__</div><div class="tracker-labels"><span>DAY 01</span><span><i class="legend expected"></i>EXPECTED <i class="legend actual"></i>YOUR PATH</span><span>DAY 84</span></div></div></div><aside class="position-wrap"><div class="position"><div class="position-head"><h3>Your starting position</h3></div><div class="position-row"><label>Current stage<input value="__STAGE__"></label><label>Strongest signal<input value="__STRONGEST__"></label><label>Largest constraint<input value="__CONSTRAINT__"></label><label>Immediate next proof<input value="__NEXT_PROOF__"></label><a class="position-edit" href="/?edit_step=0" aria-label="Edit starting position">EDIT</a></div></div></aside></div>__VIEWS__</section></div></main>
"""
    page = page.replace(
        "</style>",
        """.status-dot{display:none!important}.hero{align-items:stretch!important}.position-wrap{padding:0!important;display:flex!important;align-items:flex-end!important}.position{height:118px!important;width:100%}.position-row{grid-template-columns:1fr 1fr!important}.position-row a{display:flex;align-items:end;justify-content:space-between;gap:8px;color:inherit;text-decoration:none}.position-row a:hover input{border-color:#4f5751}.position-row a>span{font-size:12px;color:#8a908b}.position-row input{pointer-events:none}.progress-card{height:118px!important;min-height:0!important;padding:10px 16px 9px!important}.progress-head{display:none!important}.dot-tracker{height:88px!important;margin-top:0!important;grid-template-columns:repeat(42,minmax(4px,1fr))!important;gap:3px!important}.dot-column{height:88px!important;grid-template-rows:repeat(7,1fr)!important;gap:3px!important}.dot-column i{background:#e4e6e3!important}.dot-column i.filled{background:#343a36!important}.dot-column i.current{background:#ef6f2f!important;box-shadow:0 0 0 2px rgba(239,111,47,.15)!important}.tracker-labels{margin-top:5px!important}.signal-wave,.signal-dots,.signal-range,.signal-ring{position:absolute;left:18px;right:18px;bottom:18px;height:42px}.signal-wave{display:flex;align-items:center;gap:5px}.signal-wave i{flex:1;border-radius:5px;background:#e0e3df}.signal-wave i.filled{background:#6c8173}.signal-dots{display:grid;grid-template-columns:repeat(12,1fr);gap:4px;align-content:end}.signal-dots i{height:7px;border-radius:2px;background:#e2e4e1}.signal-dots i.filled{background:#697b70}.signal-range{height:22px;bottom:25px;border-top:1px solid #bdc2bd}.signal-range:before,.signal-range:after{position:absolute;top:6px;color:#9a9e9a;font:7px 'DM Mono'}.signal-range:before{content:'LOW';left:0}.signal-range:after{content:'HIGH';right:0}.signal-range i{position:absolute;top:-5px;width:10px;height:10px;margin-left:-5px;border-radius:50%;background:#2c332e;box-shadow:0 0 0 5px rgba(44,51,46,.1)}.signal-ring{left:auto;width:45px;border-radius:50%;background:conic-gradient(#667a6d var(--value),#e1e4e0 0);display:grid;place-items:center}.signal-ring:after{content:'';position:absolute;width:31px;height:31px;border-radius:50%;background:#fff}.signal-ring b{z-index:1;font:7px 'DM Mono'}</style>""",
    )
    page = page.replace("@media(max-width:1180px)", "@media(max-width:900px)")
    page = page.replace('<span class="material-symbols-rounded">person</span>', '')
    page = page.replace('<span class="material-symbols-rounded">account_tree</span>', '<span class="blueprint-glyph">⌘</span>')
    page = page.replace('<span class="material-symbols-rounded">arrow_forward</span>', '→')
    page = page.replace('<span class="material-symbols-rounded">tune</span>', '<span class="nav-glyph">≋</span>')
    page = page.replace('<span class="material-symbols-rounded">database</span>', '<span class="nav-glyph">◫</span>')
    page = page.replace('<span class="material-symbols-rounded">article</span>', '<span class="nav-glyph">¶</span>')
    page = page.replace('</style>', '.avatar:before,.avatar:after{display:block!important}.nav-glyph,.blueprint-glyph{font-family:Arial,sans-serif!important}</style>')
    page = page.replace(
        '</style>',
        '''
.layout{grid-template-columns:232px minmax(0,1fr)!important}.phase-nav{height:45px!important;border-radius:18px!important}.phase-nav>span{width:19px!important;height:19px!important;font-size:8px!important}.phase-nav b{font-size:10px!important}.phase-list{margin-top:6px!important}.rail-blueprint{margin-top:12px!important;padding:13px!important}.rail-blueprint b{margin-top:10px!important}.rail-notes{margin-top:10px;border:1px solid #d3d5d1;border-radius:17px;background:#f3f3f1;overflow:hidden}.rail-notes summary{height:43px;padding:0 11px;display:grid;grid-template-columns:20px 1fr auto;align-items:center;gap:6px;list-style:none;cursor:pointer}.rail-notes summary::-webkit-details-marker{display:none}.rail-notes summary span{color:#767c77;font-size:15px}.rail-notes summary b{font-size:9px;font-weight:500}.rail-notes summary small{color:#a0a49f;font:6px 'Courier New',monospace}.rail-notes form{padding:0 10px 10px}.rail-notes textarea{width:100%;height:72px;padding:9px;border:1px solid #d8dad7;border-radius:11px;background:#fff;color:#333;font:9px/1.45 -apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial;resize:vertical}.rail-notes button{height:25px;margin-top:6px;padding:0 9px;border:0;border-radius:9px;background:#292e2b;color:#fff;font:7px 'Courier New',monospace}
.app:has(#view-8:checked) .view-8,.app:has(#view-9:checked) .view-9,.app:has(#view-10:checked) .view-10{display:block;animation:view-in .38s ease both}
.risk-dot{width:6px;height:6px;padding:0!important;border-radius:50%;background:#c95245!important;box-shadow:0 0 0 3px rgba(201,82,69,.1)}.progress-card{height:118px!important;padding:10px 16px 8px!important}.dot-tracker{height:88px!important}.dot-column i{background:transparent!important}.dot-column i.expected{background:#d7dad6!important}.dot-column i.actual{background:#f27435!important}.dot-column i.today{background:#f27435!important;box-shadow:0 0 0 2px rgba(242,116,53,.15)!important}.tracker-labels{align-items:center!important}.tracker-labels span:nth-child(2){display:flex;align-items:center;gap:5px}.legend{width:6px;height:6px;border-radius:2px}.legend.expected{background:#d7dad6}.legend.actual{margin-left:5px;background:#f27435}
.position{height:118px!important;padding:12px 15px!important}.position-head h3{font-size:12px!important}.position-row{position:relative;margin-top:8px!important;display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:7px 15px!important}.position-row label{min-width:0;font-size:7.5px!important}.position-row input{width:100%;margin-top:2px;padding:0 0 3px;border:0;border-bottom:1px solid #d5d8d4;background:transparent;color:#313632;font-size:9.5px!important;text-overflow:ellipsis}.position-edit{position:absolute;right:0;bottom:0;color:#717773;text-decoration:none;font:6px 'Courier New',monospace;letter-spacing:.08em}
.work-grid{grid-template-columns:minmax(0,1fr) 292px!important}.finance-card{height:auto!important;min-height:0!important;position:sticky;top:12px;border:0!important;border-radius:25px!important;background:linear-gradient(150deg,#ccdbe7 0,#efa76f 44%,#be6d57 100%)!important;color:#fff;overflow:hidden;box-shadow:0 16px 36px rgba(68,49,39,.13)}.finance-card:not([open]){height:292px!important}.finance-card summary{list-style:none;cursor:pointer}.finance-card summary::-webkit-details-marker{display:none}.finance-card .finance-hero{height:165px!important;background:transparent!important}.finance-top{align-items:center}.finance-edit{margin-left:auto!important;padding:0!important;color:rgba(255,255,255,.82)!important;font:7px 'Courier New',monospace!important;text-decoration:none}.finance-copy{padding:14px 18px 18px!important;background:transparent!important}.finance-copy h3,.finance-copy p{color:#fff!important}.finance-copy p{color:rgba(255,255,255,.72)!important}.finance-copy>span{display:flex;align-items:center;gap:6px;margin-top:12px;color:#fff;font:7px 'Courier New',monospace}.finance-copy>span i{width:7px;height:7px;border-right:1px solid currentColor;border-bottom:1px solid currentColor;transform:rotate(45deg);transition:.2s}.finance-card[open] .finance-copy>span i{transform:rotate(225deg)}.finance-expanded{padding:3px 18px 18px;background:transparent}.finance-empty{margin:0 0 10px!important;border-color:rgba(255,255,255,.35)!important;color:rgba(255,255,255,.82)!important}.allocation{border-color:rgba(255,255,255,.18)!important}.allocation b,.allocation span{color:#fff!important}.allocation small{color:rgba(255,255,255,.67)!important}.allocation>i{background:rgba(255,255,255,.22)!important}.allocation>i:after{background:#fff!important}.allocation>i.unfunded:after{background:transparent!important}
.signals{grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:13px!important}.signals:has(> .signal:nth-child(4):last-child){grid-template-columns:repeat(4,minmax(0,1fr))!important}.signal.fact-card{min-width:0!important;background:#fff!important;border-color:#dedfdd!important}.signal.fact-card .signal-title>span{background:#eceeeb!important;color:#59605a!important}.signal.fact-card.green .signal-title>span{background:#dfeee4!important;color:#28734a!important}.signal.fact-card.red .signal-title>span{background:#f3dfdb!important;color:#a3483f!important}.signal.fact-card.amber .signal-title>span{background:#f3e5d0!important;color:#9a5f26!important}.signal.fact-card.blue .signal-title>span,.signal.fact-card.violet .signal-title>span{background:#eceeeb!important;color:#59605a!important}.signal-status{color:#7b817c!important}.signal.fact-card.red .signal-status{color:#a3483f!important}.signal.fact-card.green .signal-status{color:#28734a!important}.signal-action{position:absolute;left:18px;bottom:20px;color:#9a5f26;font:7px 'Courier New',monospace;letter-spacing:.08em}.signal.fact-card:has(.signal-action)>strong{max-width:90%;font-family:-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial!important;font-size:20px!important;line-height:1.02!important;letter-spacing:-.045em!important}
.road-step{position:relative}.road-step summary{grid-template-columns:19px 26px minmax(0,1fr) auto 13px!important}.step-check{position:absolute;z-index:3;left:1px;top:18px;width:16px;height:16px;display:grid;place-items:center;border:1px solid #bfc4bf;border-radius:50%;color:#fff;text-decoration:none;font-size:8px}.road-step[open] .step-check{left:14px}.road-step.done .step-check{border-color:#2f8051;background:#2f8051}.road-step .chevron{width:7px;height:7px;border-right:1px solid #777;border-bottom:1px solid #777;transform:rotate(45deg);transition:.2s}.road-step[open] .chevron{transform:rotate(225deg)}
@media(max-width:1180px){.signals{grid-template-columns:repeat(2,minmax(0,1fr))!important}.layout{grid-template-columns:205px minmax(0,1fr)!important}.work-grid{grid-template-columns:minmax(0,1fr) 265px!important}}@media(max-width:900px){.layout{grid-template-columns:1fr!important}.rail{position:relative!important}.hero,.work-grid{grid-template-columns:1fr!important}.position-wrap{align-items:start!important}.signals{grid-template-columns:1fr!important}.finance-card{position:relative!important;width:100%}.rail-notes{max-width:320px}}
</style>''',
    )
    page = page.replace('<i class="status-dot info"></i>', '').replace('<i class="status-dot warn"></i>', '').replace('<i class="status-dot __POS_DOT__"></i>', '')
    page = page.replace(
        '<div class="progress-head"><span>Blueprint progress</span><b>__DONE_COUNT__ of __STEP_COUNT__ actions complete</b></div>',
        '',
    ).replace(
        '<div class="tracker-labels"><span>FOUNDATION</span><span>ORANGE = NEXT ACTION</span><span>LAUNCH</span></div>',
        '<div class="tracker-labels"><span>DAY 01</span><span>ORANGE = TODAY</span><span>DAY 42</span></div>',
    )
    page = page.replace(
        '<div class="position-head"><h3>Your starting position</h3><a class="edit" href="/Profile_Settings" aria-label="Edit starting position">✎</a></div><div class="position-row"><label>Target customer<input value="__CUSTOMER__"></label><label>Goal<input value="__GOAL__"></label><label>Weekly time<input value="__HOURS__ hrs"></label><label>Capital<input value="$__MONEY__"></label></div>',
        '<div class="position-head"><h3>Your starting position</h3></div><div class="position-row"><a href="/?edit_step=1"><label>Target customer<input value="__CUSTOMER__"></label><span>✎</span></a><a href="/?edit_step=3"><label>Success outcome<input value="__SUCCESS__"></label><span>✎</span></a><a href="/?edit_step=6"><label>Current work<input value="__CURRENT_WORK__"></label><span>✎</span></a><a href="/?edit_step=4"><label>Launch horizon<input value="__LAUNCH__"></label><span>✎</span></a></div>',
    )
    page = page.replace(
        '</style>',
        '''
.layout{grid-template-columns:250px minmax(0,1fr)!important;gap:30px!important}
.phase-nav{height:54px!important;padding:0 14px!important;border-radius:23px!important}.phase-nav>span{width:21px!important;height:21px!important;font-size:9px!important}.phase-nav b{font-size:11px!important}.phase-nav small{font-size:8px!important}
.rail-notes{position:relative;margin:16px 8px 0!important;border:0!important;border-radius:3px!important;background:#f6edc8!important;box-shadow:0 12px 25px rgba(55,49,28,.10),inset 0 0 28px rgba(163,139,66,.08)!important;overflow:visible!important;transform:rotate(-1deg)}
.rail-notes:before{content:'';position:absolute;z-index:2;left:50%;top:-8px;width:58px;height:17px;transform:translateX(-50%) rotate(1deg);background:rgba(225,220,202,.82);box-shadow:0 1px 3px rgba(0,0,0,.08)}
.rail-notes summary{height:48px!important;padding:8px 13px 0!important;grid-template-columns:18px 1fr!important}.rail-notes summary span{font-size:13px!important;color:#726b50!important}.rail-notes summary b{font-family:Georgia,serif!important;font-size:11px!important;font-weight:400!important}.rail-notes form{padding:0 12px 12px!important}.rail-notes textarea{height:68px!important;border:0!important;border-radius:0!important;background:transparent!important;padding:4px!important;font:11px/1.5 Georgia,serif!important;resize:none!important}.rail-notes button{height:24px!important;background:#4c4a3d!important}
.hero{align-items:start!important}.position-wrap{padding-top:70px!important;align-items:stretch!important}.position{height:142px!important;min-height:142px!important;max-height:142px!important;flex:none!important;width:100%!important;padding:15px 17px!important}.position-head h3{font-size:13px!important}.position-row{margin-top:13px!important;gap:12px 16px!important}.position-row input{font-size:9px!important}
.progress-card{height:62px!important;min-height:62px!important;margin-top:0!important;padding:7px 13px 7px!important;border-radius:18px!important}.dot-tracker{height:34px!important;display:grid!important;grid-template-columns:repeat(84,4px)!important;justify-content:space-between!important;gap:0!important}.dot-column{width:4px!important;height:34px!important;display:grid!important;grid-template-rows:repeat(7,4px)!important;gap:1px!important}.dot-column i{width:4px!important;height:4px!important;min-width:4px!important;border-radius:1px!important}.tracker-labels{margin-top:3px!important;font-size:5.5px!important}.legend{width:4px!important;height:4px!important}
.work-grid{grid-template-columns:minmax(0,1fr) 292px!important;align-items:start!important}.side-stack{position:sticky;top:12px;display:grid;gap:14px}.finance-card{position:relative!important;top:auto!important;height:auto!important;min-height:0!important;border:1px solid rgba(37,42,39,.08)!important;border-radius:27px!important;background:#fff!important;color:#202421!important;box-shadow:0 14px 32px rgba(54,57,55,.08)!important}.finance-card:not([open]){height:320px!important}.finance-card .finance-hero{height:177px!important;background:radial-gradient(circle at 75% 55%,#799fb3 0,#4f7688 28%,transparent 56%),radial-gradient(circle at 18% 82%,#b77950 0,#7e6259 34%,transparent 60%),linear-gradient(135deg,#7f9cad,#d7b990)!important;color:#fff!important}.finance-copy{padding:16px 19px 18px!important;background:#fff!important}.finance-copy h3{color:#202421!important;font-size:17px!important}.finance-copy p{color:#7e847f!important}.finance-copy>span{color:#59605b!important}.finance-expanded{padding:0 19px 18px!important;background:#fff!important}.finance-empty{color:#777!important;border-color:#d6d8d5!important}.allocation{border-color:#e4e5e2!important}.allocation b,.allocation span{color:#242825!important}.allocation small{color:#959a96!important}.allocation>i{background:#e5e7e4!important}.allocation>i:after{background:#3d5f4b!important}
.side-blueprint{display:block;padding:19px;border-radius:24px;background:#202823;color:#fff;text-decoration:none;box-shadow:0 14px 30px rgba(27,37,30,.12);transition:.2s}.side-blueprint:hover{transform:translateY(-2px)}.side-blueprint>span{color:#dfff00;font-size:20px}.side-blueprint b{display:block;margin-top:18px;font-size:13px}.side-blueprint small{display:block;margin-top:6px;color:#adb5af;font-size:8px;line-height:1.45}.side-blueprint i{display:block;margin-top:13px;color:#dfff00;font:7px 'Courier New',monospace;font-style:normal}
.road-step summary{grid-template-columns:26px minmax(0,1fr) auto 13px!important}.step-check,.check-slot{display:none!important}
.signals,.signals:has(> .signal:nth-child(4):last-child){grid-template-columns:repeat(6,minmax(145px,1fr))!important;gap:10px!important;overflow-x:auto;padding-bottom:5px}.signal.fact-card{min-height:174px!important;padding:15px!important;border-radius:23px!important}.signal.fact-card .signal-title{grid-template-columns:27px minmax(0,1fr) auto!important}.signal-title>span{width:27px!important;height:27px!important;font-size:12px!important}.signal-title>b{font-size:10px!important}.signal-status{font-size:6px!important}.signal.fact-card>strong{margin-top:25px!important;font-size:25px!important}.signal.fact-card>small{font-size:8px!important}.signal>div[class^="visual-"],.fact-meter{left:15px!important;right:15px!important;bottom:14px!important;height:32px!important}
@media(max-width:1180px){.layout{grid-template-columns:225px minmax(0,1fr)!important}.signals,.signals:has(> .signal:nth-child(4):last-child){grid-template-columns:repeat(6,minmax(140px,1fr))!important}.work-grid{grid-template-columns:minmax(0,1fr) 270px!important}}
</style>''',
    )
    page = page.replace(
        '<span class="kpi-label">Positive signals</span>',
        '<span class="kpi-label"><i class="positive-dot __POS_DOT__"></i>Positive signals</span>',
    )
    page = page.replace(
        '<div class="tracker-labels"><span>DAY 01</span><span><i class="legend expected"></i>EXPECTED <i class="legend actual"></i>YOUR PATH</span><span>DAY 84</span></div>',
        '<div class="tracker-labels"><span>DAY 01</span><span>DAY 84</span><span class="tracker-legend"><i class="legend expected"></i>EXPECTED <i class="legend actual"></i>YOUR PATH</span></div>',
    )
    page = page.replace(
        '<a class="position-edit" href="/?edit_step=0" aria-label="Edit starting position">EDIT</a>',
        '<a class="position-edit" href="/?edit_step=0" aria-label="Edit starting position"><span class="material-symbols-rounded">edit</span></a>',
    )
    page = page.replace(
        '</style>',
        '''
.kpis{height:58px!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:16px!important;margin:0 0 12px!important}.kpi{height:58px!important;padding:0!important;border:0!important;border-radius:0!important;background:transparent!important;display:flex!important;flex-direction:row!important;align-items:center!important;justify-content:flex-start!important;gap:8px!important}.kpi b{font-size:36px!important;line-height:1!important}.kpi .kpi-label{align-self:flex-start!important;margin-top:4px!important;padding:5px 8px!important;background:#fff!important;font-size:8px!important}.kpi:first-child .kpi-label{background:#dfff00!important;color:#334000!important;box-shadow:0 0 0 3px rgba(223,255,0,.16)}.positive-dot{display:none;width:6px;height:6px;padding:0!important;border-radius:50%;background:#2c9b5c!important;box-shadow:0 0 0 3px rgba(44,155,92,.1)}.positive-dot.good{display:inline-block}
.position-wrap{padding-top:69px!important}.position{height:132px!important;min-height:132px!important;max-height:132px!important;padding:17px 18px!important}.position-head h3{font-size:14px!important;letter-spacing:-.025em}.position-row{margin-top:15px!important;gap:13px 17px!important}.position-row label{font-size:9px!important;color:#737a74!important}.position-row input{font-size:11px!important;color:#252a26!important}.position-edit{right:0!important;top:-39px!important;bottom:auto!important;width:22px;height:22px;display:grid;place-items:center;border-radius:50%;background:#f0f1ee;color:#5e655f!important;transform:none!important}.position-edit span{font-size:13px!important;transform:none!important}
.tracker-labels{display:grid!important;grid-template-columns:auto auto 1fr!important;align-items:center!important;gap:14px!important}.tracker-labels span:nth-child(2){display:block!important}.tracker-legend{justify-self:end;display:flex!important;align-items:center;gap:5px}.work-grid{margin-top:18px!important}.side-stack{gap:12px!important}.side-blueprint{height:188px;position:relative;padding:23px 21px!important;border:1px solid rgba(114,210,151,.2);border-radius:27px!important;background:linear-gradient(145deg,#18211c 0%,#202d25 58%,#162019 100%)!important;overflow:hidden}.side-blueprint:before{content:'';position:absolute;right:-30px;top:17px;width:165px;height:84px;background:repeating-linear-gradient(165deg,transparent 0 16px,rgba(105,220,147,.24) 17px 18px);transform:rotate(-4deg)}.side-blueprint>*{position:relative;z-index:1}.side-blueprint>span{font-size:21px!important}.side-blueprint b{max-width:210px;margin-top:28px!important;font-size:17px!important;line-height:1.05;letter-spacing:-.035em}.side-blueprint small{max-width:225px;margin-top:8px!important;font-size:8px!important}.side-blueprint i{display:inline-flex!important;align-items:center;min-height:29px;margin-top:14px!important;padding:0 11px;border:1px solid rgba(223,255,0,.6);border-radius:15px;background:rgba(223,255,0,.08);color:#dfff00!important;font-size:7px!important;letter-spacing:.04em}.finance-card{position:relative!important;height:auto!important;min-height:0!important;border:0!important;border-radius:27px!important;background:radial-gradient(circle at 78% 35%,rgba(105,154,177,.92),transparent 42%),radial-gradient(circle at 16% 85%,rgba(177,106,68,.92),transparent 48%),linear-gradient(135deg,#7d8290,#ac765c)!important;color:#fff!important;box-shadow:0 16px 34px rgba(63,50,43,.14)!important}.finance-card:not([open]){height:190px!important}.finance-card .finance-hero{height:111px!important;padding:17px 18px!important;background:transparent!important;color:#fff!important}.finance-hero strong{display:block;margin-top:20px;font-size:28px!important}.finance-hero p,.finance-caption{display:none!important}.wallet-icon{width:auto!important;height:auto!important;border:0!important;border-radius:0!important;font-size:18px!important}.finance-top small{margin-left:8px;font-size:7px}.finance-edit{width:25px;height:25px;display:grid!important;place-items:center;border-radius:50%;background:rgba(255,255,255,.18)!important}.finance-edit span{font-size:13px!important}.finance-copy{padding:11px 18px 16px!important;background:transparent!important}.finance-copy h3{color:#fff!important;font-size:15px!important}.finance-copy p{display:none!important}.finance-copy>span{margin-top:6px!important;color:rgba(255,255,255,.88)!important;font-size:7px!important}.finance-expanded{padding:0 18px 16px!important;background:transparent!important}.allocation{height:39px!important;border-color:rgba(255,255,255,.24)!important}.allocation div b,.allocation span{color:#fff!important;font-size:9px!important}.allocation div small{display:block!important;max-width:175px;color:rgba(255,255,255,.7)!important;font-size:6px!important}.allocation>i{background:rgba(255,255,255,.2)!important}.allocation>i:after{background:#fff!important}
.overview-icon{width:17px;height:17px;padding:2px!important;display:grid!important;grid-template-columns:repeat(2,5px);grid-template-rows:repeat(2,5px);gap:2px;border:1px solid #aeb4af;border-radius:5px}.overview-icon i{display:block!important;width:5px;height:5px;border-radius:1.5px;background:#656d67!important;opacity:1!important}.avatar{position:relative!important;text-decoration:none!important}.avatar .material-symbols-rounded{display:none!important}.avatar:before{content:''!important;display:block!important;position:absolute;left:13px;top:6px;width:8px;height:8px;border:1.5px solid #303532;border-radius:50%}.avatar:after{content:''!important;display:block!important;position:absolute;left:8px;bottom:5px;width:18px;height:10px;border:1.5px solid #303532;border-bottom:0;border-radius:12px 12px 0 0}.position-edit{top:-41px!important}.position-edit span{font-size:14px!important}
.road-step summary{grid-template-columns:26px minmax(0,1fr) auto 13px!important}.completion-action{display:inline-flex;align-items:center;gap:6px;padding:5px 8px;border:1px solid #d0d4d0;border-radius:14px;color:#69706a;text-decoration:none;font:7px 'Courier New',monospace;white-space:nowrap;transition:.18s}.completion-action i{width:12px;height:12px;border:1px solid #aeb5af;border-radius:4px;background:#fff}.completion-action:hover{border-color:#2f8051;color:#2f8051;background:#f3f8f4}.road-step.done .completion-action{border-color:#2f8051;background:#e1eee5;color:#246840}.road-step.done .completion-action i{position:relative;border-color:#2f8051;background:#2f8051}.road-step.done .completion-action i:after{content:'';position:absolute;left:3px;top:1px;width:4px;height:7px;border-right:1.5px solid #fff;border-bottom:1.5px solid #fff;transform:rotate(45deg)}.road-step.done .node{border-color:#2f8051;color:#2f8051}
.rail-notes summary{height:72px!important}.rail-notes form{padding-bottom:15px!important}.rail-notes textarea{height:92px!important}
.signals{width:100%!important;grid-template-columns:repeat(6,minmax(0,1fr))!important;gap:13px!important;overflow:visible!important}.signals:has(> .signal:nth-child(5):last-child){grid-template-columns:repeat(5,minmax(0,1fr))!important}.signals:has(> .signal:nth-child(4):last-child){grid-template-columns:repeat(4,minmax(0,1fr))!important}.signals:has(> .signal:nth-child(3):last-child){grid-template-columns:repeat(3,minmax(0,1fr))!important}.signal.fact-card{min-width:0!important;min-height:198px!important}.signal.fact-card .signal-title{display:grid!important;grid-template-columns:28px minmax(0,1fr)!important;align-items:center!important;gap:8px!important}.signal.fact-card .signal-title>span{display:grid!important;place-items:center!important;font-size:15px!important}.signal-status{display:block!important;margin:7px 0 0 36px!important;font-size:6px!important;font-style:normal!important;letter-spacing:.06em;text-align:left!important}.signal.fact-card>strong{margin-top:12px!important}.signal.fact-card>small{display:block!important;margin-top:5px!important;max-height:30px;line-height:1.35!important;overflow:hidden}.signal>div[class^="signal-"],.signal .signal-wave,.signal .signal-dots,.signal .signal-ring{bottom:8px!important}.signal .signal-range{bottom:3px!important}
@media(max-width:1180px){.kpis{grid-template-columns:repeat(4,minmax(110px,1fr))!important;overflow-x:auto}.position-wrap{display:none!important}}
</style>''',
    )
    positive_items = [(row.get("metric_name", "Positive observation").replace("_", " ").title(), row.get("metric_value", "LOGGED")) for row in evidence_events if row.get("signal_direction", "").lower() == "positive"]
    if not positive_items:
        positive_items = [("No positive behavior has been logged yet", "0")]
    goal_labels = {
        "get_job": "Build skills for a job", "side_income": "Create side income", "small_business": "Build a small business",
        "startup": "Build a startup", "raise_money": "Prepare to raise money", "just_explore": "Explore or learn",
    }
    raw_goal = str(_get(profile, "goal", "Not captured") or "Not captured")
    customer_label = target_customer.strip() or "Not captured"
    if len(customer_label) > 30:
        customer_label = customer_label[:27].rstrip() + "…"
    goal_label = goal_labels.get(raw_goal, raw_goal.replace("_", " ").title())
    success_label = success_definition.split(":", 1)[0].strip() if success_definition else "Not captured"
    stage_label = next((phase["phase_name"] for phase in phases if int(phase["phase_order"]) == active_phase_order), "Foundation")
    total_points = len(input_checks) + roadmap_total
    total_done = input_count + roadmap_done
    current_work_label = current_work.strip() or "Nothing started yet"
    if len(current_work_label) > 30:
        current_work_label = current_work_label[:27].rstrip() + "…"
    launch_label = str(_get(profile, "launch_timeline", "Not captured") or "Not captured")
    strongest_label = positive_items[0][0] if positives else ("Founder context captured" if background or current_work else "No evidence logged")
    constraint_label = str(constraints[0]) if constraints else "No constraint captured"
    readiness_label = "Ready for first proof" if profile_strength >= 75 else "Needs founder context" if profile_strength < 50 else "Path can be refined"
    next_proof_label = next((step["name"] for step in steps if f'{step["phase"]}-1' not in completed), "Review the next decision gate")
    working_note = str(st.session_state.get("working_note", ""))
    tokens = {"__TITLE__": html.escape(project_title), "__NAV__": "".join(nav), "__VIEWS__": "".join(views), "__COMP__": str(completion), "__PROFILE__": str(profile_strength), "__EXEC__": str(execution_completion), "__INPUT_COUNT__": str(input_count), "__INPUT_TOTAL__": str(len(input_checks)), "__DONE_COUNT__": str(roadmap_done), "__STEP_COUNT__": str(roadmap_total), "__TOTAL_DONE__": str(total_done), "__TOTAL_POINTS__": str(total_points), "__ASSUME__": str(assumptions), "__POS__": str(positives), "__RISK__": str(risks), "__CLARITY__": str(clarity), "__STRONGEST__": html.escape(strongest_label), "__STRONGEST_SCORE__": str(strongest_signal[1]), "__ASSUME_TIP__": tooltip(assumption_items), "__POS_TIP__": tooltip(positive_items), "__RISK_TIP__": tooltip(risk_items), "__POS_DOT__": "good" if positives else "warn", "__POS_FEEDBACK__": "Observed positive evidence exists." if positives else "Complete the first interview or test and log the result to create a real signal.", "__DOT_TRACKER__": dot_tracker, "__CUSTOMER__": html.escape(customer_label), "__GOAL__": html.escape(goal_label), "__SUCCESS__": html.escape(success_label), "__STAGE__": html.escape(stage_label), "__CURRENT_WORK__": html.escape(current_work_label), "__LAUNCH__": html.escape(launch_label), "__CONSTRAINT__": html.escape(constraint_label), "__READINESS__": html.escape(readiness_label), "__NEXT_PROOF__": html.escape(next_proof_label), "__WORKING_NOTE__": html.escape(working_note), "__MONEY__": f"{money:,}", "__HOURS__": str(weekly_hours), "__DAYS__": str(total_days), "__READY__": str(readiness)}
    for key, value in tokens.items(): page = page.replace(key, value)
    page = page.replace(
        '<button class="edit" aria-label="Edit starting position">⌁</button>',
        '<a class="edit" href="/Profile_Settings" aria-label="Edit starting position"><span class="material-symbols-rounded">edit</span></a>',
    )
    st.html("".join(line.strip() for line in page.splitlines()))
