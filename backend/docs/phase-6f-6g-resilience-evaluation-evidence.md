# Phase 6F–6G — Resilience, Observability, and Evaluation Evidence

Status: **COMPLETE for backend/component scope; live-safe verified on 2026-08-30.** The authenticated Streamlit journey and two-user UI isolation acceptance remain Phase 7, because they require the frontend JWT boundary rather than another backend agent.

## What the handout and samples changed

The handout requires task completion instead of single-call accuracy, explicit state, human approval for writes, deliberate recovery, and testing of unhappy paths. The six sample solution kits reinforced bounded retries, narrow agent roles, independent quality review, deterministic routing, preserved partial results, terminal paths, and audit convergence.

Blueprint adopts those patterns. It deliberately rejects three weaker sample shortcuts: substituting model training knowledge when retrieval fails, storing hidden chain-of-thought, and silently accepting parser defaults or terminal dead ends.

## Phase 6F implementation

`BP-RESILIENCE-01 Failure Route and Observability` is the shared caught-failure controller. Any Blueprint workflow may call it with the failed component, redacted error, attempt count, remaining budget, successful sibling count, and canonical run/task identifiers.

The controller deterministically classifies `AUTH`, `POLICY`, `RATE_LIMIT`, `TIMEOUT`, `EMPTY_RESULT`, `SCHEMA`, `GROUNDING`, `QUALITY`, `CONFLICT`, `BUDGET`, `PROVIDER`, `VALIDATION`, `INTERNAL`, and `UNKNOWN`. It then selects exactly one bounded route:

- `RETRY` with bounded backoff when a transient failure still has attempts and budget.
- `REPAIR` for a repairable schema, grounding, or quality observation.
- `RELOAD_AND_REPLAN` for stale state/version conflicts.
- `MEMORY_DEGRADED` when Pinecone or Mem0 fails; Supabase remains canonical.
- `PARTIAL_COMPLETE` when useful sibling results exist but a required branch cannot safely finish.
- `HUMAN_REVIEW` for unresolved ambiguity, exhausted empty results, or an internal condition that cannot be safely automated.
- `SAFE_FAIL` for authentication, exhausted budget, or no useful recoverable result.
- `POLICY_DENIED` for out-of-scope actions.

There is no unbounded loop. The maximum attempt is validated, the existing transition cap remains 20, partial sibling work is preserved, and missing evidence can never be replaced with model memory.

Migration `018_resilience_observability_evals.sql` adds:

- owner-scoped `record_resilience_decision(...)` for caught failures and tool metrics;
- owner-scoped `get_run_observability(...)` for run counters, task/error/tool summaries, pending checkpoints, and terminal visibility;
- durable `eval_suite_runs` and `eval_case_results` tables with RLS and anonymous access revoked;
- the additional error classes needed for empty-result, grounding, and policy failures.

The existing `BP-90 Error and Audit` remains the global uncaught-error boundary. The two layers are intentional: 6F handles expected/caught tool observations and BP-90 catches workflow-level crashes.

## Phase 6G evaluation

Run:

```powershell
& 'C:\Users\Hrishikesh\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' scripts\run-phase6-evals.js
```

The runner executes the actual exported n8n Code-node source, not duplicated pseudocode. It also validates every workflow's node IDs, connection targets, Code-node syntax, BP-90 binding, absence of embedded secrets, unsafe evidence fallbacks, owner-isolation schema, and observability persistence contract.

Latest result: **66/66 PASS (100%)**.

| Category | Passed | What is covered |
|---|---:|---|
| Scope | 6/6 | Valid founder ideas, direct external-action denial, unexpected write payloads, chat boundaries |
| Security | 4/4 | Unauthenticated start, secret/email redaction, policy denial, RLS/owner-scope/anonymous denial contract |
| Routing | 5/5 | Selected/default research, invalid stage, missing-research replan, dispatch |
| HITL | 7/7 | Gate decisions, pause precedence, checkpoint resume, contradictions, invalid approvals |
| Grounding | 4/4 | Evidence audit, bad citation repair, no training-knowledge fallback, pre-traction limits |
| Budget | 2/2 | Transition cap and tool/cost exhaustion |
| Completion | 2/2 | Full and visible partial terminal states |
| Memory | 6/6 | Confirmed-memory allowlist, raw-log rejection, scoped retrieval, graceful degradation |
| Rerun | 4/4 | Immutable save scope, explicit approval, stale/unsafe decision rejection, dependency closure |
| Failure | 3/3 | Retry exhaustion, schema repair, partial preservation |
| State | 23/23 | All workflow structures plus durable eval/observability schema |

The live n8n failure-injection matrix separately passed **15/15** cases: 429 retry/exhaustion, memory timeout degradation, empty-result retry/HITL, schema repair/partial, grounding repair, auth safe-fail, policy denial, state reload/replan, budget partial/fail, memory-provider degradation, and internal HITL.

The first regression run was 60/64. It correctly exposed one external-action regex escaping defect and three overwritten planner guards. The implementation was fixed so `SAFE_FAIL`, `RUN_MISSING_RESEARCH`, and founder pause decisions take precedence. The final run is 66/66; expected outcomes were not weakened.

## Live installation evidence

- Supabase migration 018 applied successfully; both eval tables and both RPCs were queried by name and returned as installed objects.
- `BP-RESILIENCE-01` imported, executed successfully, returned 15 passed / 0 failed / completion rate 1, and was published.
- The corrected `BP-PLAN-01`, `BP-CORE-45`, `BP-QA-01`, `BP-00`, and `BP-API-01` versions were published in dependency order.
- A live `POST /webhook/blueprint/start` denial probe returned HTTP `422`, `OUT_OF_SCOPE`, and the safe no-send/no-pay/no-delete message.

## What is intentionally left for Phase 7

Phase 6 does not claim the frontend is authenticated or end-to-end accepted. Phase 7 must pass one real Supabase JWT start, idempotent replay, owned run/dashboard retrieval, HITL resume, profile rerun confirmation, memory controls, and a second-user isolation denial. Those are UI/auth acceptance cases, not missing 6F routing or 6G evaluator logic.

Document visual rendering was attempted for the supplied DOCX files, but the local LibreOffice executable is unavailable. Every DOCX body paragraph, table cell, header, footer, footnote, endnote, and comment was still extracted and reviewed structurally; the source documents were not modified.
