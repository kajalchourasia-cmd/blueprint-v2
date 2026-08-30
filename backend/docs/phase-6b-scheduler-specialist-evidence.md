# Phase 6B — Gate-Aware Planner, Scheduler and Stage 1 Worker Evidence

Date: 30 August 2026  
Status: implemented and live-safe verified; production workflows remain inactive

## Implemented boundary

- `BP-PLAN-01` now has three planning modes: `DISCOVER`, `PROVE_AND_DESIGN`, and `COMPLETE_ACTION_BLUEPRINT`.
- Discover creates exactly Foundation, the selected research streams, Evidence Audit, Research Verdict, and Research Blueprint work.
- Stage 2 requires Gate 1. The advisory Action Blueprint requires Gate 2.
- Missing research returns to Discover; pause creates no later work; pre-traction growth does not invent growth metrics.
- Nebius can prioritize only candidates supplied by deterministic policy. Locked tasks, dependencies, tools, stages and gates cannot be modified by the model.

## Database changes

Migration 012 adds:

- `get_orchestration_task_context`: exact immutable profile version, claimed task, dependency outputs, latest verdict and pending checkpoints;
- `get_orchestration_run_snapshot`: owner-scoped task counts/routes, checkpoints, stage progress and latest verdict.

Verification: 2/2 functions and 2/2 grants passed.

Migration 013 adds `claim_dispatchable_orchestration_tasks`. It uses owner scoping, `FOR UPDATE SKIP LOCKED`, bounded claim size and an installed-adapter module allowlist.

Verification: 1/1 function and 1/1 grant passed.

## Planner evidence

The live Discover fixture succeeded and returned seven tasks:

1. `s1_foundation`
2. `s1_customer_demand`
3. `s1_competitor_intelligence`
4. `s1_market_economics`
5. `s1_evidence_audit`
6. `s1_research_verdict`
7. `s1_research_blueprint`

The repeatable script `scripts/verify-staged-planner.js` passed 7/7 cases:

- idea-only Discover;
- Stage 2 without Gate 1;
- run-missing-research replan;
- founder pause;
- paying-customer goal branch with finance;
- Action Blueprint without Gate 2;
- pre-traction growth advisory only.

The regression suite found and fixed a route-precedence defect where the explicit `RUN_MISSING_RESEARCH` decision was being overwritten by the generic missing-gate fallback.

## Specialist evidence

`BP-STAGE1-01` supports only Foundation, Customer Demand, Competitor Intelligence and Market Economics. Production mode uses bounded You.com retrieval when required and a grounded Nebius role. It denies other module keys, safely observes thin/provider-failed retrieval, and rejects unsupported or invalid citations before output can become `VALID`.

Safe execution: success in 539 ms, `customer_demand`, `VALID`, `OBSERVE_AND_UNLOCK`, with no provider calls and no persistence.

## Scheduler evidence

`BP-SCHED-01` claims only installed adapters, loads version-exact context, invokes the bounded specialist per item, converts each result to the observation RPC contract, and returns control to `SUPERVISOR_REEVALUATE`.

The first fan-out test exposed two n8n item-collapsing defects. Context binding and observation handling were converted to per-item execution. The final live-safe run succeeded in 1.039 seconds with two inputs and two distinct outputs:

- `s1_foundation` → `VALID` → `SUPERVISOR_REEVALUATE`;
- `s1_customer_demand` → `VALID` → `SUPERVISOR_REEVALUATE`.

No web request and no production database write occurred in the safe test.

## Closed-loop meaning

The model does not retrain itself online. Blueprint learns at the orchestration layer:

1. a worker returns a typed observation;
2. Supabase records it durably;
3. `VALID` unlocks satisfied dependencies;
4. `NEEDS_REPAIR` requeues within the repair cap;
5. retryable `TOOL_FAILED` requeues within the attempt cap;
6. contradictions or exhausted repair route to human review;
7. the Supervisor reads the new snapshot and chooses the next eligible branch or replans.

This is observable, bounded, resumable adaptation—not an unprovable claim of model self-training.

## Phase 6B completion addendum — 30 August 2026

The four previously missing component paths are now implemented and live-safe verified:

1. `BP-AUDIT-01` independently audits Stage 1 outputs and emits the verdict input contract;
2. `BP-STAGE1-ROUTER-01` binds audited output to `BP-VERDICT-01` and refuses unknown worker routes;
3. `BP-SYNTH-01` creates the grounded immutable Research Blueprint V1 contract;
4. `BP-SUPERVISOR-REEVAL-01` selects dispatch, wait, founder input, contradiction review, checkpoint resume, partial completion or terminal completion from durable state, with a bounded-transition circuit breaker.

`BP-SCHED-01` now dispatches all seven Stage 1 module types through the typed router. The remaining end-to-end dependency is Phase 6E1: persist a founder checkpoint decision and resume idempotently from that exact state version. This is not missing 6B worker logic; it is the durable human-action boundary required before Stage 2. The authenticated production acceptance run follows that resume path.
