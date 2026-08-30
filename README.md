# Blueprint

Blueprint is an evidence-first decision system for turning an unfinished product or business idea into the next provable move.

## Product walkthrough

- **Video Walkthrough:** [Loom Link](https://www.loom.com/share/de86feccf09e4e1895856799e4a0542b)
- **Streamlit Link Demo:** [Streamlit link](https://blueprintxo.streamlit.app/)

Instead of producing a generic plan, Blueprint combines founder context, executable phase actions, planning priors, financial gates, and observed evidence. The interface keeps those sources visibly separate so an estimate is never presented as validation.

## Product flow

1. Describe an unfinished idea on the landing page.
2. Complete eight short onboarding questions about audience, goal, resources, prior work, and constraints.
3. Generate a personalized Roadmap & Progress dashboard.
4. Work through phases from Foundation to Growth & optimization.
5. Expand an action to see what to do, why it matters, a framework, and the done rule.
6. Mark actions complete and watch phase progress update.
7. Open the full Blueprint to inspect the complete system map, dependencies, and decision gates.
8. Review the financial plan, key signals, user inputs, data library, and product case study.

## Main surfaces

- **Landing and onboarding** — an animated idea-to-evidence entry point and an eight-question modal.
- **Roadmap & Progress** — completion, assumptions, positive signals, risks, phase navigation, executable actions, quick notes, and capital planning.
- **Full Blueprint** — a connected system map for phases, actions, dependencies, and return paths.
- **User inputs** — editable project context.
- **Data library** — inspectable CSV-backed planning sources and provenance.
- **Case study** — problem, product thesis, user goals, iterations, processing pipeline, information architecture, strategy, and reflection.

## Authenticated V2 data flow

Blueprint V2 now uses real Supabase email/password authentication. The browser receives only the Supabase publishable key; provider keys and Supabase secret/service-role credentials stay in n8n. Every n8n and Supabase request carries the signed-in founder's JWT, and Supabase RLS keeps projects and runs owner-scoped.

1. Sign in or create a Supabase account.
2. Submit the idea and choose Customer, Competitor, and/or Market Research (all three are selected by default).
3. Streamlit sends the authenticated, idempotent start request to `BP-API-01` in n8n.
4. n8n creates the owned project/run, then dispatches Foundation plus only the selected research streams to the Supervisor.
5. The dashboard reads owner-scoped progress, Blueprint versions, observability, and pending founder checkpoints from Supabase.
6. Founder decisions are state-version checked before the orchestrator resumes.
7. Signing out revokes the Supabase session and clears local project state. Signing back in reloads the founder's durable projects and latest runs.

The existing dashboard design is intentionally preserved for the later UI refinement pass. A compact live-research panel currently exposes real status, partial-projection failures, refresh, and HITL decisions.

## Data model

The V1 visual prototype still uses bundled CSV planning data. V2's canonical user, project, run, evidence, Blueprint, checkpoint, trace, failure, and version state lives in Supabase; n8n owns orchestration. Pinecone and Mem0 remain bounded projections, never the source of truth.

- `blueprint_idea_master.csv` — idea archetypes and planning attributes.
- `blueprint_phase_actions.csv` — executable phase actions, scripts, deliverables, costs, and decision signals.
- `blueprint_signal_benchmarks.csv` — signal definitions and thresholds.
- `blueprint_financial_models.csv` — budget buckets and release conditions.
- `blueprint_evidence_events.csv` — observed evidence records.
- `founder_journeys.csv` — reference founder journeys.
- `cost_templates.csv` — money, time, relationship, health, and opportunity-cost priors.
- `gap_library.csv` and `evidence_resources.csv` — missing questions, perspectives, frameworks, and learning support.
- `phase_library.csv` — phase structure and completion signals.

The app distinguishes three provenance levels:

- **User input** describes intent and constraints.
- **Planning prior** suggests sequencing, estimates, and targets.
- **Observed evidence** records what happened outside the app and is the only source of market signals.

## Technology

- Python 3.11+
- Streamlit
- Pydantic v2
- Groq SDK and Instructor for optional structured AI generation
- Pandas and bundled CSV data
- Plotly
- Supabase Auth, PostgreSQL, RLS, and owner-scoped RPCs
- n8n authenticated webhooks and adaptive orchestration
- Streamlit session state for short-lived UI state only

The app includes a deterministic fallback, so the complete prototype works without an API key. When a Groq key is configured, Blueprint can use structured LLM generation.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
streamlit run app.py
```

Open `http://localhost:8501`.

## Configuration and secrets

Local secrets belong only in `.env` or `.streamlit/secrets.toml`. Both are excluded from Git. Use `.env.example` and `.streamlit/secrets.toml.example` as templates.

Required Streamlit settings:

```toml
SUPABASE_URL = "https://gudsbrmphrokpnzmrlqd.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "your Supabase publishable key"
N8N_START_WEBHOOK_URL = "http://localhost:5679/webhook/blueprint/start"
REQUEST_TIMEOUT_SECONDS = "35"
```

Do not put You.com, Nebius, Pinecone, Mem0, Supabase secret/service-role, or database credentials in Streamlit. Those belong only in n8n credentials.

For Streamlit Community Cloud, add these settings through the app's Advanced settings instead of committing them. `localhost:5679` works only for a local Streamlit app. A cloud Streamlit deployment needs a public HTTPS n8n endpoint before the authenticated start flow can work.

## Repository structure

```text
blueprint/
├── app.py
├── pages/
│   ├── 1_📝_Questions.py
│   ├── 2_🗺️_Your_Plan.py
│   ├── 3_⚙️_Profile_Settings.py
│   ├── 4_📊_Data_Library.py
│   ├── 5_🎛️_Inputs.py
│   └── 6_🧭_Case_Study.py
├── blueprint/
│   ├── schemas.py
│   ├── llm.py
│   ├── prompts.py
│   ├── reality_check.py
│   ├── plan_generator.py
│   ├── gap_generator.py
│   ├── cost_calculator.py
│   ├── coach.py
│   ├── state.py
│   ├── app_navigation.py
│   ├── blueprint_map.py
│   └── product_dashboard_v2.py
├── data/
├── docs/
├── backend/
│   ├── n8n/          # Importable orchestration workflows
│   ├── supabase/     # Ordered migrations, verification, and RLS tests
│   ├── schemas/      # Typed workflow/API contracts
│   ├── evals/        # Frozen regression fixtures and latest report
│   ├── scripts/      # Workflow builders, validators, and evaluator
│   └── docs/         # Architecture, boundaries, evidence, and build log
├── scripts/
├── .streamlit/config.toml
└── requirements.txt
```

## Documentation

- [Information architecture](docs/information-architecture.md)
- [Recording guide](docs/VIDEO-TRANSCRIPT-CUES.md)
- [Clean walkthrough transcript](docs/VIDEO-TRANSCRIPT.md)
- [Case-study presentation transcript](docs/CASE_STUDY_PRESENTATION_TRANSCRIPT.md)

## Deployment

The production entrypoint is `app.py` on the `main` branch. Streamlit Community Cloud installs dependencies from the root `requirements.txt` file.

## Current scope

Implemented in this slice: real sign-up/sign-in/token refresh/logout, owner-scoped project recovery, authenticated idempotent start, three-stream selection, live run status, safe partial projection handling, and founder checkpoint decisions. Detailed dynamic section rendering, profile-impact reruns, and final authenticated two-user acceptance remain before submission. See [Phase 7 authentication integration](docs/PHASE-7-AUTH-INTEGRATION.md).
