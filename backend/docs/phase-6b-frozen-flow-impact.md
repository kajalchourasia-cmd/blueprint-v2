# Phase 6B — Frozen Flow Change Impact

Date: 30 August 2026  
Purpose: exact implementation delta created by the later founder-flow decision

## What remains valid

- Supabase migrations 009–010: versioned profiles, task graph, observations, checkpoints, actions, signals, reruns, memory projections, atomic plan persistence, ready-task claiming, and dependency unlocking.
- `BP-PLAN-01` structural pattern: bounded Nebius decision, deterministic allowed graph, cycle safety, budgets, owner-scoped persistence, and safe test mode.
- Existing User/Customer Demand, Competitor, Market, Evidence Auditor, QA Critic, and BP-90 baseline capabilities.
- Pinecone, Mem0, and Streamlit architecture.

## What must change before scheduler binding

| Component | Required change |
|---|---|
| Onboarding | Show only User, Competitor, and Market Research; default all three; accept idea-only onboarding. |
| Founder profile | Use `bp-founder-profile-v2`; persist initial research selection and explicit goal status. |
| BP-API-01 | Stop rejecting a missing goal; store `MISSING` or temporary `DEFAULTED_VALIDATE_DEMAND`. |
| BP-PLAN-01 | Add planning modes `DISCOVER`, `PROVE_AND_DESIGN`, and `COMPLETE_ACTION_BLUEPRINT`; initial call creates only Foundation, selected research, Evidence Audit, and Research Verdict tasks. Growth remains contextual advisory guidance, not an execution mode. |
| Research stream mapping | UI `user_research` maps to internal `customer_demand`; UI `competitor_research` maps to `competitor_intelligence`; UI `market_research` maps to `market_economics`. |
| Verdict engine | Calculate the 40/30/30 Research Viability Score deterministically from audited subscores and withhold a decision-capable score when evidence coverage is below 0.60. |
| State | Add append-only stage-verdict records and an explicit `STAGE_GATE` human checkpoint/route vocabulary. |
| Supervisor | Stop after the Research Verdict Gate when score is below 60, evidence is insufficient, research is incomplete, or a critical contradiction exists. |
| Human decision | Support targeted validation, run missing research, continue anyway, or pause/revise; bind the decision to profile/state/verdict version. |
| Later planning | Generate goal-specific Stage 2 tasks only after the checkpoint is resolved. |
| Dashboard | Show progressive research cards and keep the verdict `CALCULATING`, `LIMITED`, or `INSUFFICIENT` until its strict prerequisites are satisfied. |
| Blueprint versions | Create immutable Original/V0, Research/V1 and Action/V2 artifacts; never mutate the original; support Current and Compare views. |
| Contextual actions | Derive actions per selected section and hide the right panel when none are defensible. |
| Conversion signal | Do not show without measured founder-supplied funnel counts, time window and sample size. |
| Stage 3 | Advisory completion only: MVP, first customers, distribution, milestone roadmap and growth guidance; no weekly task program or launch execution. |
| Chatbot/RAG | Hold product integration until the staged end-to-end core is complete. |

## Revised Phase 6B build order

1. Migration 011: append-only `stage_verdicts`, route/checkpoint vocabulary, and owner-scoped verdict/dashboard RPC.
2. `BP-VERDICT-01`: deterministic score, sufficiency gate, critical-blocker override, and checkpoint proposal.
3. Revise `BP-PLAN-01` into staged planning modes and rerun its idea-only, selected-stream, all-stream, low-score, and missing-goal fixtures.
4. Build `BP-SCHED-01` to claim and dispatch only current-stage eligible tasks.
5. Bind Stage 1 specialists and expose progressive section results.
6. Bind human checkpoint resolution to Stage 2 plan creation.
7. Add goal-specific Stage 2 templates and Execution Readiness verdict.
8. Refactor `BP-00` to orchestrate the gates while retaining `BP-CORE-45` as rollback.

## Acceptance tests added by this decision

- Idea only, all three streams: Stage 1 runs and later planning waits for a goal/checkpoint.
- One selected stream: section completes; overall verdict is `LIMITED_VERDICT`.
- All streams with coverage below 0.60: verdict is `INSUFFICIENT_EVIDENCE` regardless of score.
- Score 59: no automatic Stage 2; human checkpoint created.
- Score 60: `CONDITIONAL_GO`; risks and required validation are preserved.
- Score 75: `STRONG_GO` when no critical blocker exists.
- Score 85 with critical contradiction: route is downgraded to human review.
- Continue-anyway decision: Stage 2 runs with a visible founder override and risk-first plan.
- Fundraising goal before readiness: show proof prerequisites, not a fundraising action plan.
- Pre-launch growth goal: show growth prerequisites/tips, not invented growth KPIs.
- Completed research remains readable while later approved tasks run.
