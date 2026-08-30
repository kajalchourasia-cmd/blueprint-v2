# Blueprint Evidence Dev — Supabase

Supabase Postgres is the authoritative state and evidence store. Pinecone contains only derived semantic memory for auditor-accepted evidence.

## Apply Phase 1

1. Open the Supabase project `Blueprint Evidence Dev` → **SQL Editor** → **New query**.
2. Paste and run [`migrations/001_foundation.sql`](migrations/001_foundation.sql) once.
3. Apply subsequent numbered migrations in order. Migrations 001–015 are live-applied in the development project.
4. Each migration runs inside a transaction. Any error rolls that migration back.
5. In a new query, run [`verify/001_foundation_verify_summary.sql`](verify/001_foundation_verify_summary.sql).
6. Every returned row must show `passed = true`. The longer [`verify/001_foundation_verify.sql`](verify/001_foundation_verify.sql) remains available for individual diagnostics.
7. After creating two confirmed Auth test users, run [`tests/001_gate_a_rls_state_test.sql`](tests/001_gate_a_rls_state_test.sql). Every row must show `passed = true`; the test intentionally rolls back its data.
8. Run [`tests/002_gate_b_start_run_test.sql`](tests/002_gate_b_start_run_test.sql). All six rows must show `passed = true`; it proves authenticated creation, replay idempotency, tenant isolation, anonymous denial, and invalid-input denial without persisting test data.
9. Dynamic orchestration continues through migrations 009–011. Migration 011 adds append-only stage verdicts, progressive Blueprint versions, stage progress, founder metric observations, and the deterministic Research Verdict RPC. Its verification is [`verify/011_stage_verdicts_progressive_blueprints_verify.sql`](verify/011_stage_verdicts_progressive_blueprints_verify.sql); all six checks must pass.
10. Migration 012 adds owner-scoped task execution context and an observable run snapshot. Migration 013 adds adapter-aware atomic claiming so an uninstalled worker cannot leave a task stuck in `RUNNING`. Their verification scripts return two passing rows each.
11. Migration 014 adds the owner-scoped Streamlit control-panel projection. Migration 015 adds stage-gate waiting state plus idempotent, stale-safe founder checkpoint resolution and resume.

The migration creates the complete V1 schema, ownership constraints, RLS policies, the private `blueprint-artifacts` bucket, allowed state transitions, append-only audit protection, and the `advance_run_state` RPC. It never contains project keys or passwords.

Do not edit tables manually in the dashboard after applying this migration. Any schema change becomes a new numbered migration.

## Artifact paths

Every private Storage object must use this first path segment:

```text
<authenticated-owner-uuid>/<project-uuid>/<run-uuid>/blueprint-v<version>.<format>
```

The Storage policies reject a path whose first segment is not the authenticated user's ID.
