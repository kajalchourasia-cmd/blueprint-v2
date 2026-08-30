# Phase 6B — Dynamic Planner Evidence

> Later-flow notice: this live test remains valid evidence for the bounded planner mechanism, but its all-modules-at-once product behavior is superseded by [`frozen-founder-user-flow.md`](frozen-founder-user-flow.md). The workflow must be revised into staged planning modes before scheduler binding.

Date: 30 August 2026  
Status: planner slice passed; scheduler execution/handoffs remain

## Database control plane

Migration `010_dynamic_scheduler_rpcs.sql` was applied to `Blueprint Evidence Dev` and its verification returned three passing checks:

- 3/3 scheduler functions exist.
- 3/3 are executable by `authenticated`.
- 3/3 are denied to `anon`.

The functions atomically persist an acyclic task plan, claim ready tasks with row locking, record append-only observations, apply retry/HITL/partial/safe-fail status rules, and unlock satisfied dependants.

## n8n planner

`BP-PLAN-01 Dynamic Task Planner` was generated, structurally checked, imported inactive, and live-tested.

Structural result:

- 14 nodes.
- Unique node names.
- Zero JavaScript syntax errors.
- Zero missing connection targets.
- BP-90 configured as the error workflow.
- Only two outbound HTTP nodes: Nebius planning and the owner-scoped Supabase plan RPC.

Live fixture result:

- Execution: success in 6.419 seconds.
- Output schema: `bp-plan-result-v1`.
- Status: `PLANNED`.
- Route: `TASK_SCHEDULER`.
- Planner mode: `NEBIUS_VALIDATED`.
- Human review: false.
- Production persistence: false with reason `TEST_MODE`.
- The generated graph included foundation, parallel research tasks, dependent offer/risk/finance/validation/launch/growth work, evidence audit, and final Blueprint synthesis.

## Safety properties

- The model cannot invent task types, tools, or dependencies.
- Foundation, evidence audit, and final Blueprint are mandatory.
- Deterministic validation forces unsafe dependency choices to `WAIT`.
- Production persistence requires valid owner/project/run UUIDs, a saved profile version, and a Bearer token.
- Test mode does not write founder state.

## Remaining Phase 6B work

1. Build `BP-SCHED-01` around `claim_ready_orchestration_tasks` and `observe_orchestration_task`.
2. Map task module keys to bounded specialist subworkflows.
3. Refactor `BP-00` to call the planner/scheduler while keeping `BP-CORE-45` as rollback.
4. Run authenticated production-plan, parallel-ready, repair, missing-input, and resume tests.
