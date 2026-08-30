# Blueprint Evidence Dev — Service Setup Guide

> Version: 0.2  
> Last verified: 29 August 2026  
> Scope: account readiness, development credentials, dedicated infrastructure, and redacted smoke tests before workflow implementation

## 1. What is required

| Service | Required now? | Blueprint responsibility |
|---|---|---|
| n8n | Yes | Workflow orchestration, routing, retries, tools and API webhooks |
| Supabase | Yes | Authentication, authoritative Postgres state, RLS, audit data and private artifacts |
| You.com | Yes | Web discovery and permitted page extraction |
| Nebius Token Factory | Yes | Fast routing/extraction, strong synthesis, and different-family evidence auditing |
| Fireworks | No for V1; optional later | Model-provider fallback only if Nebius proves insufficient |
| Pinecone | Yes | Derived semantic memory of accepted evidence; never the source of truth |
| GitHub | Yes before deployment/submission | Version control and submission repository |
| Streamlit Community Cloud | Later | Founder-facing UI deployment from GitHub |
| ElevenLabs | No for V1; optional polish | A post-completion spoken founder briefing only; not orchestration or evidence processing |
| Firebase | No | Duplicates Supabase Auth/database/storage and would add unnecessary identity/state complexity |
| LlamaIndex | No for V1 | n8n is the selected orchestration track; retrieval contracts are implemented directly |
| Tavily / Firecrawl / Reddit API | Optional later | Provider fallback or additional evidence, not a Phase 0 blocker |

## 2. Security rules before creating keys

1. Enable MFA/2FA on n8n, Supabase, Pinecone, GitHub, You.com and Nebius wherever offered.
2. Use a password manager. Do not save keys in screenshots, notes, chat, Markdown, n8n Set/Code nodes, pinned data, GitHub, or exported workflow JSON.
3. Create development-specific keys named `blueprint-evidence-dev-n8n`; do not reuse personal or unrelated production keys.
4. Put keys only into n8n Credentials. Streamlit later receives only its own server-side secrets and the Supabase publishable key.
5. Never expose a Supabase secret/service-role key in Streamlit or a browser. It bypasses RLS.
6. After every smoke test, record only `PASS`, HTTP status, model/index ID, timestamp, latency and a redacted error class.

Dashboard login and API authentication are two separate checks. Seeing a dashboard proves the browser session works; a successful minimal API call proves the key and billing/quota path work.

## 3. n8n setup — do this first

Recommended for the hackathon: **n8n Cloud**, unless a self-hosted instance already works reliably over HTTPS.

Current development deployment: self-hosted Docker container `blueprint-evidence-dev-n8n`, reachable locally at `http://localhost:5679`, with named volume `blueprint-evidence-dev-n8n-data` mounted at `/home/node/.n8n`. Migration and restart verification passed on 29 August 2026. The stopped container `nostalgic_bardeen-pre-volume-20260829-185909` and the dated backup under `Project/.local-backups/n8n/` are retained for rollback; do not delete either until the Blueprint workflows and credentials have been visually confirmed in the UI and a later backup exists.

1. Sign in to the n8n dashboard and confirm the correct workspace/account name.
2. Record Cloud/self-hosted and the visible n8n version in `preflight.md`.
3. Current-instance decision: additional shared projects trigger a paid upgrade, so use the existing Personal project. Prefix every Blueprint workflow with `BP-` and every Blueprint credential with `BP `. Tags such as `blueprint-evidence-dev` and `setup` are optional conveniences, not prerequisites. A paid project is not required for orchestration.
4. Add tags: `blueprint`, `api`, `agent`, `research`, `quality`, `error`, `setup`.
5. Set timezone to `Asia/Calcutta`; later set a 15-minute workflow timeout.
6. Create a disabled manual workflow named `BP-SETUP-00 Provider Smoke Tests`. Do not activate or expose a webhook.
7. Create these credentials from **Credentials → Add credential** or while configuring an HTTP Request node:

| n8n credential name | Generic auth | Header/value pattern | Test target |
|---|---|---|---|
| `BP You Search` | Header Auth | `X-API-Key: <secret>` | `POST https://ydc-index.io/v1/search` |
| `BP Nebius Token Factory` | Header Auth | `Authorization: Bearer <secret>` | `GET https://api.tokenfactory.nebius.com/v1/models?verbose=true` |
| `BP Pinecone` | Pinecone credential if available; otherwise Header Auth | `Api-Key: <secret>` | Describe the dedicated index, then data-plane test |
| `BP Supabase Public` | Header Auth | `apikey: <publishable key>` | project REST endpoint after schema exists |

The user JWT for Supabase is a dynamic `Authorization: Bearer <user JWT>` header, not a static n8n credential. Do not create the webhook HMAC credential until Streamlit integration.

8. In workflow settings, save failed executions during development. Avoid saving large successful raw webpages after debugging; Supabase will keep redacted provenance.
9. Keep the smoke-test workflow disabled after setup. Run n8n's security audit before submission and review unprotected webhooks, credentials, risky nodes and instance settings.

Workflow delivery convention: provide sanitized, importable n8n JSON files for Blueprint workflows whenever practical. Export/import files must never contain API-key values or credential exports. The user creates each named n8n credential once in the Credentials UI and, after import, selects it in the corresponding node if n8n cannot bind it automatically.

## 4. Supabase setup

1. Sign in at the Supabase dashboard and create a project with the display name `Blueprint Evidence Dev` in a development organization. Supabase generates its own technical project reference; do not rename the product to that reference.
2. Choose a region reasonably close to the n8n deployment. Store the generated database password in the password manager; it does not go into Streamlit or normal n8n HTTP nodes.
3. Wait until project health is green. Open **Connect** or **Settings → API Keys**.
4. Record the project URL/ref and copy the `sb_publishable_...` key into:
   - n8n credential `BP Supabase Public`; and
   - later, Streamlit Community Cloud Secrets.
5. Do **not** put an `sb_secret_...` or legacy `service_role` key in Streamlit. Do not add it to n8n in Phase 0. If an admin-only backend operation becomes unavoidable, create a separate narrowly used backend credential after authorization tests exist.
6. Open **Authentication → Providers → Email** and keep email/password enabled for the demo.
7. Create one dedicated demo user under **Authentication → Users**. Keep its password private. Do not weaken global production confirmation settings simply to speed up a demo.
8. Later, add the deployed Streamlit URL to Auth redirect URLs. During local development use the local URL only where required.
9. Do not manually create final tables from the dashboard. Phase 1 will apply a versioned SQL migration containing tables, grants, RLS and policies together.
10. In Phase 1, migration `001_foundation.sql` creates the private Storage bucket `blueprint-artifacts`; do not create it manually or make it public.
11. Phase 0 login check: dashboard opens, project is healthy, API Keys and Auth Users pages open, and the demo user exists.

Supabase Auth plus RLS is Blueprint's complete identity and authorization layer. Firebase is neither required nor helpful here.

## 5. Pinecone Builder setup

Use a dedicated index so this project never touches an unrelated existing index.

1. Sign in to Pinecone and confirm the organization shows the Builder plan.
2. Create an API key named `blueprint-evidence-dev-n8n` and store it directly in n8n credential `BP Pinecone`.
3. Create index `blueprint-evidence-dev`.
4. Select a dense index with **integrated embedding**.
5. Select model `llama-text-embed-v2`, keep its default **1024-dimensional** output, use cosine similarity, and map the model's text field to `chunk_text`. The console's **2,048 tokens** value is the maximum input length, not the dimension setting.
6. Use AWS `us-east-1` for the reproducible default unless the current console/model placement requires another supported Builder region.
7. Wait until index state is Ready. Record its index host and displayed configuration in `preflight.md`; the host is configuration, not the API key.
8. Do not manually create namespaces. The first upsert will create `bp-<project_uuid>` automatically.
9. Smoke test with one harmless record containing `_id`, `chunk_text`, `project_id`, `evidence_id`, `source_domain`, `retrieved_at` and `auditor_verdict`.
10. Search that namespace with a semantically related sentence, confirm the record returns, then delete the smoke-test namespace. Pinecone writes are eventually consistent, so a short bounded retry may be needed before search.

Pinecone contains only evidence already accepted by the auditor. Supabase remains authoritative and the workflow must continue if vector memory is temporarily unavailable.

## 6. You.com setup

1. Sign in at `https://you.com/platform` and confirm the usage/billing page is accessible.
2. Open the API Keys page and create `blueprint-evidence-dev-n8n`. Copy it once into n8n credential `BP You Search`.
3. In `BP-SETUP-00`, add an HTTP Request node:
   - method `POST`;
   - URL `https://ydc-index.io/v1/search`;
   - credential `BP You Search`;
   - JSON body `{"query":"founder customer discovery evidence","count":3}`.
4. PASS means HTTP 200 plus result URLs/titles. Record response structure and latency, not the full response.
5. Begin with snippets/highlights. Full-page extraction is used only when an agent needs the page, because it costs more and increases prompt-injection exposure.

## 7. Nebius Token Factory setup

The correct product name is **Nebius Token Factory**.

1. Sign in at `https://tokenfactory.nebius.com` with the account that owns the credits.
2. Create an API key named `blueprint-evidence-dev-n8n` and save it in `BP Nebius Token Factory`.
3. Run `GET https://api.tokenfactory.nebius.com/v1/models?verbose=true` from the smoke workflow.
4. Filter the response for currently available, affordable text models supporting JSON mode.
5. Shortlist role assignments:
   - `NEBIUS_FAST_MODEL`: economical and low-latency for routing, framing, query generation and extraction;
   - `NEBIUS_STRONG_MODEL`: higher-quality model for synthesis, contradiction arbitration and one repair;
   - `NEBIUS_AUDIT_MODEL`: preferably a different model family from the strong model.
6. Run one minimal Chat Completions request per shortlisted model against `https://api.tokenfactory.nebius.com/v1/chat/completions` using a strict JSON schema.
7. PASS requires HTTP 200, valid schema output, model ID, usage and acceptable latency. Record only exact model IDs and test metrics, never the key.
8. If only two models pass, the fast model may also handle routine audit extraction, but the final evidence verdict should use the model family different from synthesis.

## 8. Fireworks decision

Do not create a Fireworks V1 project, development key, n8n credential, or smoke-test node. The existing account may remain logged in, but it is outside the critical path. Add it later only if Nebius availability or model diversity fails evaluation; doing so requires a separate adapter, budget and failure tests.

## 9. GitHub and Streamlit setup

### GitHub — prepare now

1. Use the user-selected repository [`kajalchourasia-cmd/blueprint-v2`](https://github.com/kajalchourasia-cmd/blueprint-v2). The repository name is an explicit exception to the technical-slug convention and must not be changed without new user authorization.
2. Do not initialize it with unrelated sample files. The local implementation folder already contains the starting README and `.gitignore`.
3. Before the first push, run a secret scan and confirm `.env`, `.streamlit/secrets.toml`, raw exports and private evaluation results are ignored.
4. The repository can be made public only after every n8n export and artifact has been sanitized.

### Streamlit — account now, deployment later

1. Sign in to Streamlit Community Cloud using the GitHub account and authorize only the required repository/workspace.
2. Do not create/deploy the app until Phase 5; the webhook contracts and authentication must exist first.
3. Local secrets later live in `.streamlit/secrets.toml`, which is ignored by Git. Cloud secrets go in the app's Advanced settings.
4. Streamlit receives the Supabase URL/publishable key and n8n webhook configuration. It never receives You.com, Nebius, Pinecone, Supabase secret/service-role or database passwords.

## 10. Phase 0 completion checklist

- [ ] n8n deployment type/version recorded; Personal-project fallback confirmed; mandatory `BP-` workflow and `BP ` credential naming applied; optional tags may be omitted.
- [ ] Supabase development project healthy; publishable key stored; demo user created.
- [ ] Dedicated Pinecone index Ready; test upsert/search/delete passed.
- [ ] You.com POST search passed.
- [ ] Nebius model list plus JSON-schema calls passed; fast, strong and audit role IDs selected.
- [ ] Fireworks is marked optional and has no V1 credential or workflow dependency.
- [ ] Existing GitHub repository `blueprint-v2` is protected by `.gitignore` and sanitized before any push; retain its user-selected name.
- [ ] Streamlit account connected to GitHub; app not yet deployed.
- [ ] Every visible project uses `Blueprint Evidence Dev`; technical identifiers use `blueprint-evidence-dev` only where spaces/case are unsupported.
- [ ] No Firebase project created.
- [ ] No LlamaIndex or ElevenLabs dependency added to the V1 critical path.
- [ ] No secret appears in chat, Markdown, Git, screenshots, pinned data or workflow exports.
- [ ] `preflight.md` updated only with non-secret settings and PASS/FAIL results.

Only after every mandatory item passes do we start Phase 1: Supabase migration/RLS, authenticated run creation, idempotent state transitions and `BP-90 Error and Audit`.

## 11. Official references

- [n8n documentation](https://docs.n8n.io/)
- [n8n security audit](https://docs.n8n.io/hosting/securing/security-audit/)
- [Supabase API keys](https://supabase.com/docs/guides/getting-started/api-keys)
- [Supabase Auth](https://supabase.com/docs/guides/auth)
- [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Pinecone quickstart](https://docs.pinecone.io/guides/get-started/quickstart)
- [Pinecone index creation](https://docs.pinecone.io/guides/index-data/create-an-index)
- [Pinecone namespaces](https://docs.pinecone.io/guides/index-data/implement-multitenancy)
- [You.com quickstart](https://you.com/docs/quickstart)
- [You.com API key management](https://you.com/docs/administration/api-keys)
- [You.com Search API](https://you.com/docs/api-reference/search/v1-search)
- [Fireworks onboarding](https://docs.fireworks.ai/getting-started/onboarding)
- [Fireworks OpenAI-compatible API](https://docs.fireworks.ai/tools-sdks/openai-compatibility)
- [Nebius Token Factory quickstart](https://docs.tokenfactory.nebius.com/quickstart)
- [Nebius model listing](https://docs.tokenfactory.nebius.com/api-reference/examples/list-of-models)
- [Nebius structured output](https://docs.tokenfactory.nebius.com/ai-models-inference/json)
- [Streamlit Community Cloud deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Streamlit secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
