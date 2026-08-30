# Hackathon Build Checklist — Blueprint Evidence Dev Status

Audited against the complete pasted checklist and all 122 ordered textual paragraph/table/header records extracted from the full Week 3 handout on 30 August 2026. LibreOffice was unavailable, so this was a structural/textual audit rather than a rendered visual-layout review.

Legend: **DONE** = implemented and evidenced; **PARTIAL** = designed or implemented but an acceptance test/UI binding remains; **PENDING** = not built yet; **N/A BY SCOPE** = deliberately prohibited rather than omitted.

## 1. Define the project — DONE

- **DONE:** Own comparable multi-step use case: an evidence-first founder idea validation Blueprint.
- **DONE:** Concrete user and workflow: an early-stage founder with an existing idea, moving from framing through customer, competitor, market, finance, validation, final quality, and next action.
- **DONE:** Assignment one-liner covers user, multi-step job, Streamlit surface, manual research cost, autonomous read-only research/calculation, You/Nebius/Supabase/Pinecone tools, HITL, and bounded completion target.
- **DONE:** Explicitly out of scope: messaging/contacting, publishing, payment, booking, purchasing, deletion, legal/financial certainty, fabricated interviews, and unsupported market/WTP claims.
- **DONE:** n8n chosen.
- **DONE:** Hybrid multi-agent architecture chosen and justified: deterministic orchestration and calculations plus narrow LLM specialists and independent critics.
- **DONE:** The handout's core distinction is preserved: Blueprint is not a one-shot LLM call and not merely a RAG lookup. RAG and Mem0 are bounded tools inside an agentic control/state/error/HITL system.
- **DONE:** The exact handout framework is filled in `agent-framework-and-boundaries.md`, including one-liner, end-to-end completion, memory location/duration, read/write boundary, HITL, failure behavior and measurable success.

## 2. Specify the end-to-end workflow — PARTIAL

- **DONE:** Full control-flow diagram exists.
- **DONE:** Start triggers: authenticated start webhook, chat webhook, and manual safe fixtures.
- **DONE:** Terminal statuses exist: completed, partial, waiting/human review, needs input, safe failure, and cancelled.
- **DONE:** Conditional branches, parallelizable research streams, stopping rules, maximum transitions/search/tool calls/revisions/retries, and visible outcomes are defined.
- **DONE — LIVE SAFE:** The gate-aware planner prevents Stage 2/3 creation before their founder decisions; missing research reroutes to Discover, pause stops progression, and pre-traction growth is `NOT_APPLICABLE` rather than fabricated.
- **DONE — LIVE SAFE:** The scheduler preserved two parallel claimed tasks as two separate specialist observations and returned both to Supervisor re-evaluation.
- **DONE — LIVE SAFE:** The bounded Supervisor re-evaluation worker selects dispatch, wait, founder input, contradiction review, durable checkpoint resume, partial completion, or terminal completion and stops after 20 transitions.
- **DONE:** BP-90 creates an audit outcome for unhandled workflow errors.
- **PARTIAL:** Authenticated start → background Supervisor dispatch is wired but awaits one Streamlit/JWT acceptance run.
- **PARTIAL — BACKEND LIVE SAFE:** Stage-gate creation now moves the run to `WAITING_APPROVAL`; `BP-HITL-01` records only a currently allowed decision, rejects stale/different replay, advances the run and returns the exact replanning mode. Streamlit binding and one authenticated acceptance run remain.

## 3. Design routing deliberately — PARTIAL

- **DONE:** Deterministic rules handle scope, validation, cancellation, budget caps, module allowlists, and chat commands.
- **DONE:** Typed Supervisor route schema, allowlisted routes, route evidence/confidence, missing-information route, and downstream structured context exist.
- **DONE:** Server-side adapter-aware claiming prevents the scheduler from claiming a READY task whose worker is not installed.
- **DONE:** Chat has `AMBIGUOUS` and clarification-safe behavior.
- **PARTIAL:** User correction is represented by `CORRECTION` and resume state but is not yet bound to a UI/API action.
- **DONE:** The repeatable Phase 6G suite covers default/selected research, invalid stages, missing-research replan, pause precedence, dispatch, contradictions, clarification, and checkpoint routes; all routing cases pass.
- **NOTE:** LLM intent classification is intentionally not used where deterministic routing is sufficient; ambiguous natural-language classification can be added only where an eval shows value.

## 4. Define agents and handoff contracts — DONE FOR STAGE 1 / PARTIAL OVERALL

- **DONE:** Narrow roles exist for Supervisor, Idea Frame, Research Planner, Provider Gateway, Customer Demand, Competitor Intelligence, Market Economics, Financial Scenario, Experiment Designer, Evidence Auditor, Blueprint Synthesis, Blueprint Critic, Research Copilot, and memory indexing route.
- **DONE:** JSON contracts/schemas exist for Supervisor, quality, chat, core specialist responses, and final Blueprint.
- **DONE:** Phase 6A contracts now exist for immutable founder profiles, dynamic tasks/dependencies/observations, detailed module sections, dynamic signals, next actions and targeted/full rerun impact previews.
- **DONE — LIVE SAFE:** `BP-STAGE1-01` enforces four allowlisted roles and returns typed `VALID`, `NEEDS_REPAIR`, `TOOL_FAILED`, or `POLICY_DENIED` observations; `BP-SCHED-01` performs the task handoff without collapsing parallel items.
- **DONE — LIVE SAFE:** `BP-STAGE1-ROUTER-01` now hands off all seven Stage 1 module types to bounded research, independent audit, deterministic verdict, or immutable Blueprint synthesis; unknown adapters fail with `POLICY_DENIED`.
- **DONE:** Chat contracts distinguish grounded, partially grounded and insufficient-evidence outcomes, source tracing and Blueprint-version comparison; Mem0 writes have a provenance-bearing allowlist schema.
- **DONE:** Structured handoffs carry goals, founder inputs, evidence, limitations, questions, counters, route decisions, agent trace, and approval/human status.
- **DONE:** Independent Evidence Auditor and Blueprint Critic validate other agents instead of blindly trusting their prose.
- **DONE:** Unknown values remain unknown; facts, deterministic scenarios, recommendations, and assumptions are separated.
- **PARTIAL:** A single final agent/tool inventory documenting every role's exact token/tool/time limits and never-actions still needs to be assembled for submission.

## 5. Create the shared state model — PARTIAL

- **DONE:** Run/user/project IDs, original request, intent/constraints, route/node, plans, evidence, outputs, missing information, errors, counters, approvals, safety flags, quality, terminal status, and final output have database locations.
- **DONE:** `run_contexts`, transitions, Blueprint sections, errors, approvals, chat, and final results persist across sessions.
- **DONE:** Owner-scoped RLS and composite owner foreign keys isolate users/projects.
- **DONE:** Authenticated context retrieval and atomic Supervisor/chat writes are implemented; anonymous access is blocked.
- **DONE:** A claimed worker receives the exact immutable profile version, dependency outputs, latest stage verdict and pending checkpoints through an owner-scoped RPC; a separate snapshot exposes task counts, routes, checkpoints and stage progress without chain-of-thought.
- **DONE:** `get_founder_control_panel` projects missing input, contradictions, tool failures, partial results, pending stage gates, allowed founder decisions, severity and next route in one Streamlit-ready owner-scoped payload.
- **PARTIAL:** Authenticated production write path awaits the Streamlit/JWT run.
- **DONE — BACKEND:** Auditor-passed Stage 1 evidence is persisted canonically before Pinecone projection; retrieval is owner/project scoped and revalidated against active Supabase projection records. Scoped upsert/search/delete passed live.
- **DONE — BACKEND:** The Mem0 Founder Journey adapter accepts only confirmed goals, preferences, constraints, decisions, corrections, lessons and episode summaries. Scoped add/search/delete passed live and Supabase remains canonical.
- **BACKEND COMPLETE:** Confirmed-memory boundaries, raw-log rejection, scoped search, graceful degradation, canonical Supabase revalidation, and RLS/owner-isolation contracts pass Phase 6G. User-facing inspect/correct/delete controls and a real second-user UI denial remain Phase 7 acceptance.
- **DONE — BACKEND:** Immutable profile edits, deterministic dependency impact, explicit confirmation, stale-preview rejection, targeted/full rerun creation and dependency-closed plan persistence are implemented. Authenticated Streamlit acceptance remains.

## 6. Implement tools safely — PARTIAL

- **DONE:** Tools have narrow purposes, bounded payloads, argument checks, timeouts, capped retries, structured errors, and provenance.
- **DONE:** Provider credentials remain in n8n credentials and are absent from prompts/exported JSON/repository files.
- **DONE:** Research/model tools are read-only; database writes use authenticated owner-scoped, idempotent/atomic RPCs.
- **DONE:** Start runs and agent commands have duplicate-prevention keys.
- **DONE:** Atomic claiming uses `FOR UPDATE SKIP LOCKED`, a limit of 1–5, and an installed-adapter module allowlist; unsupported READY tasks remain unclaimed rather than becoming stuck.
- **DONE:** BP-90 classifies retryable versus non-retryable failures and redacts secrets.
- **PARTIAL:** Retry delay is bounded; a formal exponential-backoff helper and repeatable 429 test remain.
- **PARTIAL:** Retrieved content is treated as evidence rather than instruction in prompts; a dedicated prompt-injection test fixture remains.
- **PENDING:** Final least-privilege/read-write permissions table for submission.

## 7. Add grounding and validation — PARTIAL

- **DONE:** Retrieved evidence plus Supabase accepted evidence are the source of truth.
- **DONE:** Claims retain URLs, query, provider, timestamp, excerpt, limitations, and auditor verdict.
- **DONE:** Volatile/high-stakes unknowns do not fall back to model memory.
- **DONE:** Code/schema validators check required fields, arrays, values, ranges, evidence IDs, and parser failures.
- **DONE:** Deterministic finance is separated from LLM interpretation.
- **DONE:** Parser/critic failure cannot become PASS; quality fails closed.
- **PARTIAL:** Search-result excerpts are directional. Direct source-page verification is still required before strong market-size, price, or WTP claims.
- **PENDING:** Automated cross-agent contradiction suite beyond current auditor/critic checks.

## 8. Build bounded feedback loops — DONE

- **DONE:** Independent critic uses a seven-part rubric.
- **DONE:** Specific repair instructions plus original Blueprint/evidence go to a separate reviser.
- **DONE:** Exactly one final Blueprint revision is allowed in BP-QA-01.
- **DONE:** Revised output is schema/evidence-allowlist checked and independently re-criticized.
- **DONE:** Failed revalidation returns quality warning/partial or human review.
- **DONE:** Before/after scores and whether quality improved are recorded.
- **LIVE EVIDENCE:** An attempted unsupported revision was stripped and ended `QUALITY_FAILED / PARTIAL_COMPLETE`, not a false PASS.

## 9. Add human-in-the-loop — PARTIAL

- **N/A BY SCOPE:** Blueprint performs no consequential external send/post/pay/delete/publish action in V1; such requests are denied.
- **DONE:** Human-review, founder-input, approval records, expiry field, evidence/risk context, and safe non-completion language exist in the state/database design.
- **DONE:** Repeated failure, conflicting/authority-sensitive quality, missing information, and uncertainty can route to human review.
- **PARTIAL/DONE:** Streamlit now renders pending founder checkpoints and submits only each checkpoint's allowlisted decision through the state-version-checked owner RPC. Full edit/request-more-information/cancel/rerun control coverage remains.
- **PENDING:** Real-JWT UI test proving a founder decision persists, resumes orchestration, and rejects a stale replay.

## 10. Handle failures — DONE FOR BACKEND/COMPONENT SCOPE

- **DONE or implemented:** missing/invalid input, no useful research, provider error, authentication failure, malformed JSON, missing fields, quality contradiction, partial result, duplicate start, retry exhaustion, unsafe request, and workflow-level failure.
- **LIVE TESTED:** safe out-of-scope denial; malformed/unsafe quality revision; quality failure; core safe partial; provider/core live success; duplicate/idempotent database primitives.
- **DONE:** A repeatable evaluator plus the live 15-case n8n injection matrix cover ambiguous/invalid routes, forced timeout, forced 429, empty results, provider outage, schema and grounding repair, retry exhaustion, stale-state reload/replan, memory degradation, human review, policy denial, budget exhaustion, and preserved partial siblings. Restart/resume is covered by durable checkpoint/state contracts; real browser-session resume remains Phase 7 acceptance.
- **DONE:** Each failure maps to retry, safe fallback, clarification, partial continuation, stop, or escalation; no silent continuation.

## 11. Add observability — PARTIAL

- **DONE:** Agent trace, provider/model, route, correlation ID, errors, transitions, retry/revision counters, evidence provenance, and audit tables exist.
- **DONE:** `get_orchestration_run_snapshot` provides an owner-scoped debug projection of tasks, counts, checkpoints, stage progress and the latest verdict.
- **DONE:** BP-90 redacts secrets and stores sanitized failure context.
- **DONE:** No hidden chain-of-thought is exposed; only decisions/observations are recorded.
- **PARTIAL:** Tool/model latency and cost fields exist but are not populated consistently by every Phase 4–6 node.
- **PARTIAL:** Streamlit now shows owner-scoped run status, completion/activity/attention counts, pending checkpoints, and safe projection failures. One-click sanitized replay remains pending.

## 12. Evaluate the system — DONE FOR BACKEND/COMPONENT SCOPE

- **DONE:** Individual live/manual tests cover provider access, Pinecone insert/search/delete, core happy path, quality repair failure, chatbot grounding, and unsafe request denial.
- **DONE:** Seven repeatable staged-planner regression cases cover idea-only Discover, missing Gate 1, missing-research replan, founder pause, goal-specific Stage 2, missing Gate 2, and pre-traction growth.
- **DONE:** Safe n8n executions cover the parameterized Stage 1 specialist and a two-item scheduler/subworkflow/observation fan-out.
- **DONE:** Safe n8n executions cover the independent evidence audit (`PASS`, `0.76` coverage), immutable Research Blueprint synthesis, typed worker router, and five Supervisor branch outcomes.
- **DONE:** Cleanup-safe live provider executions cover Phase 6C Pinecone upsert/search/delete and Phase 6D Mem0 add/scoped-search/scoped-delete; the Phase 6E2 targeted rerun graph fixture also passes.
- **DONE:** `scripts/run-phase6-evals.js` executes the actual exported n8n Code nodes and structural/security contracts. Latest result: 66/66 PASS. The separately executed live n8n failure matrix passed 15/15.
- **DONE:** The machine-readable report aggregates completion, routing, grounding, recovery, quality/HITL, security, memory, rerun, budget, and state-contract pass rates.
- **PHASE 7/8 ACCEPTANCE:** Measure real authenticated-journey latency, provider cost, user acceptance, and unnecessary-step rate after the Streamlit path exists; backend-only fixtures cannot honestly produce those product metrics.

## 13. Prepare the interface and output — PENDING/PARTIAL

- **DONE:** Existing Streamlit V1 UI/case study are preserved; V2 information architecture and Blueprint/dashboard contracts are defined.
- **DONE:** Structured decision-ready Blueprint includes source/uncertainty, partial completion, dashboard signals, finance scenarios, and next route.
- **PARTIAL:** Research Copilot backend works manually and has a Streamlit-compatible webhook; owner-scoped Pinecone projection plus Supabase revalidation are complete, while founder-facing chat integration remains deliberately held until the staged core and eval gate pass.
- **DONE — DESIGN:** Every roadmap item has a detailed section contract, evidence/comparison tables, next actions, version history and in-section rerun proposal.
- **PARTIAL/DONE:** Real sign-up/sign-in/refresh/logout, returning-project recovery, authenticated start, three-stream selection, dynamic run status, safe partial projection handling, and checkpoint decisions are bound. Detailed dynamic sections, corrections, sources, finance, full version views, rerun and export/download remain; RAG chat stays deliberately held.
- **V2 PLANNED:** Founder document upload to Supabase Storage, LlamaIndex ingestion/deduplication, prompt-injection checks and page-level RAG citations.

## 14. Prepare submission assets — PENDING/PARTIAL

- **DONE/PARTIAL:** Architecture diagram, state design, routing/error/HITL descriptions, setup notes, build prompts, iteration notes, and source documentation exist locally.
- **PENDING:** Consolidated Google Doc, final agent/tool and permission tables, complete evaluation report, known-limitations/future-work section, sample authenticated output, ≤5-minute video, final README/env verification, and sanitized GitHub push.
- **PENDING:** Final credential/private-data scan before submission.
- **DATE CHECKED:** Handout states 30 August 2026 for Builder of the Week and 16 September 2026 for final certification.
- **HANDOUT COVERAGE:** Own use case is allowed; n8n is an allowed build track; Nebius must appear in at least one model call; project documentation, a ≤5-minute live video and GitHub link are mandatory; error handling and HITL are explicitly emphasized; copying supplied solution documents can score zero.

## Minimum / strong / advanced assessment

| Level | Current status |
|---|---|
| Minimum acceptable | **Almost met:** real multi-step workflow, real tools, branches, explicit state, safe errors, human checkpoint, and end-to-end Blueprint exist; authenticated UI and submission assets remain. |
| Strong submission | **Backend complete:** hybrid routing, typed outputs, provenance, bounded quality repair, fail-closed safety, audit trail, live failure demonstration, and repeatable evaluation exist; authenticated UI acceptance remains. |
| Advanced optional | **Substantially implemented:** specialist agents, owner isolation, persistent state, production auth schema, cost-aware model roles, Pinecone projection, resumable HITL, Mem0 boundaries, and automated regression evals exist; the founder-facing controls/dashboard remain Phase 7. |
