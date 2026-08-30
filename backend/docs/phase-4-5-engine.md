# Phase 4–5 Evidence Blueprint Engine

## Current state

`BP-CORE-45 Evidence Blueprint` is imported into the local Blueprint Evidence Dev n8n instance with ID `bpCore45Evidence01`. It is inactive, connected to BP-90, and references only the existing `BP You Search` and `BP Nebius Token Factory` credentials. Static validation passed: 42 unique nodes, no missing connection targets, no Code-node syntax errors, all required specialist roles present, no Supabase/Pinecone write URLs, one bounded repair branch, and one safe-partial branch.

Live acceptance passed on n8n execution `201` on 30 August 2026. The run completed in 77.648 seconds, all three You.com research calls succeeded, all specialist roles succeeded, the different-family auditor accepted 23 directional citations across customer, competitor, and market streams, no repair was needed, and the workflow reached the complete synthesis path. The output kept exact market size, willingness to pay, conversion, and forecast claims explicitly unknown rather than promoting search excerpts to high-stakes proof.

## What one execution does

1. Accepts a Supervisor payload or the clearly labelled manual safe fixture.
2. Rejects malformed or out-of-scope action fields.
3. Frames the founder's idea without inventing missing facts.
4. Builds bounded customer, competitor, and market search queries.
5. Calls You.com for all three evidence streams.
6. Normalizes URLs and excerpts into evidence cards with provenance and limitations.
7. Runs separate Customer Demand, Competitor Intelligence, and Market/Economics analyses.
8. Calculates budget allocation, runway, and break-even scenarios deterministically when inputs exist; otherwise it asks precise financial questions.
9. Proposes first-user channels, validation experiments, launch sequence, and growth hypotheses. Every external action remains a proposal requiring founder approval.
10. Sends the complete evidence/analysis package to the different-family silent auditor.
11. If coverage or support is weak, performs exactly one targeted additional search and re-audits. It cannot loop again.
12. If the evidence gate passes, produces a cited idea-specific blueprint. Otherwise, it returns a useful `PARTIAL` or `HUMAN_REVIEW` blueprint with unknowns and questions visible.

## Dashboard output contract

The result contains the product idea, starting position, completion, open assumptions, positive signals, open risks, financial plan, citations, limitations, and module sections. Each section has a status, completion percentage, summary, open founder questions, and accepted evidence IDs. `AGENT_DONE` is deliberately different from `COMPLETED` so the UI cannot hide a required founder answer or approval.

Migration `006_blueprint_sections_dashboard.sql` provides the durable `blueprint_sections` table and authenticated `get_blueprint_dashboard(project_id)` RPC. Its table, RLS, four owner-only policies, authenticated access, and anonymous denial passed 5/5.

## Live acceptance evidence

- Execution: `201`; manual; `success`
- Started/stopped: `2026-08-29 18:35:45.621` / `2026-08-29 18:37:03.269` UTC
- Research: three successful You.com streams
- Audit: `PASS`, `can_synthesize=true`, no contradiction, no human escalation, no repair
- Accepted citations: 23, each labelled as directional search-excerpt evidence
- Final route: Blueprint Synthesis → schema-valid complete/partial evidence-led blueprint; safe-partial node did not run
- High-stakes guardrail: no verified market size, WTP, conversion, or forecast claims were asserted

Phase 6 now connects the verified core to authenticated run state, Supabase persistence, clarification/resume, approvals, Pinecone accepted-evidence memory, and cancellation.
