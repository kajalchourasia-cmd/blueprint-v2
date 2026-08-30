"""Shared eight-step Blueprint onboarding dialog.

The dialog can be opened from either the landing page or the empty dashboard
without changing routes. Its frame and navigation remain fixed while only the
question body changes.
"""

from __future__ import annotations

import streamlit as st

from blueprint.backend import BackendError, make_idempotency_key, start_blueprint
from blueprint.schemas import UserProfile


def _create_profile(answers: dict) -> UserProfile:
    goal_codes = {
        "Build a profitable business": "small_business",
        "Replace my current income": "get_job",
        "Create a side income": "side_income",
        "Turn an idea into a real product": "startup",
        "Build a large company": "startup",
        "Build a brand / community": "just_explore",
        "Test whether an idea can work": "just_explore",
        "Create something I eventually want to sell": "startup",
        "Solve a problem I care about": "just_explore",
        "Build it for the experience / vibes": "just_explore",
        "Other": "just_explore",
    }
    location = answers.get("location_detail") or answers.get("location", "Not sure")
    customer = ", ".join(answers.get("target_customer", []))
    if answers.get("customer_detail"):
        customer = f"{customer}; {answers['customer_detail']}"
    goal_label = answers.get("goal", "Test whether an idea can work")
    selected_type = answers.get("idea_type", "Not sure")
    idea_types = {selected_type} if isinstance(selected_type, str) else set(selected_type)
    idea_type = "saas" if "App / Software" in idea_types else "service" if "Service" in idea_types else "physical_business" if "Physical store" in idea_types else "other"
    return UserProfile(
        idea=answers.get("idea", ""),
        idea_type=idea_type,
        location=location,
        target_customer=customer,
        background=answers.get("goal_detail", ""),
        life_context=answers.get("constraints", []),
        goal=goal_codes.get(goal_label, "just_explore"),
        success_definition=(f"{answers.get('success_type')}: {answers.get('success_definition', '')}" if answers.get("success_type") else ""),
        launch_timeline=answers.get("launch_timeline", ""),
        current_work=", ".join(answers.get("prior_work", [])) + (f"; {answers.get('current_work')}" if answers.get("current_work") else ""),
        constraints=answers.get("constraints", []),
        hours_per_week=answers.get("hours_per_week", 0),
        money_available=answers.get("money_available", 0),
    )


@st.dialog("Help us understand you better", width="small")
def questions_dialog() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stDialog"]>div{height:min(680px,calc(100vh - 96px))!important;min-height:min(680px,calc(100vh - 96px))!important;max-height:min(680px,calc(100vh - 96px))!important;overflow:hidden!important;border-radius:28px!important;background:#f7f7f5!important}
        [data-testid="stDialog"]>div>div{height:100%!important;overflow:hidden!important}
        [data-testid="stDialog"] [data-testid="stVerticalBlock"]{gap:8px!important}
        .wizard-intro{margin:-8px 0 4px;color:#757c76;font:10px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}.wizard-kicker{color:#1c201d;font:650 17px/1.25 -apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}.wizard-number{display:block;margin-bottom:6px;color:#7f8680;font:8px monospace;letter-spacing:.1em}.wizard-required{margin:6px 0 0;color:#858b86;font:9px monospace}.wizard-dots{display:grid;grid-template-columns:repeat(8,1fr);gap:6px;margin:17px 0 18px}.wizard-dots span{height:4px;border-radius:4px;background:#e0e2df}.wizard-dots span.active,.wizard-dots span.done{background:#2f8051}
        .st-key-wizard_body{height:315px!important;min-height:315px!important;max-height:315px!important;padding:4px 4px 8px 0!important;overflow-y:auto!important;scrollbar-gutter:stable}
        [data-testid="stDialog"] [data-testid="stTextArea"] textarea,[data-testid="stDialog"] [data-testid="stTextInput"] input,[data-testid="stDialog"] [data-baseweb="select"]>div{border-radius:13px!important;background:#fff!important;border-color:#d2d6d2!important}
        [data-testid="stDialog"] [data-testid="stPills"] button{min-height:30px!important;padding:5px 10px!important;border-radius:15px!important;border:1px solid #d4d7d3!important;background:#fff!important;color:#555b57!important;font-size:10px!important}[data-testid="stDialog"] [data-testid="stPills"] button[aria-pressed="true"]{border-color:#397e57!important;background:#e2eee5!important;color:#205d3b!important}
        .wizard-nav{margin-top:auto}.generation{text-align:center;padding:65px 10px 22px}.generation-orbit{width:78px;height:78px;margin:0 auto 22px;position:relative;border:1px solid #c8ccc8;border-radius:50%;animation:wizardSpin 2.2s linear infinite}.generation-orbit:before,.generation-orbit:after{content:'';position:absolute;border-radius:50%}.generation-orbit:before{width:15px;height:15px;left:4px;top:13px;background:#2f8051;box-shadow:48px 30px 0 #c8dff0}.generation-orbit:after{width:7px;height:7px;left:34px;top:34px;background:#1d201e;box-shadow:0 0 0 10px rgba(47,128,81,.1)}.generation h3{margin:0;font:650 27px/1.1 -apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}.generation p{color:#777d78;font-size:12px}.generation-lines{display:grid;gap:7px;margin-top:24px}.generation-lines i{height:4px;border-radius:4px;background:#e1e3e0;overflow:hidden}.generation-lines i:after{content:'';display:block;width:45%;height:100%;background:#2f8051;animation:wizardScan 1.2s ease-in-out infinite}.generation-lines i:nth-child(2):after{animation-delay:.2s}.generation-lines i:nth-child(3):after{animation-delay:.4s}@keyframes wizardSpin{to{transform:rotate(360deg)}}@keyframes wizardScan{0%{transform:translateX(-110%)}100%{transform:translateX(240%)}}
        @media(max-height:700px){[data-testid="stDialog"]>div{height:calc(100vh - 72px)!important;min-height:calc(100vh - 72px)!important;max-height:calc(100vh - 72px)!important}.st-key-wizard_body{height:270px!important;min-height:270px!important;max-height:270px!important}}
        </style>
        """,
        unsafe_allow_html=True,
    )
    if generation_error := st.session_state.get("generation_error"):
        st.error(generation_error)
        if st.button("Retry safely", key="retry_blueprint_start_shared", use_container_width=True):
            st.session_state["generation_error"] = None
            st.session_state["generating_blueprint"] = True
            st.rerun()
    if st.session_state.get("generating_blueprint"):
        answers = st.session_state["dialog_answers"]
        st.markdown('<div class="generation"><div class="generation-orbit"></div><h3>Starting your evidence Blueprint</h3><p>Saving your founder context, creating the owned research run, and handing it to the Supervisor.</p><div class="generation-lines"><i></i><i></i><i></i></div></div>', unsafe_allow_html=True)
        profile = _create_profile(answers)
        idempotency_key = st.session_state.setdefault("backend_idempotency_key", make_idempotency_key())
        try:
            start_result = start_blueprint(profile, answers, idempotency_key=idempotency_key)
        except BackendError as exc:
            st.session_state["generating_blueprint"] = False
            st.session_state["generation_error"] = str(exc)
            st.error(str(exc))
            st.caption("Your onboarding answers are preserved. Retry uses the same idempotency key and cannot create a duplicate run.")
            return
        st.session_state.update({
            "profile": profile,
            "backend_project_id": start_result["project_id"],
            "backend_run_id": start_result["run_id"],
            "backend_start_result": start_result,
            "backend_bundle": None,
            "backend_last_refresh_at": 0,
            "show_questions": False,
            "generating_blueprint": False,
            "generation_error": None,
            "bp_selected_section": "foundation",
            "bp_auto_selected_run_id": start_result["run_id"],
        })
        st.session_state.setdefault("projects", {})[profile.idea or "Untitled project"] = {"profile": profile, "project_id": start_result["project_id"], "run_id": start_result["run_id"]}
        st.rerun()

    options = ["Business", "Product", "App / Software", "Service", "Physical store", "Online business", "Community", "Not sure"]
    goals = ["Build a profitable business", "Replace my current income", "Create a side income", "Turn an idea into a real product", "Build a large company", "Build a brand / community", "Test whether an idea can work", "Create something I eventually want to sell", "Solve a problem I care about", "Build it for the experience / vibes", "Other"]
    timelines = ["Within 30 days", "Within 3 months", "Within 6 months", "Within 12 months", "No fixed date", "Not sure"]
    contexts = ["Full-time job", "Caregiving", "School", "Debt or financial pressure", "Health constraint", "Relocation", "Need predictable income", "No major constraint"]
    customer_types = ["Individual consumers", "Families", "Students", "Professionals", "Small businesses", "Large companies", "Creators", "Communities", "Not sure"]
    prior_work = ["Nothing yet", "Read or watched research", "Talked to potential customers", "Built a prototype", "Created a landing page", "Made a sale", "Ran an experiment", "Compared competitors"]
    questions = ["What are you building?", "Who is it for, and where?", "Why are you building it?", "What does success look like?", "How much can you invest?", "How much time can you give?", "What have you already done?", "What are your biggest constraints?"]
    answers = st.session_state.setdefault("dialog_answers", {"idea": st.session_state.get("idea", "")})
    q = st.session_state.setdefault("dialog_question", 0)
    st.markdown("<div class='wizard-intro'>Eight quick questions will make the Blueprint specific to your context.</div>", unsafe_allow_html=True)
    st.markdown("<div class='wizard-dots'>" + "".join(f"<span class='{'active' if i == q else 'done' if i < q else ''}'></span>" for i in range(8)) + "</div>", unsafe_allow_html=True)
    question_col, skip_top = st.columns([4, 1])
    question_col.markdown(f"<span class='wizard-number'>QUESTION {q + 1:02d} OF 08</span><div class='wizard-kicker'>{questions[q]}</div><div class='wizard-required'>Optional — answer what you know and refine it later</div>", unsafe_allow_html=True)
    if skip_top.button("Skip", key=f"shared_skip_{q}", use_container_width=True):
        st.session_state["dialog_question"] = q + 1 if q < 7 else q
        if q == 7:
            st.session_state["generating_blueprint"] = True
        st.rerun()
    with st.container(key="wizard_body"):
        if q == 0:
            answers["idea"] = st.text_area("What do you want to build?", value=answers.get("idea", ""), placeholder="Tell us in your own words. It can still be vague.", height=68)
            current_type = answers.get("idea_type", "Not sure")
            if isinstance(current_type, list):
                current_type = current_type[0] if current_type else "Not sure"
            answers["idea_type"] = st.selectbox("What kind of thing is it?", options, index=options.index(current_type) if current_type in options else options.index("Not sure"))
            research_options = ["Customer research", "Competitor research", "Market research"]
            answers["research_selection"] = st.pills("What should Blueprint research first?", research_options, default=answers.get("research_selection", research_options), selection_mode="multi")
        elif q == 1:
            answers["target_customer"] = st.pills("Who do you want to build this for?", customer_types, default=answers.get("target_customer", []), selection_mode="multi")
            answers["customer_detail"] = st.text_input("Anything specific about them?", value=answers.get("customer_detail", ""), placeholder="Optional: busy professionals who train at home")
            location_options = ["India", "United States", "United Kingdom", "Other country", "Specific city / region", "Online / global", "Not sure"]
            answers["location"] = st.selectbox("Where do you want to build or sell it?", location_options, index=location_options.index(answers.get("location", "Not sure")))
            answers["location_detail"] = st.text_input("City or region", value=answers.get("location_detail", ""), placeholder="Optional: Pune, Austin, or a target country")
        elif q == 2:
            answers["goal"] = st.selectbox("What do you want this to do for you?", goals, index=goals.index(answers.get("goal", goals[6])))
            journey_modes = ["Serious business", "Side project", "Creative experiment", "Just for the vibes"]
            answers["journey_mode"] = st.selectbox("How do you want this journey to feel?", journey_modes, index=journey_modes.index(answers.get("journey_mode", "Serious business")))
            answers["goal_detail"] = st.text_area("Anything else you want this project to give you?", value=answers.get("goal_detail", ""), height=65)
        elif q == 3:
            success_options = ["First paying customers", "Replace my current income", "Reliable side income", "Launch a working product", "Reach a revenue target", "Create measurable impact", "Build an audience or community", "Not sure"]
            answers["success_type"] = st.selectbox("If this works, what would success look like?", success_options, index=success_options.index(answers.get("success_type", "Not sure")))
            answers["success_definition"] = st.text_input("What would make that success concrete?", value=answers.get("success_definition", ""), placeholder="Optional: 100 weekly active users")
        elif q == 4:
            money = min(200000, max(0, round(int(answers.get("money_available", 5000) or 0) / 2500) * 2500))
            answers["money_available"] = st.slider("How much can you invest?", 0, 200000, money, step=2500)
        elif q == 5:
            answers["hours_per_week"] = st.slider("How much time can you give each week?", 0, 40, answers.get("hours_per_week", 5))
            answers["launch_timeline"] = st.selectbox("When do you want to launch or test it?", timelines, index=timelines.index(answers.get("launch_timeline", "Not sure")))
        elif q == 6:
            answers["prior_work"] = st.pills("What have you already done?", prior_work, default=answers.get("prior_work", []), selection_mode="multi")
            answers["current_work"] = st.text_input("Anything important to add?", value=answers.get("current_work", ""), placeholder="Optional detail")
        else:
            answers["constraints"] = st.pills("What could constrain you?", contexts, default=answers.get("constraints", []), selection_mode="multi")
    back, next_col = st.columns([1, 1.45])
    if back.button("← Back", disabled=q == 0, use_container_width=True, key=f"shared_back_{q}"):
        st.session_state["dialog_question"] = max(0, q - 1)
        st.rerun()
    label = "Generate my Blueprint →" if q == 7 else "Continue →"
    if next_col.button(label, type="primary", use_container_width=True, key=f"shared_next_{q}"):
        if q == 0 and len(str(answers.get("idea", "")).strip()) < 10:
            st.warning("Describe the idea in at least one clear sentence.")
        elif q == 0 and not answers.get("research_selection"):
            st.warning("Select at least one research stream.")
        elif q < 7:
            st.session_state["dialog_question"] = q + 1
            st.rerun()
        else:
            st.session_state["generating_blueprint"] = True
            st.rerun()
