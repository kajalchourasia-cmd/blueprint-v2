# Blueprint Evidence Dev

> Current authority: [Authoritative Build Plan](docs/current-build-plan.md). Older phase labels below are retained as implementation history and must not be used as the current completion status.

See [Architecture and Product Map](docs/architecture-and-product-map.md) for the complete agent catalogue, orchestration routes, build status, founder-facing Blueprint flow, UI sequencing decision and V1 preservation plan.

An evidence-first, agentic founder research system built with n8n, Supabase, You.com, Nebius Token Factory, Pinecone, and Streamlit.

## Status

Phases 1–5 and the complete dynamic Phase 6A–6G backend are implemented. Staged planning, typed handoffs, durable HITL, accepted-evidence Pinecone projection, confirmed Founder Journey Mem0, profile-impact reruns, bounded failure recovery, observability, and the repeatable 66-case evaluation gate are live-safe verified. Authenticated Streamlit integration and submission assets remain.

- [Phase 6 implementation and live evidence](docs/phase-6-supervisor-chat-quality.md)
- [Phase 6C/6D/6E2 memory and rerun evidence](docs/phase-6c-6d-6e2-evidence.md)
- [Phase 6F/6G resilience and evaluation evidence](docs/phase-6f-6g-resilience-evaluation-evidence.md)
- [Requirement-by-requirement checklist status](docs/requirements-checklist-status.md)
- [Current build status and next steps](docs/build-status-and-next-steps.md)

## Source plans

- `../blueprint.md` — product and agent architecture
- `../implementation-plan.md` — phased build runbook
- `../requirements-readiness.md` — hackathon requirement traceability

## Build rule

A phase is complete only after its success and failure checks pass. Never commit API keys, JWTs, webhook secrets, raw private research inputs, or n8n credential values.
