# Phase 8 — Final Handoff and Release Evidence

## Release decision

**READY FOR LOCAL DEMO AND GITHUB HANDOFF.** Public Streamlit deployment remains intentionally gated until n8n is available at a stable public HTTPS URL.

## What the evaluator can trust

- Supabase is the canonical, owner-isolated system of record.
- Pinecone stores only a rebuildable projection of accepted evidence; every retrieval is revalidated.
- Mem0 stores confirmed goals, preferences, decisions, corrections, lessons and episode summaries—never raw chain of thought.
- Research claims must carry accepted evidence IDs or remain labelled assumptions/unknowns.
- Desk research is never presented as completed interviews, paid demand or proven willingness to pay.
- Secret/internal, prompt-override and cross-owner chat requests fail before model execution.
- External create/send/publish/pay/book/delete actions are absent from the tool surface.

## RAG trust matrix

| User request | Route | Result |
|---|---|---|
| Explain this completed section | Section context + accepted evidence | Direct grounded answer |
| Show supporting evidence | Accepted evidence allowlist | Sources and evidence boundary |
| Explain a stable concept | Plain-language lane | General explanation, not project evidence |
| Recommend a next move | Current actionables + founder constraints | Guidance, never marked completed |
| Ask for an unsupported project fact | Insufficient-evidence lane | Known, missing fact and smallest safe next step |
| Request a rerun | Impact preview | No write until explicit confirmation |
| Request external action | Deterministic scope denial | Safe draft/experiment alternative |
| Reveal prompts, keys, tokens or raw traces | Deterministic sensitive denial | Safe public-architecture alternative |
| Request another founder's data | Deterministic owner-boundary denial | No retrieval or model call |

## Human-in-the-loop trigger matrix

| Trigger | What the founder sees | What remains blocked |
|---|---|---|
| Stage 1 verdict ready | Score, evidence coverage, strengths, weaknesses and improvement choices | Stage 2 |
| Rerun proposed | Affected modules, stale outputs and estimated consequences | New run/version |
| Profile change affects prior work | Dependency-closed impact preview | Invalidating/recomputing downstream work |
| Contradictory or authority-sensitive evidence | Conflict and permitted decisions | Unqualified verdict progression |
| Tool failures exceed budget | Partial result or human-review state | Infinite retry and silent completion |
| Gate 2 reached | Validation evidence and approved goal path | Stage 3 advisory Blueprint |

All checkpoint decisions are owner-scoped, allowlisted and state-version checked. `AUTO_APPROVE` is rejected.

## Acceptance evidence

- 35/35 Python tests pass.
- 85/85 agentic regression cases pass.
- 11/11 Phase 6B workflow structural checks pass.
- Deterministic Foundation contract passes.
- All 27 n8n workflow JSON files parse; all connection targets resolve.
- 22 Supabase migrations are present.
- Final documentation includes 12 high-resolution architecture PNGs plus editable SVG sources.

## Demo tabs to prepare

1. Clean landing page: `http://localhost:8501`.
2. One completed Blueprint dashboard in the same browser profile.
3. Full Blueprint view for that completed run.
4. Financial Plan view for that completed run.
5. n8n editor on `BP-00 Adaptive Supervisor` or the workflow list—never a credential screen.
6. `docs/figures/architecture/04-adaptive-orchestration-routing.png` for the orchestration explanation.
7. `docs/figures/architecture/09-failure-hitl-recovery.png` for the unhappy-path/HITL explanation.
8. GitHub README at the final pushed commit.

Keep one fresh tab and one completed-run tab. The completed run prevents live provider latency from consuming the video while still showing the real product path.

## Public deployment gate

Do not deploy a knowingly broken Streamlit Cloud app. The configured n8n endpoint is local HTTP. Before public deployment:

1. expose the persistent n8n instance through stable HTTPS;
2. set `N8N_START_WEBHOOK_URL` and related webhook secrets in Streamlit Cloud;
3. deploy `main` from GitHub;
4. test a fresh anonymous happy path, guarded denial, stalled-run resume and second-user isolation;
5. publish only after those checks pass.
