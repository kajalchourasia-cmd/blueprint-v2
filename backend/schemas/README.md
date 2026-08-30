# Blueprint Evidence Dev — Schemas

Versioned JSON Schemas for state, route decisions, agent envelopes, evidence, and Blueprint output live here. Model output is untrusted until it passes schema and policy validation.

Phase 6A dynamic contracts:

- `founder-profile.schema.json` — immutable onboarding/profile versions, goals, constraints and `ALL`/selected module scope;
- `blueprint-task.schema.json` — typed task/dependency/budget/observation contract for the Supervisor;
- `module-section.schema.json` — full click-through section output and in-section rerun eligibility;
- `next-action.schema.json` — ranked founder/system action contract;
- `dashboard-signal.schema.json` — provenance-bearing dynamic signal contract;
- `rerun-impact.schema.json` — targeted/full rerun impact and confirmation preview.
- `founder-memory.schema.json` — provenance-bearing, version-aware memories allowed into Mem0.

`chat-request.schema.json` and `chat-response.schema.json` also carry Blueprint-version comparison, source-trace, grounding and insufficient-evidence behavior so Ask Blueprint cannot answer unsupported questions as fact.
