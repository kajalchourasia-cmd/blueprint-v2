# Blueprint Evidence Dev — Phase 0 Preflight

Do not record secret values here. Record only availability, non-secret configuration, redacted error class, and the date tested.

## Product lock

- Demo founder idea: **OPEN**
- Intended customer: **OPEN**
- Founder decision the blueprint must support: **OPEN**
- Demo success statement: **OPEN**

## Account access

The user confirmed dashboard login/access on 29 August 2026. This does not yet count as API authentication.

| Platform | Dashboard login | Required V1 resource |
|---|---|---|
| n8n | YES — local endpoint HTTP 200 and owner login works | Persistent Docker migration and four-provider smoke workflow passed |
| Supabase | YES | `Blueprint Evidence Dev` reachable; migrations 001–005 applied; foundation, Gate A, Gate B, and BP-90 integration verification passed |
| Pinecone | YES | `blueprint-evidence-dev` control plane and data-plane upsert/search/delete passed |
| You.com | YES | Development API credential search call passed |
| Nebius Token Factory | YES | Model-list and three strict structured-output role tests passed |
| GitHub | YES | Retain public repository `blueprint-v2`; remote currently has no branches/commits |
| Streamlit Community Cloud | YES — GitHub identity connected | `blueprint-v2` cannot yet be deployed because the remote is empty; initial app commit pending |
| Fireworks | YES | Intentionally skipped for V1 |

## n8n

- Deployment: **self-hosted Docker Desktop**
- Active container: **`blueprint-evidence-dev-n8n` using `n8nio/n8n:latest`**
- Rollback container: **`nostalgic_bardeen-pre-volume-20260829-185909` retained stopped**
- Version: **2.35.7**
- Plan/execution limits: **OPEN**
- Base URL: **`http://localhost:5679` for local development**
- Owner setup: **already completed; owner email identified from the local database but intentionally not recorded here**
- Existing project inventory: **one Personal project only; no Blueprint project**
- Legacy workflow isolation: **27 existing workflows remain in Personal; one is active (`17 - Behind the Label Hybrid V2 DEV`) and uses only a Chat Trigger, with no schedule or fixed webhook-path collision found**
- SMTP password recovery: **not configured**
- Persistent Docker volume: **`blueprint-evidence-dev-n8n-data`, mounted read/write at `/home/node/.n8n`**
- Pre-migration backup: **`C:\Users\Hrishikesh\Developer\genai\Week 3\Project\.local-backups\n8n\pre-volume-20260829-185909`**
- Backup verification: **`database.sqlite` and `config` present; SQLite integrity `ok`; 27 workflows, 3 credentials, 1 project, 1 user**
- Post-migration restart test: **PASS — HTTP 200, SQLite integrity `ok`, and matching record counts**
- Blueprint organization: **current edition gates additional shared projects behind an upgrade; use the existing Personal project with mandatory `BP-` workflow / `BP ` credential prefixes; tags are optional**
- First Blueprint workflow: **`BP-SETUP-00 Provider Smoke Tests` updated in place from sanitized JSON; ten nodes, four `BP ...` credential bindings, no duplicate, remains inactive**
- Workflow artifact: **`n8n/BP-SETUP-00-provider-smoke-tests.json`; no suspected secret values found**
- Workflow rollback export: **`.local-backups/n8n/workflow-exports/BP-SETUP-00-before-provider-nodes-20260829.json`**
- Provider execution: **PASS — all four branches completed successfully in one manual run; workflow remains inactive**
- Error workflow: **`BP-90 Error and Audit` imported successfully with ID `bp90ErrorAudit01`; seven nodes, one Error Trigger, active/published, no embedded secret**
- Error workflow dependency: **server-only RPC `record_workflow_failure` applied through migration `003_record_workflow_failure.sql`**
- Error writer credential: **PASS — `BP Supabase Error Writer` is privately bound to the BP-90 RPC node; the key value was never exported or read**
- Controlled failure harness: **`BP-TEST-90 Controlled Failure Harness` imported with ID `bp90FailureTest01`; temporary private Schedule Trigger used for verification, then unpublished and confirmed inactive; no public webhook**
- BP-90 controlled failure test: **PASS — BP-90 executions 191 and 193 succeeded; the latest synthetic run was independently verified as `SAFE_FAILED` with one error row, one dead-letter row, one audited transition, `PROVIDER`, and retryable/replay-eligible true**
- Controlled-test data inventory: **four clearly labelled `INTEGRATION_TEST` runs remain as audit evidence: two `SAFE_FAILED` proof runs and two `NEW` setup runs from failed test-path attempts; no founder research data is present**
- Timezone `Asia/Calcutta`: **PASS — set on BP-90 and the controlled failure harness**
- Error workflow support checked: **PASS — harness `settings.errorWorkflow` resolves to active workflow ID `bp90ErrorAudit01`**
- Phase 2 validator: **PASS — `BP-SETUP-01 Phase 2 Validation` completed with three Nebius structured-output assertions and Pinecone upsert/search/delete/cleanup; workflow remains inactive**
- Start API workflow: **`BP-API-01 Start Run` imported with ID `bpApi01StartRun`; 13 nodes, two `BP Supabase Public` bindings, BP-90 attached, no embedded secret, confirmed unpublished**
- Start API database contract: **PASS — migration 005 applied and Gate B returned 6/6 true for creation, idempotent replay, duplicate marking, invalid input, owner isolation, and anonymous denial**
- Local production webhook activation test: **NOT COUNTED — CLI publication did not register the route before the safety cleanup; both probes returned 404. Workflow was immediately unpublished and re-exported with `active=false`. Final success-path webhook testing will use a real Streamlit-issued JWT after the UI auth client exists.**

## Provider matrix

| Provider | Credential available? | Non-secret configuration | Smoke test | Redacted failure/action |
|---|---|---|---|---|
| You.com | YES — API key created and saved in `BP You Search` | Search returned URLs/titles | PASS — 29 Aug 2026, ~1.72 s | — |
| Fireworks | YES — user confirmed access | Optional post-MVP fallback | SKIPPED FOR V1 | No credential needed |
| Nebius Token Factory | YES — project/key saved in `BP Nebius Token Factory` | Fast: `Qwen/Qwen3-30B-A3B-Instruct-2507`; Strong: `Qwen/Qwen3-235B-A22B-Instruct-2507`; Audit: `openai/gpt-oss-120b` | PASS — all three strict JSON-schema assertions, 29 Aug 2026 | GPT-OSS audit requires a larger output budget because reasoning tokens consume the completion limit |
| Supabase | YES — publishable key saved in `BP Supabase Public` | URL `https://gudsbrmphrokpnzmrlqd.supabase.co`; ref `gudsbrmphrokpnzmrlqd` | PASS for Auth settings reachability — 29 Aug 2026, ~0.72 s | Do not expose secret/service-role key to Streamlit |
| Pinecone | YES — key saved in `BP Pinecone`; index created | Dedicated index Ready; dense/cosine; integrated `llama-text-embed-v2`; dimension 1024 | PASS — control-plane plus synthetic text upsert, semantic search, matched record, delete, 29 Aug 2026 | Test namespace `bp-phase2-smoke` was cleaned up |
| Tavily (optional) | OPEN | — | NOT RUN | May remain disabled |
| Firecrawl (optional) | OPEN | — | NOT RUN | May remain disabled |

## Supabase Phase 1 foundation

- Project reference: **`gudsbrmphrokpnzmrlqd`**
- Migration: **`supabase/migrations/001_foundation.sql` applied successfully on 29 August 2026**
- Verification suite: **PASS — all seven checks returned `passed = true`**
- Public tables: **16 / 16 present**
- RLS: **16 / 16 enabled; none disabled**
- RLS/Storage policies: **47 / 47 minimum present**
- Private Storage bucket: **`blueprint-artifacts` present and private**
- Allowed state transitions: **52 / 52 present**
- Atomic state RPC: **`advance_run_state` present**
- Critical indexes: **17 / 17 present**
- Auth users: **2 confirmed non-production test users available; email addresses intentionally not recorded**
- Gate A rollback-only database test: **PASS — 9/9 checks**
- Ownership isolation: **PASS — own read allowed; cross-user read/write/RPC denied**
- State protection: **PASS — legal transition audited; stale version, illegal transition, and direct state-field update denied**
- Idempotency constraint: **PASS — duplicate `(owner_id, idempotency_key)` rejected**
- Test cleanup: **PASS — 0 test projects, 0 test runs, and 0 test transitions persisted**
- Hardening migration: **`002_harden_state_guard.sql` applied after the first test detected a transaction-local bypass flag lasting too long**
- Error RPC migration: **`003_record_workflow_failure.sql` applied; executable only by `service_role`**
- Controlled-test helper: **`004_prepare_bp90_failure_test.sql` applied; executable only by `service_role`; creates clearly labelled synthetic rows without embedding an Auth user UUID in n8n**
- Authenticated start RPC: **`005_start_blueprint_run.sql` applied; executable only by `authenticated`; atomically creates project plus NEW run and replays by owner-scoped idempotency key**
- Gate B rollback-only test: **PASS — 6/6 checks; no Gate B rows persisted**
- Secrets used in SQL: **none**

## Dedicated Pinecone index

- Plan: **Builder**
- Index name: `blueprint-evidence-dev`
- Host: **`blueprint-evidence-dev-kdijdfn.svc.aped-4627-b74a.pinecone.io`**
- Vector mode: **dense integrated embedding**
- Integrated model: `llama-text-embed-v2`
- Dimension: **1024 (selected integrated-model default; do not change to 2048)**
- Source text field: `chunk_text`
- Similarity metric: **cosine**
- Cloud/region: **AWS `us-east-1` unless the console requires another supported placement**
- Existing workload/data: **none; dedicated index**
- Planned namespace: `bp-<project_uuid>`
- Text upsert/search/delete smoke test: **PASS — synthetic record matched semantically and was deleted**
- Supabase-only fallback accepted if incompatible: **YES**

## Phase 0 exit record

- Required-provider API reachability passed: **YES — You.com, Nebius, Supabase, and Pinecone**
- Full technical Phase 0 gate passed: **YES — all required provider control/data-plane checks passed; product lock and repository secret scan remain product/release tasks**
- Phase 1 database foundation: **APPLIED AND VERIFIED**
- Blockers: **demo idea/product baseline, Streamlit-issued JWT success-path test, and repository secret scan remain**
- Gate owner/date: **OPEN / 29 August 2026**
