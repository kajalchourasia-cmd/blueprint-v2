# Hackathon Requirements — Final Phase 8 Checklist

Audited against the Week 3 handout, supplied build checklist, sample-project solution kits, implemented workflows, current repository and final acceptance suite on 31 August 2026.

Legend: **DONE** = implemented and evidenced; **READY LOCALLY** = complete for the local demo but requires the stated hosting step for public access; **V2** = explicitly excluded from V1 and disclosed.

| Requirement | Status | Evidence |
|---|---|---|
| 1. Define the project and one-liner | DONE | Founder idea validation is narrow, useful and task-completion oriented; scope and success measure are documented. |
| 2. Specify end-to-end workflow | DONE | Landing → onboarding → durable run → Foundation → parallel research → audit → verdict → human gate → later stages/stop. |
| 3. Design routing deliberately | DONE | Typed deterministic routes, planner branches, dependency scheduling, missing-input, contradiction, retry, partial and terminal routes. |
| 4. Define agents and handoffs | DONE | Narrow roles, typed observations, shared state and explicit Supervisor/specialist/auditor/critic/checkpoint contracts. |
| 5. Create shared state model | DONE | Supabase is canonical; session, episodic, semantic and confirmed-journey memory have separate authority and lifetime. |
| 6. Implement tools safely | DONE | Read-only discovery/model tools; owner-scoped writes; idempotency; budgets; secrets remain server-side. |
| 7. Add grounding and validation | DONE | Accepted-evidence IDs, source lineage, Supabase revalidation, audit, deterministic score and uncertainty labels. |
| 8. Build bounded feedback loops | DONE | One repair/revision, re-audit, transition/tool/retry budgets and no unbounded self-loop. |
| 9. Add human-in-the-loop | DONE | Gate 1, Gate 2, rerun impact confirmation, profile-change consequences, contradictions and transition-cap escalation. |
| 10. Handle failures | DONE | Retry, repair, reload, partial completion, needs input, human review, policy denial and safe fail. |
| 11. Add observability | DONE | Correlation/run/task identity, route reason, attempt, provider/model, latency/error/evidence outcome and terminal state without chain of thought. |
| 12. Evaluate the system | DONE | 39/39 Python, 85/85 agentic regressions, 21/21 closed-loop checks, 11/11 workflow structure and deterministic Foundation pass. |
| 13. Prepare interface and output | DONE | No-login Streamlit workflow, visible state, detailed research, sources, actions, Full Blueprint, Financial Plan and section-scoped chat. |
| 14. Prepare submission assets | DONE | README, architecture pack, DOCX/PDF submission, demo runbook, transcript, limitations and repository handoff. |
| Public hosting | READY LOCALLY | Requires stable public HTTPS n8n endpoint before Streamlit Cloud can use the live orchestrator. |
| Uploaded-document ingestion / LlamaIndex | V2 | Deliberately excluded from V1; current RAG operates over accepted project evidence. |

## Three handout rules

1. **Task completion, not single-shot accuracy:** the measurable outcome is a founder reaching a visible verdict and next decision, including safe partial or stop states.
2. **State is the hard part:** Supabase owns exact durable truth; Pinecone and Mem0 are rebuildable, bounded projections; Streamlit state is ephemeral.
3. **Write actions deserve a human:** consequential state changes require a checkpoint; external sends, payments, bookings, publishing and deletion are not provisioned in V1.

## Final release boundary

The local submission is complete. Public deployment is blocked only by infrastructure reachability, not by missing application logic: `localhost` n8n must become a stable HTTPS service, then two-user isolation and public webhook acceptance must be rerun.
