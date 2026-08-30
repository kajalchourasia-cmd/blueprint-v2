# Phase 6C, 6D and 6E2 — Memory and Rerun Evidence

Date verified: 30 August 2026

## Outcome

The memory and profile-change backend is installed in the local Blueprint Evidence Dev stack. Supabase is the canonical source for identity, evidence, profile versions, run state and projection status. Pinecone and Mem0 are bounded, rebuildable projections; provider availability never changes canonical truth.

## Phase 6C — accepted-evidence Pinecone projection

Implemented:

- `016_memory_projection_rpcs.sql` persists Stage 1 evidence only after an independent audit returns `PASS`.
- Canonical Supabase evidence UUIDs replace temporary search-card IDs before later verdict and Blueprint work.
- `BP-PINE-01 Accepted Evidence Memory` supports `INDEX_RUN`, `SEARCH` and `DELETE` with authenticated owner/project/run scope.
- The project namespace is derived from owner and project state; callers cannot supply an arbitrary namespace.
- Pinecone hits are revalidated against active Supabase projection records before being returned.
- Pinecone failure returns a memory-degraded result while preserving Supabase evidence.

Live acceptance result:

- Workflow: `BP-PINE-01 Accepted Evidence Memory`
- Result: `PASS`
- Test: integrated-embedding upsert → semantic search → exact synthetic match → scoped delete
- Namespace: `bp-6c-smoke`
- Cleanup: attempted and passed

The implementation follows Pinecone's integrated-embedding records API for text upsert and the scoped vector-delete API:

- https://docs.pinecone.io/reference/api/2026-04/data-plane/upsert_records
- https://docs.pinecone.io/reference/api/2026-04/data-plane/delete

## Phase 6D — confirmed Founder Journey memory

Implemented:

- `BP-MEM0-01 Founder Journey Memory` accepts only `GOAL`, `PREFERENCE`, `CONSTRAINT`, `CONFIRMED_DECISION`, `CORRECTION`, `LESSON`, and `EPISODE_SUMMARY`.
- Adds require explicit `confirmed: true` and an authenticated owner/project/run scope.
- Search is scoped by founder and project agent identifier; returned IDs/content hashes are revalidated in Supabase.
- Delete requires one explicit memory ID; the acceptance cleanup uses a synthetic user/agent/run scope only.
- Raw logs, hidden reasoning, unapproved guesses, canonical run state and full Blueprints are excluded.

Live acceptance result:

- Workflow: `BP-MEM0-01 Founder Journey Memory`
- Result: `PASS`
- Test: add with inference disabled → scoped semantic search → exact synthetic match → scoped cleanup
- Scope: synthetic `user_id`, `agent_id`, and `run_id`

Provider operations follow Mem0's documented add, search and delete contracts:

- https://docs.mem0.ai/api-reference/memory/add-memories
- https://docs.mem0.ai/api-reference/memory/search-memories
- https://docs.mem0.ai/api-reference/memory/delete-memory

## Phase 6E2 — profile impact and targeted/full rerun

Implemented:

- `017_profile_impact_and_rerun.sql` keeps founder profiles immutable and computes a deterministic dependency impact from changed fields.
- Unknown changed fields expand to a safe research closure and are surfaced as uncertain rather than guessed.
- Every preview creates a durable `RERUN` checkpoint with `APPROVE`, `EDIT`, and `CANCEL` choices.
- Approval rejects stale source state, is idempotent, creates a new run without overwriting the source, and preserves Original/Current comparison.
- `BP-RERUN-01 Profile Impact and Rerun` supports `SAVE_AND_PREVIEW`, `PREVIEW`, and `RESOLVE`.
- Only explicit `RESOLVE: APPROVE` creates and persists a dependency-closed task plan. Cancel and malformed commands preserve canonical state.

Live safe-plan result:

- Workflow: `BP-RERUN-01 Profile Impact and Rerun`
- Result: `PASS`
- Fixture: budget/pricing-style targeted impact
- Affected tasks: `offer_pricing`, `financial_readiness`, `action_blueprint`, `final_blueprint`
- Assertion: four typed tasks, dependency closure, no production write in test mode

## Remaining acceptance work

- Run `SAVE_AND_PREVIEW` and `RESOLVE` through a real Streamlit Supabase JWT.
- Test stale-preview rejection, idempotent replay, cancel, full rerun and unknown-field safe expansion in the Phase 6G runner.
- Test cross-user isolation and temporal-conflict behavior for both memory providers.
- Add Phase 7 controls for profile editing, impact preview, confirmation, version comparison and memory inspect/correct/delete.

