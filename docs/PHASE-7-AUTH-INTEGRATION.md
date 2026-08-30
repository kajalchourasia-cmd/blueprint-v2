# Phase 7 — authentication and end-to-end data flow

## Implemented

- Real Supabase email/password sign-up and sign-in.
- Access-token expiry checks and refresh-token rotation.
- Supabase logout plus clearing of local Blueprint/session state.
- Owner JWT and publishable key on all n8n and Supabase calls.
- RLS-backed loading of the signed-in founder's active projects and latest runs.
- Eight-question onboarding with exactly three first-research choices: Customer, Competitor, and Market Research; all are selected by default.
- Stable idempotency key across a safe retry, preventing duplicate starts.
- Authenticated n8n start payload containing founder context and only selected research modules.
- Dashboard integration panel for live run state, partial projection errors, refresh, and state-version-checked founder checkpoint decisions.
- Protected product pages; the case study remains public.
- Seven frontend contract tests and 68 backend/orchestration regression cases pass.
- Published local n8n start workflow verified with live `422 OUT_OF_SCOPE`, `400 INVALID_REQUEST`, and `401 UNAUTHENTICATED` responses.

## Deliberate security boundary

Streamlit contains only the Supabase project URL, Supabase publishable key, and public n8n webhook URL. You.com, Nebius, Pinecone, Mem0, Supabase secret/service-role, and database credentials remain in n8n. Supabase is canonical; Streamlit session state is only a UI cache.

Blueprint never sends, contacts, publishes, pays, purchases, books, or deletes externally. These requests are denied. Internal project/run persistence is owner-scoped and allowlisted. Founder checkpoints govern expensive reruns, conflicting evidence, and stage progression.

## Acceptance still required

1. Add the real public settings privately to `.streamlit/secrets.toml` or Streamlit Cloud Secrets.
2. Sign in with the existing Supabase demo user.
3. Start one safe demo idea and confirm the response creates exactly one owned project/run.
4. Refresh the dashboard and verify selected research modules, status, observability, and any checkpoint.
5. Sign out, sign back in, and reopen the saved Blueprint.
6. Repeat with a second user and prove that neither user can see the other's project/run.
7. For Streamlit Cloud, replace the local webhook with a public HTTPS n8n endpoint.

## Phase 7 integration status — updated after canonical-path convergence

- **7A:** authenticated start now creates the owner-scoped project/run, immutable profile v1, and Original Blueprint before dispatch.
- **7B:** the public start webhook now invokes the dynamic Planner → Scheduler → typed Stage 1 workers → independent audit → deterministic verdict → immutable synthesis loop under the existing `bp00Supervisor` ID.
- **7C:** Streamlit now reads and renders live status, detailed research sections, sources, risks, unknowns, actionables, verdicts, and founder checkpoints. The older dashboard remains below it so visual redesign can happen without changing backend contracts.
- **7D:** workflow/component evaluation passes 77/77 and Python auth/backend tests pass 9/9.
- **7E:** Ask this Research retrieves only the current owner's dynamic outputs, Blueprint, verdict, actionables, and accepted evidence. A rerun is proposal → impact preview → explicit approve/cancel; natural-language chat cannot silently execute it.

Still required for final acceptance: one real signed-in golden journey, a second-user isolation journey, and a cloud-reachable HTTPS n8n URL before Streamlit Community Cloud deployment.
