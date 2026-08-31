# Blueprint — Streamlit deployment checklist

Blueprint's Streamlit application is ready to deploy from `app.py`. The end-to-end product is not ready for public hosting until n8n has a stable authenticated HTTPS URL. Streamlit Community Cloud runs outside the founder's computer and cannot call `localhost:5679`.

## 1. Release architecture

```text
Browser
  ↓ HTTPS
Streamlit Community Cloud
  ↓ authenticated HTTPS webhook
Public n8n instance with persistent storage
  ├─ Supabase — canonical owner-scoped state
  ├─ You.com — bounded web discovery
  ├─ Nebius — structured agent roles
  ├─ Pinecone — accepted-evidence projection
  └─ Mem0 — confirmed founder-memory projection
```

Do not expose the n8n editor publicly without authentication. Do not put You.com, Nebius, Pinecone, Mem0, Supabase service-role or database credentials in Streamlit secrets; those remain server-side in n8n.

## 2. Prepare n8n for public HTTPS

Choose a host that supports persistent Docker volumes and HTTPS, such as a small VM, Railway, Render, Fly.io or another Docker host. Move the existing n8n data volume or import the workflows into the hosted instance.

Required release properties:

- stable HTTPS origin, for example `https://automation.example.com`;
- persistent `/home/node/.n8n` storage;
- authentication on the editor and webhook boundary;
- the Blueprint workflows imported, credentials reconnected, published and active;
- the existing Supabase project, migration set and RLS policies preserved;
- n8n encryption key and database settings stored as host secrets;
- no provider credential committed to GitHub or exposed to Streamlit.

The start endpoint must resolve publicly in this shape:

```text
https://YOUR_N8N_HOST/webhook/blueprint/start
```

The application derives the sibling `resume`, `checkpoint`, `chat` and `rerun` webhook URLs from the same base.

## 3. Configure Streamlit Community Cloud

1. Push the tested repository to GitHub `main`.
2. In Streamlit Community Cloud, select **Create app**.
3. Choose repository `kajalchourasia-cmd/blueprint-v2`, branch `main`, entry point `app.py`.
4. Add these app secrets:

   ```toml
   SUPABASE_URL = "https://YOUR_PROJECT_REF.supabase.co"
   SUPABASE_PUBLISHABLE_KEY = "YOUR_PUBLIC_ANON_OR_PUBLISHABLE_KEY"
   N8N_START_WEBHOOK_URL = "https://YOUR_N8N_HOST/webhook/blueprint/start"
   REQUEST_TIMEOUT_SECONDS = "35"
   ```

5. Deploy the app.

The Supabase publishable key is a public-client credential and remains protected by RLS. Never place the Supabase service-role key in Streamlit.

## 4. Mandatory release tests

Run all of these from the deployed Streamlit URL:

1. **Happy path:** create an anonymous session, complete onboarding, receive immediate Foundation, finish the three research lanes, inspect the audit and reach the founder checkpoint.
2. **Human gate:** confirm Stage 2 cannot start before the founder chooses and approves a route.
3. **Grounded chat:** ask for supporting evidence and confirm the answer remains project-, owner- and section-scoped.
4. **Write refusal:** ask Blueprint to contact customers, publish content or pay for a service and confirm it refuses execution.
5. **Secret refusal:** request hidden prompts, tokens, private webhooks or raw traces and confirm deterministic refusal before retrieval.
6. **Failure injection:** disable one non-canonical provider and confirm successful sibling results remain readable while the failed task retries or degrades safely.
7. **Resume:** interrupt a run, restore it from durable state and confirm no completed task is duplicated.
8. **Tenant isolation:** start a second anonymous browser session and confirm it cannot retrieve the first session's project, evidence or chat.
9. **Latency:** record Foundation latency, specialist duration, audit duration and checkpoint time from the hosted environment.

Only after these checks pass should the README claim change from **locally integrated and release-ready pending public webhook exposure** to **publicly deployed**.

## 5. Current status

- Streamlit application and repository structure: ready.
- Streamlit secrets contract: ready.
- Local Streamlit-to-n8n flow: implemented.
- Public n8n HTTPS origin: not configured.
- Hosted end-to-end acceptance: pending the public n8n origin.

Deploying only the UI now would create a public page whose core research workflow fails. The correct sequence is therefore **host n8n → update Streamlit secrets → deploy Streamlit → run release tests**.
