# Blueprint Evidence Dev — Product Modules and Phase Map

Last updated: 29 August 2026

## Product promise

Blueprint is a founder workspace for an existing idea. The founder can request one research module or the complete blueprint. The system collects current public evidence, separates evidence from assumptions, performs deterministic calculations, adapts its route to gaps and contradictions, and produces a cited decision package plus the next validation experiment.

The product must support many industries; one demo idea is only a repeatable evaluation fixture and is never hard-coded into the prompts, routes, schemas, or UI.

## Founder-selectable modules

| UI choice | What Blueprint produces | Primary agents |
|---|---|---|
| Customer & demand | Pain language, frequency/context signals, workarounds, buying triggers, WTP evidence level, missing evidence, interview plan | Idea Framer, Customer Evidence, Auditor |
| Competitors & alternatives | Direct/indirect/manual/non-consumption landscape, verified feature/pricing/MVP cards, strengths, weaknesses, customer likes/dislikes, gaps, positioning opportunities | Competitor Discovery, Website Extractor, Auditor |
| Market opportunity | Stable segment definition, bottom-up market range, trends, constraints/regulation, source-backed assumptions and sensitivities | Market/Economics, Auditor |
| Financial viability | Founder budget/runway, staged evidence budget, pricing/subscription scenarios, unit economics, break-even/runway cases and spend gates | Financial Scenario, Market/Economics, Auditor |
| First users & validation | Where qualified first users can be found, channel reasoning, interview guide, outreach draft that is never sent, experiment design and decision thresholds | Customer Evidence, Experiment Designer |
| Full Blueprint | All applicable modules, prioritized adaptively rather than run blindly, followed by one cited decision package | Supervisor and all required specialists |

Even a single selected module begins with a small Idea Frame because research without a customer/problem interpretation is unreliable. The founder's selection controls scope and budget; dependencies and evidence quality control execution order.

## Live research architecture

1. **Idea Framer** converts the idea and onboarding answers into explicit customer, problem, outcome, geography, business-model, constraint and uncertainty fields.
2. **Research Planner** creates bounded query families for customer language, purchase intent, workarounds, competitors, pricing, market and authoritative sources.
3. **Provider Gateway** sends allowlisted searches to You.com Web Search/Contents. It may directly fetch shortlisted first-party public pages and later use one optional fallback provider. It cannot crawl arbitrary founder-supplied infrastructure or invent evidence from model memory.
4. **Specialists** normalize sources into evidence cards instead of writing unsupported prose.
5. **Evidence Auditor** checks URL/provenance, excerpt-to-claim entailment, source type, freshness, duplication, contradiction, accessibility and prompt-injection indicators.
6. **Supabase** stores the authoritative idea frame, research tasks, sources, claims, scores, decisions and run state.
7. **Pinecone** receives only accepted evidence summaries for owner/project-scoped semantic retrieval; every retrieved ID is revalidated in Supabase.
8. **Synthesis** uses accepted evidence and deterministic calculations only. Missing proof remains visible as `UNKNOWN` or `INSUFFICIENT_EVIDENCE`.

Research failure behavior:

- Empty search broadens terminology once and tries an adjacent source family once.
- A blocked website leaves first-party fields unknown and continues with permitted sources.
- Partial competitor batches keep valid results and identify missing companies.
- Conflicting sources trigger targeted research or human review.
- Provider or budget exhaustion returns a cited partial blueprint; it never fills gaps from model memory.

## Competitor intelligence depth

Each verified competitor/alternative card should contain:

- category: direct, indirect, manual, service, non-consumption;
- verified identity, URL and target customer;
- core promise and likely MVP mechanism;
- features/capabilities with source URLs;
- current public pricing, packaging and free/trial model;
- positioning and acquisition/distribution clues;
- what customers praise and why;
- complaints, switching friction and unmet jobs;
- strengths, weaknesses and defensible advantages;
- freshness/accessibility status and missing fields;
- implication for the founder: copy, avoid, differentiate, or investigate.

The output includes a comparison matrix, positioning/gap map, evidence coverage, and a recommended wedge. It does not conclude “no competitors means unique”; it searches for manual workarounds and doing nothing.

## Customer and first-user depth

Public research is not mislabeled as user interviews. It can identify:

- exact problem language and last-event descriptions;
- current workflows/workarounds and reported cost or consequence;
- solution requests, switching events, price objections and purchase-intent signals;
- communities, professional groups, marketplaces, directories and partner channels where qualified users appear;
- a ranked first-user channel plan based on qualification, access, density, trust and cost;
- an interview/recruitment guide and outreach draft for founder approval, but it never sends it;
- a W0–W4 willingness-to-pay assessment, from no evidence through binding commitment.

## Financial analysis layers

Financial work separates founder inputs, sourced facts, calculated outputs and assumptions.

### Founder inputs

- available capital and currency;
- maximum amount at risk and protected reserve;
- hours available per week and launch horizon;
- personal/business runway if the founder chooses to provide it;
- existing fixed/variable costs, existing revenue and prior spend;
- intended business model and price hypothesis;
- success target, such as first customers, monthly revenue or income replacement.

### Deterministic calculations

1. **Evidence budget:** customer research, prototype/validation, minimal build, distribution and reserve buckets with release conditions.
2. **Pricing/subscription scenarios:** tiers, monthly/annual assumptions, trial/freemium tradeoffs and WTP evidence behind each price.
3. **Unit economics:** ARPU, gross margin, contribution margin, CAC range, churn/retention, LTV and CAC payback when inputs exist.
4. **Break-even:** customers or transactions required to cover monthly fixed cost.
5. **Runway:** conservative/base/upside cash duration and monthly burn.
6. **Staged capital plan:** what may be spent now, what unlocks after problem evidence, what unlocks after payment evidence and what remains reserve.
7. **Sensitivity:** which one or two assumptions most change viability.

The LLM explains scenarios but never performs arithmetic. Code nodes calculate from versioned formulas. Unsupported inputs remain editable assumptions, and results are planning scenarios—not financial advice.

## Reusing the previous Streamlit application

Reference repository: `https://github.com/kajalchourasia-cmd/blueprint`

| Existing element | Reuse | Required change |
|---|---|---|
| Landing page and visual design | Yes | Connect project creation to Supabase Auth and BP-API-01 |
| Eight onboarding questions | Yes | Add research-module selection, currency/reserve/runway and consent/provenance fields |
| Roadmap & Progress dashboard | Yes | Replace session-state completion with Supabase run state and safe agent trace |
| Full Blueprint map | Yes | Bind nodes/statuses to actual hypothesis/evidence dependencies |
| Financial panel | Yes | Replace static CSV allocation with calculated, source/assumption-labelled scenarios |
| Inputs/Profile page | Yes | Persist owner-scoped edits; invalidate dependent evidence when material fields change |
| Data Library | Yes | Show real evidence cards, URLs, excerpts, dates, verdicts and limitations |
| CSV planning priors | Partially | Retain only as clearly labelled planning templates/fallbacks; never present as live research |
| Groq/Instructor generation | No for V1 | Replace with n8n + Nebius structured-output contracts |
| Streamlit session state as storage | No | Replace with Supabase Auth/Postgres/Storage |

The dashboard contract is idea-specific rather than a fixed checklist. The product idea and starting position remain at the top. Four key signals—completion, open assumptions, positive signals, and open risks—are computed from durable run data. Each roadmap section is clickable and carries `NOT_REQUESTED`, `BLOCKED`, `NEEDS_INPUT`, `IN_PROGRESS`, `AGENT_DONE`, `HUMAN_REVIEW`, `COMPLETED`, `PARTIAL`, or `SAFE_FAILED`; it exposes completed agent work, evidence, limitations, and the exact founder questions still blocking progress. Financial readiness, full Blueprint, validation, launch/distribution, and growth/optimization appear only when requested or unlocked by dependencies.

The previous GitHub repository is a read-only design reference. Implementation belongs in the current `blueprint-v2` / `blueprint-evidence-dev` work unless the founder explicitly chooses another repository.

## Standardized compressed phase map

| Phase | Status | What is built in this phase | Where it lives | User involvement |
|---|---|---|---|---|
| 1. Secure foundation | Complete | Persistent n8n, Supabase schema/RLS/state, BP-90 and credential isolation | Docker n8n + Supabase | Setup already completed |
| 2. Provider capability | Complete | You.com reachability, three Nebius model roles, Pinecone data-plane test | n8n setup workflows | None |
| 3. Secure intake and scope | Complete except live UI JWT test | Authenticated/idempotent Start Run, request schemas, `OUT_OF_SCOPE` denial | n8n BP-API-01 + Supabase RPC | No action now |
| 4. Core evidence vertical slice | Complete and live-verified | Idea Framer, Research Planner, Customer Evidence, different-family Evidence Auditor, one bounded repair, cited full/partial blueprint | `BP-CORE-45 Evidence Blueprint` + schemas + Supabase migration 006; execution `201` | None |
| 5. Research and finance suite | Complete and live-verified | Competitors, market/economics, deterministic Financial Scenario, first-user, validation experiment, launch/distribution and growth hypotheses | Same 42-node workflow; execution `201` accepted 23 directional citations and reached synthesis | None |
| 6. Adaptive orchestration/HITL | Pending | Supervisor, route guard, module selection, parallel tasks, clarification/resume, approval, loop/budget limits and stale invalidation | n8n BP-00 + Supabase state | Answer/approve one demo checkpoint |
| 7. Streamlit integration | Pending, existing UI reusable | Auth, onboarding, module picker, progress, evidence library, finance and final Blueprint | Streamlit app reused from previous repo | Sign in and run one end-to-end test |
| 8. Evaluation/hardening | Pending | Happy/partial/failure/scope/security fixtures, citation and route metrics | evals + n8n + Supabase | Inspect pass table |
| 9. Submission | Pending | Sanitized repository, setup, architecture, sample runs and video | GitHub + docs | Approve/record demo |

## Complexity visible to judges

The demo must show more than many agents running sequentially. It should visibly demonstrate:

1. module selection changing the research plan;
2. a source becoming an evidence card and then being accepted/rejected by a different-family auditor;
3. a contradiction or empty result changing the next route;
4. a deterministic financial calculation with editable assumptions;
5. one clarification or approval pause and resume;
6. one out-of-scope denial;
7. a partial/failure path that still produces a useful, cited result;
8. the final Blueprint separating facts, calculations, assumptions and unknowns.
