# Blueprint Evidence Dev — Architecture and Product Map

Last updated: 30 August 2026

## Status legend

- **Complete:** implemented and verified through a named test or live n8n execution.
- **In progress:** the design and contracts exist, but the complete workflow is not yet acceptance-tested.
- **Pending:** intentionally scheduled for a later phase.

## System architecture and build status

```mermaid
flowchart TB
    Founder[Founder with an existing idea]

    subgraph UI[Founder experience]
      ST[Streamlit V2\nPhase 7 — pending]
      DASH[Evidence dashboard\nPhase 7 — pending]
      MAP[Interactive Blueprint map\nV1 design exists; V2 binding pending]
      CS[Case study\nV1 preserved in GitHub]
    end

    subgraph ENTRY[Secure entry — complete]
      AUTH[Supabase Auth + RLS]
      API[BP-API-01 Start Run\nvalidate · scope guard · idempotency]
    end

    subgraph CONTROL[Adaptive control plane]
      SUP[BP-00 Supervisor\nPhase 6 — live-verified]
      ROUTE[Route guard + budgets\nloop limits · stale dependencies]
      HITL[Clarify · approve · edit · reject · resume\nPhase 6 — backend complete; UI pending]
    end

    subgraph CORE[BP-CORE-45 evidence engine — live verified]
      FRAME[Idea Framer]
      PLAN[Research Planner]
      SEARCH[You.com Provider Gateway]
      NORM[Evidence Normalizer]
      CUSTOMER[Customer Demand Agent]
      COMP[Competitor Intelligence Agent]
      MARKET[Market and Economics Agent]
      FIN[Financial Scenario Agent\ndeterministic calculations]
      EXP[Validation and Distribution Agent]
      AUDIT[Independent Evidence Auditor\ndifferent model family]
      REPAIR[One bounded research repair]
      SYNTH[Blueprint Synthesis Agent]
      PARTIAL[Safe partial / human-review result]
    end

    subgraph MEMORY[Durable state and memory]
      DB[Supabase run state · evidence · audit · sections\nfoundation complete]
      PC[Pinecone accepted-evidence projection\nPhase 6C live-tested]
      M0[Mem0 confirmed Founder Journey\nPhase 6D live-tested]
      ERR[BP-90 Error · Audit · Dead Letter\ncomplete and active]
    end

    Founder --> ST
    ST --> AUTH --> API --> SUP
    SUP --> ROUTE --> FRAME --> PLAN --> SEARCH --> NORM
    NORM --> CUSTOMER --> COMP --> MARKET --> FIN --> EXP --> AUDIT
    AUDIT -- supported --> SYNTH
    AUDIT -- weak coverage --> REPAIR --> AUDIT
    AUDIT -- contradiction / authority needed --> HITL --> SUP
    AUDIT -- still insufficient --> PARTIAL
    SYNTH --> DB
    PARTIAL --> DB
    DB --> PC
    DB --> M0
    SUP <--> DB
    SUP <--> PC
    SUP -. failure .-> ERR
    CORE -. failure .-> ERR
    DB --> DASH --> MAP
    ST --> CS

    classDef complete fill:#dff5e5,stroke:#287a42,color:#153c23;
    classDef progress fill:#fff1c7,stroke:#a36a00,color:#563700;
    classDef pending fill:#eceff3,stroke:#687386,color:#2c3440;
    class AUTH,API,FRAME,PLAN,SEARCH,NORM,CUSTOMER,COMP,MARKET,FIN,EXP,AUDIT,REPAIR,SYNTH,PARTIAL,DB,ERR,CS complete;
    class SUP,ROUTE progress;
    class ST,DASH,MAP,HITL,PC pending;
```

## Runtime orchestration logic

The Supervisor is not a single agent that writes the entire answer. It owns the route and asks narrow agents to perform bounded jobs. The current core workflow is live-verified; Phase 6 makes the routing durable, resumable and human-aware.

```mermaid
stateDiagram-v2
    [*] --> ValidateScope
    ValidateScope --> OutOfScope: request asks Blueprint to message, buy, publish, book, pay or delete
    ValidateScope --> FrameIdea: valid founder-research request
    FrameIdea --> NeedFounderInput: idea is too vague or a required decision is missing
    NeedFounderInput --> FrameIdea: founder clarifies
    FrameIdea --> PlanResearch: sufficient working frame
    PlanResearch --> GatherEvidence
    GatherEvidence --> SpecialistAnalysis
    SpecialistAnalysis --> EvidenceAudit
    EvidenceAudit --> TargetedRepair: weak or missing coverage and repair budget remains
    TargetedRepair --> EvidenceAudit
    EvidenceAudit --> HumanReview: contradiction, correction or founder authority required
    HumanReview --> PlanResearch: edit or request changes
    HumanReview --> SynthesizeBlueprint: approve supported direction
    EvidenceAudit --> SynthesizeBlueprint: evidence gate passes
    EvidenceAudit --> SafePartial: evidence remains insufficient
    SynthesizeBlueprint --> PersistAcceptedEvidence
    PersistAcceptedEvidence --> ValidationNext: real-world proof is still required
    SafePartial --> NeedFounderInput
    ValidationNext --> [*]
    OutOfScope --> [*]
```

## Agent and control catalogue

| Component | Type | What it can do | What it must not do | Status |
|---|---|---|---|---|
| Scope Guard | Deterministic control | Validate the contract, allow founder research, deny unrelated actions | Contact, purchase, publish, book, pay or delete | Complete |
| Supervisor | Orchestrator | Read run state, select the next eligible agent, enforce budgets, pause/resume and choose a terminal route | Invent research or bypass evidence/HITL gates | Phase 6 live-verified; authenticated persistence acceptance pending |
| Idea Framer | Fast reasoning agent | Convert a vague-but-usable idea into customer, problem, outcome, assumptions, missing questions and search terms | Present assumptions as facts | Complete |
| Research Planner | Deterministic/LLM-assisted planner | Create bounded customer, competitor and market queries within provider limits | Search indefinitely or silently expand scope | Complete |
| Provider Gateway | Tool adapter | Call You.com, classify provider failures and normalize responses | Treat provider output as automatically trusted | Complete |
| Customer Demand Agent | Specialist | Identify reported pain, workflows, alternatives, segments and directional demand signals | Claim real WTP without behavioral/payment evidence | Complete |
| Competitor Intelligence Agent | Specialist | Compare direct/indirect alternatives, positioning, public features, pricing claims, strengths and gaps | Invent private metrics or unsupported competitor capabilities | Complete |
| Market and Economics Agent | Specialist | Summarize category structure, drivers, constraints, business-model signals and unknowns | Invent TAM/SAM/SOM or forecasts | Complete |
| Financial Scenario Agent | Deterministic calculator | Calculate staged budgets, reserve, runway and break-even scenarios from founder inputs | Perform arithmetic through an LLM or present a scenario as financial advice | Complete |
| Validation and Distribution Agent | Specialist | Propose first-user channels, falsifiable experiments, thresholds, cost caps and launch hypotheses | Send outreach, recruit, buy ads or run experiments without approval | Complete |
| Evidence Auditor | Independent verifier | Test citation relevance, source limitations, coverage and contradictions; accept/reject evidence IDs | Add new research or accept plausible unsupported claims | Complete |
| Repair Router | Bounded feedback control | Run exactly one targeted search for the weakest stream and re-audit | Loop without limit | Complete |
| Blueprint Synthesis Agent | Strong synthesis agent | Produce an actionable, cited, idea-specific blueprint with assumptions and unknowns separated | Reintroduce rejected claims or fabricate certainty | Complete |
| BP-90 | Operational safety workflow | Record failures, audit transitions and dead letters; move exhausted runs to safe failure | Expose secrets or silently swallow failures | Complete |
| Human Checkpoint | Control/HITL | Ask a precise question and support approve, edit, reject, request changes, cancel and resume | Let an agent exercise founder authority | Backend complete; authenticated UI acceptance pending |
| Accepted-evidence Memory | Retrieval memory | Store only audited evidence in project-isolated Pinecone namespaces, revalidate against Supabase and degrade safely | Store rejected/untrusted excerpts as reusable truth | Phase 6C live-tested |
| Founder Journey Memory | Personalization memory | Store only confirmed goals, preferences, constraints, decisions, corrections, lessons and episode summaries | Replace canonical profile/run state or store raw reasoning/logs | Phase 6D live-tested; UI controls pending |
| Profile Rerun Controller | Deterministic/HITL control | Version profile edits, preview dependency impact, require approval and create targeted/full task plans | Overwrite prior Blueprints or silently rerun costly work | Phase 6E2 backend complete; authenticated UI acceptance pending |

## Founder-facing product flow

The V2 **Blueprint** page should retain the professional connected-decision map from V1, but its nodes must be generated from real Supabase state rather than Streamlit session-state estimates.

```mermaid
flowchart LR
    A[Sign in] --> B[Describe idea]
    B --> C[Choose research modules]
    C --> D[Confirm starting position\nbudget · time · geography · stage]
    D --> E[Research in progress]
    E --> F{Needs founder input?}
    F -- yes --> G[Clarify or approve]
    G --> E
    F -- no --> H[Dashboard]
    H --> I[Key signals\ncompletion · assumptions · positives · risks]
    H --> J[Clickable research sections]
    H --> K[Evidence library]
    H --> L[Financial readiness]
    H --> M[Full Blueprint map]
    M --> N[Foundation]
    M --> O[Customer demand]
    M --> P[Competitors]
    M --> Q[Market and economics]
    M --> R[Validation and proof]
    M --> S[Launch and distribution]
    M --> T[Growth and optimization]
    N & O & P & Q & R & S & T --> U[Decision gate and next action]
    U --> V[Download cited Blueprint]
```

Each map node opens a detail view containing: status, agent-completed work, accepted citations, rejected/limited evidence, calculations, assumptions, open risks, founder questions, dependencies and the next permitted action. The map must distinguish `AGENT_DONE` from `COMPLETED`.

## UI and integration sequencing decision

1. Collect and freeze navigation, dashboard sections, information hierarchy and required interactions **now**. These choices can affect the Phase 6 response and persistence contracts.
2. Build Phase 6 Supervisor/HITL against those contracts. Do not pause it for typography, colors or card styling.
3. At the start of Phase 7, apply the structural dashboard changes before binding screens to live Supabase/n8n data. This avoids integrating screens that will immediately be reorganized.
4. Bind the revised UI to Auth, Start Run, status, clarification, approval, evidence, finance and blueprint APIs.
5. Apply final responsive and visual polish only after the end-to-end path works.

Therefore, dashboard suggestions should be supplied before Phase 6 is finalized. Structural UI changes happen at the beginning of Phase 7; cosmetic polish happens after integration.

## V1 preservation decision

Blueprint V1 is the repository `https://github.com/kajalchourasia-cmd/blueprint`. Its clean local checkout points to that repository, and the V1 case-study page is tracked at `pages/6_🧭_Case_Study.py`. The original interactive map is tracked at `blueprint/blueprint_map.py`.

V1 remains unchanged as the product-history record. V2 belongs in `blueprint-v2` and must preserve V1 through documentation rather than overwriting it. Before final submission, V2 will include:

- `docs/v1-case-study/` containing the preserved case-study source/content or an approved archival snapshot;
- `docs/V1-TO-V2.md` explaining what V1 proved, what V2 changes and why;
- a visible Case Study navigation entry in Streamlit V2;
- the V2 architecture, agent map, build history, iterations, evaluation results and demo evidence;
- a link back to the immutable V1 repository and deployed V1 demo.
