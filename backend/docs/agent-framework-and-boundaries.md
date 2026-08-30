# Blueprint Evidence Dev — Agent Framework, Boundaries and Completion Contract

Last updated: 30 August 2026

This is the filled version of the Week 3 handout framework. It is the single reference for what Blueprint may do, what requires a founder, what it remembers, how it fails, and how end-to-end success is measured.

## Assignment one-liner

Blueprint helps an early founder with an existing idea complete an evidence-backed validation workflow in a Streamlit web app, replacing days of disconnected customer, competitor, market and financial research. An n8n Supervisor coordinates bounded read-only research and analysis tools, pauses for material ambiguity, correction, rerun or consequential action, and succeeds when the founder receives a quality-approved, cited, actionable Blueprint in under 12 minutes with at least 90% of material factual claims linked to accepted evidence and every run ending visibly.

## Filled agent framework

| Field | Blueprint Evidence Dev decision |
|---|---|
| Agent goal (one line) | Turn one founder idea, goal and constraints into a dynamic, cited and actionable validation Blueprint whose route changes with evidence, failures and founder decisions. |
| Where do people use it? | In an authenticated Streamlit founder workspace containing onboarding/profile, a dynamic roadmap, detailed research sections, evidence, signals, actions, reruns and Ask Blueprint. |
| What steps does it take, in order? | Validate scope and identity; load the current profile/state/memory; create a dependency-aware plan; run eligible research; audit results; repair, replan or pause as needed; calculate scenarios; synthesize and critique; persist the version, actions and memory; expose a visible terminal result. |
| What can it actually do? | **Autonomous reads:** search permitted public sources, fetch shortlisted pages, retrieve accepted project evidence/memory, compare and audit evidence, and calculate deterministic scenarios. **Private writes:** persist owner-scoped run state, evidence, audit, Blueprint versions and approved memories. **Proposal only:** prepare experiments, interview scripts, outreach/content drafts and rerun plans, but never execute external actions. |
| What does it need to remember? | The active run and checkpoint, exact project event history, immutable profile/Blueprint versions, accepted semantic evidence, corrections, confirmed decisions and distilled Founder Journey memories. State is isolated by owner and project and is never inferred from a loose timestamp or reused across founders. |
| What should it never do? | Never invent research, customers, interviews, citations, prices, market size or WTP; never reveal cross-user data, secrets, hidden reasoning or unnecessary personal information; never contact, send, publish, pay, purchase, book, delete externally, access private accounts or execute arbitrary founder-supplied tools/URLs. |
| Human-in-the-loop | Ask for a founder when material input is missing, sources conflict on a consequential claim, repairs are exhausted, a pivot/correction changes downstream work, a rerun is proposed, an experiment or final decision needs acceptance, memory is corrected/deleted, or any external/write action is requested. Review supports approve, reject, edit, more information, request changes, retry, override-with-reason and cancel. |
| What happens when something breaks? | Classify the failure, record a redacted observation, retry only temporary failures within a cap, use an allowlisted fallback where justified, preserve successful parallel work, ask the founder when authority/input is missing, and otherwise return a cited partial or safe failure. No branch continues silently and every run reaches a visible terminal/checkpoint status. |
| How do you know it worked? | End-to-end goal completion, not one good answer: at least 90% supported material facts, 100% visible terminal/checkpoint outcomes, schema-valid outputs after at most one repair, correct module/rerun routing on the eval set, and a founder-usable Blueprint in the target time/cost envelope. |

## The three handout rules translated into system gates

| Handout rule | Enforced Blueprint behavior | Acceptance evidence |
|---|---|---|
| Task completion, not single-shot accuracy | `COMPLETED` requires the required task graph to be terminal, synthesis/critique to finish, a usable artifact and actions to persist, and the founder to receive a visible result. A strong specialist answer cannot mark the run complete by itself. | End-to-end eval result, final state transition, artifact ID, quality verdict and visible dashboard status |
| State is the hard part | Supabase owns exact active/episodic state; Pinecone owns accepted semantic evidence; Mem0 owns distilled Founder Journey memory. Every record carries owner/project/run/version identifiers and explicit retention/deletion rules. | Resume test, version comparison, memory provenance, stale/superseded handling and cross-user isolation test |
| Write actions deserve a human | Public/project reads may be autonomous. Internal private persistence is allowlisted and owner-scoped. Any external create/modify/send/pay/delete/publish action is absent or denied; a future integration must be proposal-first and approval-gated. | Tool allowlist/permission table, denial fixture and approval checkpoint test |

## Version identity: never mix these concepts

| Identifier | Meaning | Example |
|---|---|---|
| `product_version` | The application capability release | `V1` research product; `V2` adds founder document upload |
| `profile_version` | Immutable version of onboarding answers, goals and constraints | Profile 3 changed budget and customer segment |
| `blueprint_version` | Immutable founder-facing Blueprint artifact | Blueprint 1 before interviews; Blueprint 2 after new evidence |
| `run_id` | One orchestration execution or rerun | A targeted competitor rerun |
| `module_run_id` | One execution of one roadmap module | Competitor research attempt 2 |
| `memory_id` | One distilled Mem0 memory with provenance | Confirmed decision to exclude enterprise buyers |

Questions such as “How has my idea changed?” use Supabase Blueprint/profile versions for the exact timeline, Mem0 to retrieve relevant confirmed journey memories, and Pinecone for the accepted evidence that caused the change. Mem0 never stores the entire Blueprint as the canonical copy.

## Memory duration and ownership

| State | Store | Duration/default | Correction/deletion behavior |
|---|---|---|---|
| Active task/checkpoint | Supabase | Until terminal state or cancellation; retained in project history afterward | Immutable event history plus a new corrective event |
| Profile and Blueprint versions | Supabase | Project lifetime until founder deletes the project | Never overwrite; create a new version and mark relationships |
| Accepted evidence and section/action retrieval | Pinecone + Supabase IDs | Project lifetime, with freshness/staleness checks before reuse | Delete vector when authoritative Supabase evidence is deleted/rejected; supersede rather than silently replace |
| Founder Journey memory | Mem0 | Project lifetime until corrected/deleted by the founder | Inspect, update/supersede or delete with an audit event |
| Raw/redacted tool/error diagnostics | Supabase/n8n operations | Target 30 days for detailed payloads; retain compact metrics/events longer | Automatic expiry; never place raw payloads into Mem0/Pinecone |
| Ask Blueprint messages | Supabase | Project lifetime for V1 unless the founder deletes the thread/project | Owner-scoped delete; do not promote chat text to Mem0 without an explicit input/decision or approved run outcome |

The 30-day diagnostic retention is the target policy and still requires an automated cleanup job before production claims are made.

## Ask Blueprint boundaries

Ask Blueprint is a project research interface, not an unrestricted chatbot.

### It may answer

- explanations of completed/current Blueprint sections;
- what sources support or oppose a claim;
- why a route, score, limitation, unknown or next action exists;
- comparisons between the founder's own Blueprint versions;
- goal-relative next steps;
- what would become stale if an input changed;
- a grounded proposal to rerun a module.

### It must not answer as fact

- questions for which the project contains no adequate accepted evidence;
- current prices, market sizes, WTP or competitor facts from model memory alone;
- claims about private individuals or inaccessible/private sources;
- legal, medical, investment or financial certainty;
- hypothetical customer interviews as if they happened;
- unrelated general-assistant requests outside founder validation.

When evidence is missing, it says `INSUFFICIENT_EVIDENCE`, explains the gap and offers a bounded research or founder-input proposal. When only partial evidence exists, it labels the answer partial and cites limitations.

### It must never execute

- email/message/call/contact;
- post/publish/update CRM or third-party records;
- purchase/pay/book;
- delete external data;
- arbitrary URLs, code or tools supplied in chat;
- a module rerun without a confirmation preview and explicit founder approval.

Safe denial:

> Blueprint can explain and research this founder project, but it cannot perform that external or unrelated action. I can instead provide a grounded draft, propose a validation experiment, or prepare a confirmed research rerun.

## Research-module boundaries

| Module | May do | Must stop, limit or ask |
|---|---|---|
| Foundation | Normalize founder inputs and identify hypotheses/unknowns | Ask one focused question instead of inventing a customer, problem, goal or constraint |
| Customer research | Analyze permitted public demand language, workarounds, buying/WTP signals and reachable segments | Never call public comments “interviews,” invent named customers or claim willingness to pay without evidence/experiment |
| Competitor research | Verify direct, indirect, service, manual and non-consumption alternatives and compare sourced attributes | Do not scrape private/login/paywalled content, fill blocked pricing/features from model memory, defame competitors or claim “no competitors means unique” |
| Market research | Use source-backed segment/trend/category evidence and deterministic bottom-up ranges | Never invent TAM or present directional snippets/unsupported forecasts as authoritative facts |
| Offer/pricing | Produce hypotheses and test plans from customer/competitor evidence | Never claim an optimal price without real payment evidence |
| Financial readiness | Calculate editable scenarios from founder inputs and sourced assumptions | Never provide financial advice or fabricate CAC, churn, margin, runway or revenue inputs |
| Validation/launch/growth | Recommend experiments, channels, drafts and metrics | Never send outreach or publish; never show traction KPIs before real traction data exists |

## Failure and HITL completion matrix

| Situation | Automatic behavior | Human path | Terminal/checkpoint result |
|---|---|---|---|
| Empty search | Broaden terminology once, try one adjacent source family | Ask only if the missing evidence is decision-critical | Continue with limitation or `PARTIAL` |
| Timeout/429/provider outage | Capped retry/backoff, then allowlisted fallback | Optional retry later | `PARTIAL` or `SAFE_FAILED` if no useful result |
| Malformed model output | Schema repair once, then fail closed | Review if the missing output blocks a consequential decision | `PARTIAL`/`HUMAN_REVIEW` |
| Blocked/inaccessible page | Preserve unknown, use permitted alternatives | Founder may provide a public source | Continue with explicit limitation |
| Contradictory evidence | Auditor records both sides and runs one targeted check | Founder decides only when the contradiction changes strategy or authority is unavailable | `HUMAN_REVIEW` or unresolved risk |
| Prompt injection in source/chat | Treat as untrusted data and ignore instructions | None unless a false positive blocks necessary evidence | Evidence rejected/limited |
| One parallel module fails | Preserve successful modules; do not restart everything | Targeted rerun proposal | `PARTIAL` plus rerun option |
| Profile correction | Version profile, compute affected dependencies and mark outputs stale | Founder confirms targeted/full rerun | Durable checkpoint then resume |
| Requested external action | Deny before tool execution | Offer draft/proposal only | `OUT_OF_SCOPE` for the action; project remains usable |
| Budget/retry/time exhausted | Stop additional calls and preserve best audited work | Founder may approve a later rerun with a new budget | Visible `PARTIAL`/`SAFE_FAILED` |

## V1/V2 RAG boundary

- **V1:** Pinecone retrieval over accepted live web evidence, Blueprint section summaries and actions for Ask Blueprint. RAG is a grounding tool inside the larger agentic workflow.
- **V2:** founder file upload, Supabase Storage, LlamaIndex parsing/chunking/deduplication, document trust/injection checks and page-level citations.

The project is never presented as “a chatbot with RAG.” Its judged value is adaptive task completion, state, tools, failure recovery, bounded autonomy and HITL.
