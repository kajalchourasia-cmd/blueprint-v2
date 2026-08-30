# Blueprint Evidence Dev — Build Status and Next Steps

Last updated: 30 August 2026

## Latest architecture-contract update

The approved dynamic design is recorded in `docs/dynamic-blueprint-orchestration-spec.md`. Its Phase 6A–6G backend contracts are now bound to Supabase migrations, n8n workflows, a shared resilience controller, and a repeatable evaluation gate. Authenticated Streamlit binding remains.

V1 now has the owner-scoped Pinecone accepted-evidence projection and bounded Mem0 Founder Journey adapter. Founder-facing Ask Blueprint remains held until the staged core passes the eval gate. Founder document upload and LlamaIndex ingestion are explicitly V2.

The handout framework and boundaries are frozen in `docs/agent-framework-and-boundaries.md`. Chat/source/version contracts and provenance-bearing memory/rerun state are enforced by n8n plus owner-scoped Supabase RPCs.

## Plain-English status

The secure foundation, Phase 4–5 research engine, and the main Phase 6 orchestration layer are implemented and live-verified with safe fixtures. `BP-00` now calls `BP-CORE-45`, hands the result to independent `BP-QA-01`, selects a terminal/next route, and writes production results atomically through Supabase. `BP-CHAT-01` provides grounded Q&A, confirmation-gated research commands, and explicit out-of-scope denial. `BP-API-01` now dispatches BP-00 after an authenticated idempotent start. The remaining end-to-end acceptance dependency is the Streamlit Supabase JWT connection.

Approximate readiness:

- Infrastructure and provider setup: 100%
- Database, ownership, state, failure handling, and Start Run contract: 97%
- Core research/audit/synthesis agent workflow: 100% for the isolated core; import, static checks, safe-failure execution, and cited live synthesis passed
- Supervisor, final quality gate, and research copilot: 90%; manual live paths passed, authenticated production persistence test awaits Streamlit
- Streamlit founder experience: the earlier UI shell is approximately 60% reusable; Supabase/n8n integration is not implemented
- Evaluation and submission package: 25% implemented through tests and documentation
- Overall hackathon product: approximately 72–75%

## What is already working

1. Persistent self-hosted n8n with previous workflows preserved.
2. You.com, Nebius, Supabase, and Pinecone credentials connected privately in n8n.
3. Nebius Fast, Strong, and independent Audit models return validated structured JSON.
4. Pinecone can insert, semantically retrieve, and delete a test evidence record.
5. Supabase has owner-isolated tables, RLS, a bounded state machine, audit records, private artifact storage, and atomic transition functions.
6. BP-90 catches workflow failures and records safe failure, error, dead-letter, and transition evidence.
7. BP-API-01 validates input, denies out-of-scope external actions, verifies a user JWT, and creates/replays an idempotent project run.
8. Gate A passed 9/9 and Gate B passed 6/6.
9. Migration 006 adds durable blueprint-section status and an owner-scoped dashboard RPC; table/RLS/policies/function access passed 5/5 verification.
10. `BP-CORE-45 Evidence Blueprint` imported with 42 nodes, 12 provider/model calls, no missing connections, no Code-node syntax errors, no external write URLs, a bounded repair route, and a safe-partial route.
11. `BP-QA-01` independently scores seven quality dimensions, allows one bounded repair, revalidates evidence IDs, and fails closed.
12. `BP-00` completed a live 12-step agent trace through research, audit, synthesis, quality, and `MEMORY_INDEX` routing.
13. `BP-CHAT-01` passed grounded Q&A and a live denial for an unauthorized “ping/send” request.
14. Supabase migrations 007–008 are applied: owner-isolated run context/chat/commands plus atomic Supervisor/chat persistence; all access verification checks passed.
15. `BP-API-01` is wired to dispatch the Supervisor after a successful authenticated start.

## What is not built yet

1. Streamlit sign-in/backend integration, module selection, progress, chat, and one authenticated start/persistence acceptance run.
2. Streamlit controls for approval/correction/resume, profile edit, impact preview, rerun confirmation, version comparison and memory inspection.
3. Remaining direct-source verification hardening; search excerpts remain explicitly limited even though accepted-evidence Pinecone projection is complete.
4. Founder-facing observability/debug view using the completed Phase 6F RPC; the Phase 6G evaluator itself is complete at 66/66.
5. Demo recording, consolidated Google Doc, sanitized GitHub push, and final submission checks.

## The founder input

The founder ultimately types one product/business idea into Streamlit. The n8n workflow already contains one clearly marked safe test fixture for manual verification; it is test data and is not used by the Supervisor path.

Example:

> An AI customer-discovery copilot for solo SaaS founders that combines founder interviews, competitor evidence, and public customer pain signals to produce an evidence-backed ICP and willingness-to-pay experiment.

## Scope-denial behavior

Blueprint evaluates ideas. It does not execute arbitrary personal or business tasks.

- Allowed: “Evaluate an app that helps stores message customers.”
- Denied: “Message this customer for me.”
- Allowed: “Research a product that automates appointment booking.”
- Denied: “Book this appointment for me.”

Denial response:

> Blueprint can research and evaluate a founder idea, but it cannot contact people, send messages, publish, purchase, book, pay, or delete anything. I can instead turn that action into a founder-approved validation experiment or draft.

## Remaining compressed build sequence

| Next phase | Output | Builder estimate | User action |
|---|---|---:|---|
| 4. Vertical slice | Complete; execution `201` passed | 0 h | None |
| 5. Research and finance | Complete; execution `201` passed with 23 citations | 0 h | None |
| 6. Adaptive control | **6A–6G backend complete; 66/66 evaluator and 15/15 live failure matrix pass** | Complete | Review results only |
| 7. Streamlit | Reuse the previous interface; connect sign-in, module picker, progress, evidence, finance, approval and result | 2–3 h | Sign in and run one end-to-end test |
| 8. Hardening | Required security, failure, quality, and scope-denial fixtures | 2–3 h | No setup; inspect results |
| 9. Submission | Sanitized repository, diagrams, sample runs, demo script/video | 2–3 h | Record or approve the final demo |

These are focused estimates. Work proceeds in importable batches; optional integrations and visual polish are deferred until the complete happy path and one controlled failure are demonstrable.
