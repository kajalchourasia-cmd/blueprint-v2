# Phase 7 — Closed Streamlit-to-n8n Blueprint Path

Last verified: 30 August 2026

## Outcome

The evaluator-facing path now begins on the existing Blueprint landing page with no email, password, account, login, logout, or name form. Streamlit silently creates a unique Supabase anonymous user. That user receives a normal authenticated JWT, so the existing owner-scoped RLS and n8n authorization boundary remain intact.

The local main path is:

`Landing → eight-question onboarding → authenticated BP-API-01 start → BP-00 Supervisor → staged planner → stage-scoped scheduler → typed specialists → independent audit → deterministic verdict → immutable Research Blueprint → founder checkpoint → Stage 2 → Gate 2 → advisory Action Blueprint`.

## UI contract

- Four persistent KPIs: verdict/score, evidence coverage, open risks, and Blueprint completion.
- Left: Stage 1, Stage 2, and Stage 3 section threads with not-started, queued, running, completed, error/needs-input, and locked states.
- Center: selected section executive finding, detailed evidence-labelled output, and section-specific Ask this Research history.
- Right: contextual founder actionables, scoped sources, background-process state, and approval-gated research rerun.
- Stage 2 stays locked until the founder resolves Gate 1. Stage 3 stays locked until Gate 2 is resolved.
- The `Full Blueprint` route opens the same live workspace focused on the Action Blueprint instead of the obsolete static map.

## Agentic closure

Gate 1 resolution is sent to `BP-API-03 Founder Checkpoint and Resume`, which calls the durable HITL workflow and—only for an allowed continue decision—resumes the same `BP-00` Supervisor with `PROVE_AND_DESIGN`. Gate 2 uses the same endpoint and resumes with `COMPLETE_ACTION_BLUEPRINT`. Pause/cancel records the decision and performs no autonomous continuation.

Stage 2 selects only goal-relevant modules. Stage 3 provides MVP boundary, first-customer route, distribution, financial scenarios, milestones, and growth prerequisites. It does not execute a launch or manufacture weekly actions.

## Live evidence

- A fresh anonymous browser session opened the landing page without any sign-in surface.
- All three research streams were selected by default during onboarding.
- Live run `e9990a5e-d3e8-4e97-ad8a-18c6151a3834` progressed through foundation, customer, competitor, market, independent audit, deterministic verdict, Research Blueprint synthesis, and a visible founder gate.
- The workspace showed queued/running/completed states, detailed customer research, sources, limitations, unknowns, contextual actions, and the section chat input.
- The first smoke run exposed an oversized scheduler allowlist. It failed safely, the generator was corrected to send 7 Discover, 6 Prove-and-Design, or 3 Action-Blueprint modules, and the second live run completed Stage 1.
- The second smoke run exposed a misleading 99/100 result caused by treating research completeness as commercial viability. The auditor now labels `DESK_RESEARCH_ONLY`, detects the absence of direct interviews/behavior/commitments/payments, caps desk-only viability below 60, and creates a targeted-validation blocker. This correction is published for subsequent runs; the historical smoke-test verdict remains immutable.

## Automated evidence

- Python auth/backend contracts: 11/11 pass.
- Staged planner branch regressions: 7/7 pass.
- Phase 7 closed-loop contracts: 17/17 pass, including guest ownership, resume routing, stage allowlists, section-scoped chat, deterministic finance, checkpoint authentication, and the desk-research viability ceiling.
- Structural validation reports valid JSON, unique node names, no missing targets, and no Code-node syntax errors for the modified workflows.

## Deliberately pending human acceptance

The real Gate 1 `PROCEED` click was not automated. The checkpoint exists specifically because continuing writes new task plans and state. A founder/evaluator must choose the allowed decision in the popup. After that click, the live Stage 2 and Gate 2 journey must be observed once; the Stage 2/3 workflow and its safe fixtures are already built and published.

Public Streamlit deployment is also pending. Streamlit Community Cloud cannot reach `localhost:5679`; n8n needs a public HTTPS endpoint before the repository should be deployed as the final demo.

