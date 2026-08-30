-- Blueprint Evidence Dev
-- Migration 001: authoritative state, evidence, audit, RLS, and private artifacts
-- Apply once in the Supabase SQL Editor as the project owner.

begin;

create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table public.projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  idea_text text not null check (char_length(btrim(idea_text)) between 10 and 10000),
  optional_industry text check (optional_industry is null or char_length(optional_industry) <= 200),
  geography text check (geography is null or char_length(geography) <= 200),
  constraints jsonb not null default '{}'::jsonb check (jsonb_typeof(constraints) = 'object'),
  normalized_frame jsonb not null default '{}'::jsonb check (jsonb_typeof(normalized_frame) = 'object'),
  current_status text not null default 'ACTIVE' check (current_status in ('ACTIVE', 'ARCHIVED', 'DELETED')),
  deleted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (id, owner_id),
  check ((current_status = 'DELETED') = (deleted_at is not null))
);

create table public.runs (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  idempotency_key text not null check (char_length(idempotency_key) between 8 and 200),
  status text not null default 'NEW' check (status in (
    'NEW', 'FRAMING', 'NEEDS_INPUT', 'PLANNING', 'RESEARCHING', 'AUDITING',
    'WAITING_APPROVAL', 'SYNTHESIZING', 'COMPLETED', 'PARTIAL',
    'HUMAN_REVIEW', 'SAFE_FAILED', 'CANCELLED'
  )),
  current_route text check (current_route is null or current_route in (
    'IDEA_FRAME', 'CUSTOMER_DEMAND', 'COMPETITOR_INTELLIGENCE',
    'MARKET_ECONOMICS', 'EVIDENCE_AUDIT', 'EXPERIMENT_DESIGN',
    'BLUEPRINT_SYNTHESIS', 'FOUNDER_INPUT', 'HUMAN_REVIEW',
    'PARTIAL_COMPLETE', 'SAFE_FAIL', 'COMPLETE', 'CANCEL'
  )),
  current_node text,
  state_version integer not null default 0 check (state_version >= 0),
  transition_count integer not null default 0 check (transition_count between 0 and 20),
  search_cycle_count integer not null default 0 check (search_cycle_count between 0 and 3),
  tool_call_count integer not null default 0 check (tool_call_count between 0 and 80),
  revision_count integer not null default 0 check (revision_count between 0 and 3),
  cost_estimate_usd numeric(12,6) not null default 0 check (cost_estimate_usd >= 0),
  deadline_at timestamptz,
  original_request jsonb not null default '{}'::jsonb check (jsonb_typeof(original_request) = 'object'),
  missing_information jsonb not null default '[]'::jsonb check (jsonb_typeof(missing_information) = 'array'),
  safety_flags jsonb not null default '[]'::jsonb check (jsonb_typeof(safety_flags) = 'array'),
  final_output jsonb check (final_output is null or jsonb_typeof(final_output) = 'object'),
  final_artifact_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (id, owner_id),
  unique (owner_id, idempotency_key)
);

create table public.hypotheses (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid not null references public.runs(id) on delete restrict,
  hypothesis_type text not null check (hypothesis_type in (
    'CUSTOMER', 'PROBLEM', 'OUTCOME', 'WORKAROUND', 'WILLINGNESS_TO_PAY',
    'COMPETITOR', 'CHANNEL', 'MARKET', 'ECONOMICS', 'SOLUTION', 'RISK'
  )),
  statement text not null check (char_length(btrim(statement)) between 5 and 4000),
  source text not null default 'AGENT' check (source in ('FOUNDER', 'AGENT', 'EVIDENCE', 'EXPERIMENT')),
  importance numeric(5,4) not null default 0.5 check (importance between 0 and 1),
  confidence numeric(5,4) not null default 0 check (confidence between 0 and 1),
  status text not null default 'OPEN' check (status in ('OPEN', 'SUPPORTED', 'CONTRADICTED', 'STALE', 'RESOLVED', 'REJECTED')),
  depends_on uuid[] not null default '{}'::uuid[],
  stale_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (id, owner_id)
);

create table public.evidence (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid not null references public.runs(id) on delete restrict,
  hypothesis_id uuid references public.hypotheses(id) on delete restrict,
  claim text not null check (char_length(btrim(claim)) between 5 and 8000),
  stance text not null check (stance in ('SUPPORTS', 'CONTRADICTS', 'NEUTRAL', 'MIXED')),
  source_url text not null check (source_url ~* '^https://'),
  source_title text,
  source_domain text not null,
  source_type text not null check (source_type in (
    'FIRST_PARTY', 'GOVERNMENT', 'ACADEMIC', 'INDUSTRY', 'NEWS',
    'REVIEW', 'COMMUNITY', 'MARKETPLACE', 'OTHER'
  )),
  published_at timestamptz,
  retrieved_at timestamptz not null default now(),
  excerpt text check (excerpt is null or char_length(excerpt) <= 12000),
  query text,
  provider text not null check (provider in ('YOU', 'TAVILY', 'FIRECRAWL', 'DIRECT', 'FOUNDER', 'OTHER')),
  content_hash text not null check (char_length(content_hash) between 32 and 128),
  relevance_score numeric(5,4) check (relevance_score between 0 and 1),
  source_strength_score numeric(5,4) check (source_strength_score between 0 and 1),
  freshness_score numeric(5,4) check (freshness_score between 0 and 1),
  support_score numeric(5,4) check (support_score between 0 and 1),
  limitations jsonb not null default '[]'::jsonb check (jsonb_typeof(limitations) = 'array'),
  auditor_verdict text not null default 'PENDING' check (auditor_verdict in (
    'PENDING', 'ACCEPT', 'ACCEPT_WITH_LIMITATION', 'REPAIR', 'REJECT', 'HUMAN_REVIEW'
  )),
  pinecone_record_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index evidence_content_dedupe_idx
  on public.evidence (project_id, content_hash, coalesce(hypothesis_id, '00000000-0000-0000-0000-000000000000'::uuid));

create table public.competitors (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid not null references public.runs(id) on delete restrict,
  normalized_name text not null,
  domain text,
  category text not null check (category in ('DIRECT', 'INDIRECT', 'SERVICE', 'MANUAL_WORKFLOW', 'NON_CONSUMPTION')),
  verified_fields jsonb not null default '{}'::jsonb check (jsonb_typeof(verified_fields) = 'object'),
  unknown_fields jsonb not null default '[]'::jsonb check (jsonb_typeof(unknown_fields) = 'array'),
  verification_status text not null default 'CANDIDATE' check (verification_status in ('CANDIDATE', 'VERIFIED', 'PARTIAL', 'REJECTED')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (project_id, normalized_name)
);

create table public.agent_runs (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid not null references public.runs(id) on delete restrict,
  agent text not null check (agent in ('SUPERVISOR', 'IDEA_FRAME', 'CUSTOMER_DEMAND', 'COMPETITOR_INTELLIGENCE', 'MARKET_ECONOMICS', 'EVIDENCE_AUDITOR', 'EXPERIMENT_DESIGNER', 'BLUEPRINT_SYNTHESIS')),
  schema_version text not null,
  prompt_version text not null,
  input_hash text not null,
  output jsonb,
  provider text,
  model text,
  status text not null check (status in ('STARTED', 'SUCCEEDED', 'PARTIAL', 'RETRYING', 'FAILED', 'CANCELLED')),
  latency_ms integer check (latency_ms is null or latency_ms >= 0),
  input_tokens integer check (input_tokens is null or input_tokens >= 0),
  output_tokens integer check (output_tokens is null or output_tokens >= 0),
  cost_estimate_usd numeric(12,6) check (cost_estimate_usd is null or cost_estimate_usd >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (id, owner_id)
);

create table public.tool_calls (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid not null references public.runs(id) on delete restrict,
  agent_run_id uuid references public.agent_runs(id) on delete restrict,
  tool text not null,
  provider text not null,
  query_hash text,
  url_hash text,
  status_code integer,
  status text not null check (status in ('STARTED', 'SUCCEEDED', 'RETRYING', 'FAILED', 'SKIPPED')),
  duration_ms integer check (duration_ms is null or duration_ms >= 0),
  retry_count integer not null default 0 check (retry_count between 0 and 5),
  provenance jsonb not null default '{}'::jsonb check (jsonb_typeof(provenance) = 'object'),
  redacted_error jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.quality_checks (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid not null references public.runs(id) on delete restrict,
  agent_run_id uuid references public.agent_runs(id) on delete restrict,
  check_type text not null,
  rubric_scores jsonb not null default '{}'::jsonb check (jsonb_typeof(rubric_scores) = 'object'),
  failed_rules jsonb not null default '[]'::jsonb check (jsonb_typeof(failed_rules) = 'array'),
  repair_instructions jsonb not null default '[]'::jsonb check (jsonb_typeof(repair_instructions) = 'array'),
  before_score numeric(5,4) check (before_score between 0 and 1),
  after_score numeric(5,4) check (after_score between 0 and 1),
  verdict text not null check (verdict in ('PASS', 'REPAIR', 'FAIL', 'HUMAN_REVIEW')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.state_transitions (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid not null references public.runs(id) on delete restrict,
  from_status text not null,
  to_status text not null,
  route text,
  actor text not null check (actor in ('FOUNDER', 'SUPERVISOR', 'AGENT', 'AUDITOR', 'SYSTEM', 'ADMIN')),
  reason_code text not null,
  detail jsonb not null default '{}'::jsonb check (jsonb_typeof(detail) = 'object'),
  state_version integer not null check (state_version > 0),
  correlation_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (run_id, state_version)
);

create table public.research_tasks (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid not null references public.runs(id) on delete restrict,
  task_type text not null check (task_type in ('SEARCH', 'FETCH', 'EXTRACT', 'VERIFY', 'CALCULATE')),
  hypothesis_ids uuid[] not null default '{}'::uuid[],
  status text not null default 'PENDING' check (status in ('PENDING', 'LEASED', 'SUCCEEDED', 'PARTIAL', 'FAILED', 'TIMED_OUT', 'CANCELLED')),
  lease_owner text,
  leased_until timestamptz,
  timeout_at timestamptz,
  attempt_count integer not null default 0 check (attempt_count between 0 and 5),
  partial_result jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.approvals (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid not null references public.runs(id) on delete restrict,
  proposal_type text not null check (proposal_type in ('EXPERIMENT', 'SCOPE_CHANGE', 'FINAL_RECOMMENDATION', 'OTHER')),
  proposal_hash text not null,
  payload jsonb not null check (jsonb_typeof(payload) = 'object'),
  decision text not null default 'PENDING' check (decision in ('PENDING', 'APPROVE', 'REJECT', 'EDIT', 'REQUEST_CHANGES', 'MORE_INFORMATION', 'EXPIRED')),
  edits jsonb,
  expires_at timestamptz not null,
  decided_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (run_id, proposal_hash)
);

create table public.errors (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid references public.projects(id) on delete restrict,
  run_id uuid references public.runs(id) on delete restrict,
  error_class text not null check (error_class in ('AUTH', 'VALIDATION', 'PROVIDER', 'RATE_LIMIT', 'TIMEOUT', 'SCHEMA', 'QUALITY', 'CONFLICT', 'BUDGET', 'INTERNAL', 'UNKNOWN')),
  retryable boolean not null default false,
  workflow_name text not null,
  node_name text,
  safe_message text not null,
  redacted_technical_details jsonb not null default '{}'::jsonb check (jsonb_typeof(redacted_technical_details) = 'object'),
  recovery_action text,
  correlation_id text,
  resolved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (id, owner_id)
);

create table public.dead_letter_events (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid references public.projects(id) on delete restrict,
  run_id uuid references public.runs(id) on delete restrict,
  error_id uuid references public.errors(id) on delete restrict,
  payload_reference jsonb not null check (jsonb_typeof(payload_reference) = 'object'),
  originating_workflow text not null,
  originating_node text,
  failure_class text not null,
  correlation_id text not null,
  replay_eligible boolean not null default false,
  replay_count integer not null default 0 check (replay_count >= 0),
  resolution_status text not null default 'OPEN' check (resolution_status in ('OPEN', 'REPLAYED', 'RESOLVED', 'DISMISSED')),
  resolved_by uuid references auth.users(id) on delete restrict,
  resolved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.artifacts (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid not null references public.runs(id) on delete restrict,
  version integer not null check (version > 0),
  storage_path text not null,
  checksum text not null,
  format text not null check (format in ('MARKDOWN', 'JSON', 'PDF')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (id, owner_id),
  unique (run_id, version, format),
  unique (storage_path)
);

create table public.feedback (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid not null references public.runs(id) on delete restrict,
  usefulness_score integer check (usefulness_score between 1 and 5),
  accepted_recommendation boolean,
  founder_correction jsonb,
  note text check (note is null or char_length(note) <= 5000),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.runs
  add constraint runs_final_artifact_fk
  foreign key (final_artifact_id) references public.artifacts(id) on delete set null;

-- Composite ownership keys prevent a caller from linking an owned row to a
-- guessed project/run/parent identifier owned by somebody else.
alter table public.runs
  add constraint runs_project_owner_fk foreign key (project_id, owner_id)
  references public.projects(id, owner_id) on delete restrict;
alter table public.hypotheses
  add constraint hypotheses_project_owner_fk foreign key (project_id, owner_id)
  references public.projects(id, owner_id) on delete restrict,
  add constraint hypotheses_run_owner_fk foreign key (run_id, owner_id)
  references public.runs(id, owner_id) on delete restrict;
alter table public.evidence
  add constraint evidence_project_owner_fk foreign key (project_id, owner_id)
  references public.projects(id, owner_id) on delete restrict,
  add constraint evidence_run_owner_fk foreign key (run_id, owner_id)
  references public.runs(id, owner_id) on delete restrict,
  add constraint evidence_hypothesis_owner_fk foreign key (hypothesis_id, owner_id)
  references public.hypotheses(id, owner_id) on delete restrict;
alter table public.competitors
  add constraint competitors_project_owner_fk foreign key (project_id, owner_id)
  references public.projects(id, owner_id) on delete restrict,
  add constraint competitors_run_owner_fk foreign key (run_id, owner_id)
  references public.runs(id, owner_id) on delete restrict;
alter table public.agent_runs
  add constraint agent_runs_project_owner_fk foreign key (project_id, owner_id)
  references public.projects(id, owner_id) on delete restrict,
  add constraint agent_runs_run_owner_fk foreign key (run_id, owner_id)
  references public.runs(id, owner_id) on delete restrict;
alter table public.tool_calls
  add constraint tool_calls_project_owner_fk foreign key (project_id, owner_id)
  references public.projects(id, owner_id) on delete restrict,
  add constraint tool_calls_run_owner_fk foreign key (run_id, owner_id)
  references public.runs(id, owner_id) on delete restrict,
  add constraint tool_calls_agent_run_owner_fk foreign key (agent_run_id, owner_id)
  references public.agent_runs(id, owner_id) on delete restrict;
alter table public.quality_checks
  add constraint quality_checks_project_owner_fk foreign key (project_id, owner_id)
  references public.projects(id, owner_id) on delete restrict,
  add constraint quality_checks_run_owner_fk foreign key (run_id, owner_id)
  references public.runs(id, owner_id) on delete restrict,
  add constraint quality_checks_agent_run_owner_fk foreign key (agent_run_id, owner_id)
  references public.agent_runs(id, owner_id) on delete restrict;
alter table public.state_transitions
  add constraint state_transitions_project_owner_fk foreign key (project_id, owner_id)
  references public.projects(id, owner_id) on delete restrict,
  add constraint state_transitions_run_owner_fk foreign key (run_id, owner_id)
  references public.runs(id, owner_id) on delete restrict;
alter table public.research_tasks
  add constraint research_tasks_project_owner_fk foreign key (project_id, owner_id)
  references public.projects(id, owner_id) on delete restrict,
  add constraint research_tasks_run_owner_fk foreign key (run_id, owner_id)
  references public.runs(id, owner_id) on delete restrict;
alter table public.approvals
  add constraint approvals_project_owner_fk foreign key (project_id, owner_id)
  references public.projects(id, owner_id) on delete restrict,
  add constraint approvals_run_owner_fk foreign key (run_id, owner_id)
  references public.runs(id, owner_id) on delete restrict;
alter table public.errors
  add constraint errors_project_owner_fk foreign key (project_id, owner_id)
  references public.projects(id, owner_id) on delete restrict,
  add constraint errors_run_owner_fk foreign key (run_id, owner_id)
  references public.runs(id, owner_id) on delete restrict;
alter table public.dead_letter_events
  add constraint dead_letter_project_owner_fk foreign key (project_id, owner_id)
  references public.projects(id, owner_id) on delete restrict,
  add constraint dead_letter_run_owner_fk foreign key (run_id, owner_id)
  references public.runs(id, owner_id) on delete restrict,
  add constraint dead_letter_error_owner_fk foreign key (error_id, owner_id)
  references public.errors(id, owner_id) on delete restrict;
alter table public.artifacts
  add constraint artifacts_project_owner_fk foreign key (project_id, owner_id)
  references public.projects(id, owner_id) on delete restrict,
  add constraint artifacts_run_owner_fk foreign key (run_id, owner_id)
  references public.runs(id, owner_id) on delete restrict;
alter table public.runs
  add constraint runs_final_artifact_owner_fk foreign key (final_artifact_id, owner_id)
  references public.artifacts(id, owner_id) on delete restrict;
alter table public.feedback
  add constraint feedback_project_owner_fk foreign key (project_id, owner_id)
  references public.projects(id, owner_id) on delete restrict,
  add constraint feedback_run_owner_fk foreign key (run_id, owner_id)
  references public.runs(id, owner_id) on delete restrict;

create table public.allowed_run_transitions (
  from_status text not null,
  to_status text not null,
  primary key (from_status, to_status)
);

insert into public.allowed_run_transitions (from_status, to_status) values
  ('NEW', 'FRAMING'), ('NEW', 'HUMAN_REVIEW'), ('NEW', 'SAFE_FAILED'), ('NEW', 'CANCELLED'),
  ('FRAMING', 'NEEDS_INPUT'), ('FRAMING', 'PLANNING'), ('FRAMING', 'HUMAN_REVIEW'), ('FRAMING', 'SAFE_FAILED'), ('FRAMING', 'CANCELLED'),
  ('NEEDS_INPUT', 'FRAMING'), ('NEEDS_INPUT', 'PLANNING'), ('NEEDS_INPUT', 'HUMAN_REVIEW'), ('NEEDS_INPUT', 'SAFE_FAILED'), ('NEEDS_INPUT', 'CANCELLED'),
  ('PLANNING', 'RESEARCHING'), ('PLANNING', 'SYNTHESIZING'), ('PLANNING', 'WAITING_APPROVAL'), ('PLANNING', 'HUMAN_REVIEW'), ('PLANNING', 'PARTIAL'), ('PLANNING', 'SAFE_FAILED'), ('PLANNING', 'CANCELLED'),
  ('RESEARCHING', 'AUDITING'), ('RESEARCHING', 'PARTIAL'), ('RESEARCHING', 'HUMAN_REVIEW'), ('RESEARCHING', 'SAFE_FAILED'), ('RESEARCHING', 'CANCELLED'),
  ('AUDITING', 'RESEARCHING'), ('AUDITING', 'PLANNING'), ('AUDITING', 'SYNTHESIZING'), ('AUDITING', 'PARTIAL'), ('AUDITING', 'HUMAN_REVIEW'), ('AUDITING', 'SAFE_FAILED'), ('AUDITING', 'CANCELLED'),
  ('WAITING_APPROVAL', 'PLANNING'), ('WAITING_APPROVAL', 'RESEARCHING'), ('WAITING_APPROVAL', 'SYNTHESIZING'), ('WAITING_APPROVAL', 'HUMAN_REVIEW'), ('WAITING_APPROVAL', 'SAFE_FAILED'), ('WAITING_APPROVAL', 'CANCELLED'),
  ('SYNTHESIZING', 'COMPLETED'), ('SYNTHESIZING', 'PARTIAL'), ('SYNTHESIZING', 'RESEARCHING'), ('SYNTHESIZING', 'HUMAN_REVIEW'), ('SYNTHESIZING', 'SAFE_FAILED'), ('SYNTHESIZING', 'CANCELLED'),
  ('HUMAN_REVIEW', 'FRAMING'), ('HUMAN_REVIEW', 'PLANNING'), ('HUMAN_REVIEW', 'RESEARCHING'), ('HUMAN_REVIEW', 'AUDITING'), ('HUMAN_REVIEW', 'SYNTHESIZING'), ('HUMAN_REVIEW', 'SAFE_FAILED'), ('HUMAN_REVIEW', 'CANCELLED');

create index projects_owner_idx on public.projects(owner_id);
create index runs_owner_project_idx on public.runs(owner_id, project_id);
create index runs_status_route_idx on public.runs(status, current_route);
create index hypotheses_run_status_idx on public.hypotheses(run_id, status);
create index evidence_run_verdict_idx on public.evidence(run_id, auditor_verdict);
create index evidence_source_idx on public.evidence(source_domain, source_type, retrieved_at desc);
create index competitors_run_idx on public.competitors(run_id, verification_status);
create index agent_runs_run_idx on public.agent_runs(run_id, agent, status);
create index tool_calls_run_idx on public.tool_calls(run_id, status);
create index quality_checks_run_idx on public.quality_checks(run_id, verdict);
create index state_transitions_run_idx on public.state_transitions(run_id, state_version);
create index research_tasks_run_idx on public.research_tasks(run_id, status);
create index approvals_run_idx on public.approvals(run_id, decision);
create index errors_run_idx on public.errors(run_id, created_at desc);
create index dead_letter_status_idx on public.dead_letter_events(owner_id, resolution_status);
create index artifacts_run_idx on public.artifacts(run_id, version desc);
create index feedback_run_idx on public.feedback(run_id);

do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'projects', 'runs', 'hypotheses', 'evidence', 'competitors', 'agent_runs',
    'tool_calls', 'quality_checks', 'research_tasks', 'approvals', 'errors',
    'dead_letter_events', 'artifacts', 'feedback'
  ] loop
    execute format(
      'create trigger %I before update on public.%I for each row execute function public.set_updated_at()',
      table_name || '_set_updated_at', table_name
    );
  end loop;
end;
$$;

create or replace function public.reject_audit_mutation()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  raise exception 'AUDIT_ROW_IMMUTABLE' using errcode = '42501';
end;
$$;

create trigger state_transitions_immutable
before update or delete on public.state_transitions
for each row execute function public.reject_audit_mutation();

create trigger dead_letter_events_immutable
before update or delete on public.dead_letter_events
for each row execute function public.reject_audit_mutation();

create or replace function public.prevent_identity_change()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if new.id <> old.id or new.owner_id <> old.owner_id then
    raise exception 'IMMUTABLE_IDENTITY_FIELD' using errcode = '42501';
  end if;
  return new;
end;
$$;

create or replace function public.protect_run_state_fields()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if current_setting('blueprint.allow_state_transition', true) is distinct from 'on'
     and (
       new.status is distinct from old.status
       or new.current_route is distinct from old.current_route
       or new.current_node is distinct from old.current_node
       or new.state_version is distinct from old.state_version
       or new.transition_count is distinct from old.transition_count
       or new.search_cycle_count is distinct from old.search_cycle_count
       or new.tool_call_count is distinct from old.tool_call_count
       or new.revision_count is distinct from old.revision_count
       or new.cost_estimate_usd is distinct from old.cost_estimate_usd
     ) then
    raise exception 'USE_ADVANCE_RUN_STATE_RPC' using errcode = '42501';
  end if;
  return new;
end;
$$;

create or replace function public.protect_initial_run_state()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if new.status <> 'NEW'
     or new.current_route is not null
     or new.current_node is not null
     or new.state_version <> 0
     or new.transition_count <> 0
     or new.search_cycle_count <> 0
     or new.tool_call_count <> 0
     or new.revision_count <> 0
     or new.cost_estimate_usd <> 0
     or new.final_output is not null
     or new.final_artifact_id is not null then
    raise exception 'INVALID_INITIAL_RUN_STATE' using errcode = '22023';
  end if;
  return new;
end;
$$;

create trigger runs_protect_initial_state
before insert on public.runs
for each row execute function public.protect_initial_run_state();

create trigger runs_protect_state_fields
before update on public.runs
for each row execute function public.protect_run_state_fields();

do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'projects', 'runs', 'hypotheses', 'evidence', 'competitors', 'agent_runs',
    'tool_calls', 'quality_checks', 'research_tasks', 'approvals', 'errors',
    'artifacts', 'feedback'
  ] loop
    execute format(
      'create trigger %I before update on public.%I for each row execute function public.prevent_identity_change()',
      table_name || '_protect_identity', table_name
    );
  end loop;
end;
$$;

alter table public.projects enable row level security;
alter table public.runs enable row level security;
alter table public.hypotheses enable row level security;
alter table public.evidence enable row level security;
alter table public.competitors enable row level security;
alter table public.agent_runs enable row level security;
alter table public.tool_calls enable row level security;
alter table public.quality_checks enable row level security;
alter table public.state_transitions enable row level security;
alter table public.research_tasks enable row level security;
alter table public.approvals enable row level security;
alter table public.errors enable row level security;
alter table public.dead_letter_events enable row level security;
alter table public.artifacts enable row level security;
alter table public.feedback enable row level security;
alter table public.allowed_run_transitions enable row level security;

do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'projects', 'runs', 'hypotheses', 'evidence', 'competitors', 'agent_runs',
    'tool_calls', 'quality_checks', 'research_tasks', 'approvals', 'errors',
    'dead_letter_events', 'artifacts', 'feedback'
  ] loop
    execute format('create policy %I on public.%I for select to authenticated using ((select auth.uid()) = owner_id)', table_name || '_select_own', table_name);
    execute format('create policy %I on public.%I for insert to authenticated with check ((select auth.uid()) = owner_id)', table_name || '_insert_own', table_name);
  end loop;
end;
$$;

create policy state_transitions_select_own
on public.state_transitions for select to authenticated
using ((select auth.uid()) = owner_id);

create policy allowed_run_transitions_read
on public.allowed_run_transitions for select to authenticated
using (true);

do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'projects', 'runs', 'hypotheses', 'evidence', 'competitors', 'agent_runs',
    'tool_calls', 'quality_checks', 'research_tasks', 'approvals', 'errors',
    'artifacts', 'feedback'
  ] loop
    execute format('create policy %I on public.%I for update to authenticated using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id)', table_name || '_update_own', table_name);
  end loop;
end;
$$;

revoke all on public.allowed_run_transitions from anon, authenticated;
grant select on public.allowed_run_transitions to authenticated;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'blueprint-artifacts',
  'blueprint-artifacts',
  false,
  10485760,
  array['text/markdown', 'application/json', 'application/pdf']
)
on conflict (id) do update
set public = false,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

create policy blueprint_artifacts_select_own
on storage.objects for select to authenticated
using (
  bucket_id = 'blueprint-artifacts'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);

create policy blueprint_artifacts_insert_own
on storage.objects for insert to authenticated
with check (
  bucket_id = 'blueprint-artifacts'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);

create policy blueprint_artifacts_update_own
on storage.objects for update to authenticated
using (
  bucket_id = 'blueprint-artifacts'
  and (storage.foldername(name))[1] = (select auth.uid())::text
)
with check (
  bucket_id = 'blueprint-artifacts'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);

create policy blueprint_artifacts_delete_own
on storage.objects for delete to authenticated
using (
  bucket_id = 'blueprint-artifacts'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);

create or replace function public.advance_run_state(
  p_run_id uuid,
  p_expected_version integer,
  p_new_status text,
  p_route text default null,
  p_transition_record jsonb default '{}'::jsonb
)
returns public.runs
language plpgsql
security definer
set search_path = public
as $$
declare
  current_run public.runs%rowtype;
  updated_run public.runs%rowtype;
  search_delta integer := coalesce((p_transition_record ->> 'search_cycle_delta')::integer, 0);
  tool_delta integer := coalesce((p_transition_record ->> 'tool_call_delta')::integer, 0);
  revision_delta integer := coalesce((p_transition_record ->> 'revision_delta')::integer, 0);
  cost_delta numeric := coalesce((p_transition_record ->> 'cost_delta_usd')::numeric, 0);
  transition_actor text := coalesce(nullif(p_transition_record ->> 'actor', ''), 'SYSTEM');
  transition_reason text := coalesce(nullif(p_transition_record ->> 'reason_code', ''), 'UNSPECIFIED');
begin
  if auth.uid() is null then
    raise exception 'AUTH_REQUIRED' using errcode = '42501';
  end if;

  if p_new_status not in (
    'NEW', 'FRAMING', 'NEEDS_INPUT', 'PLANNING', 'RESEARCHING', 'AUDITING',
    'WAITING_APPROVAL', 'SYNTHESIZING', 'COMPLETED', 'PARTIAL',
    'HUMAN_REVIEW', 'SAFE_FAILED', 'CANCELLED'
  ) then
    raise exception 'INVALID_RUN_STATUS: %', p_new_status using errcode = '22023';
  end if;

  if transition_actor not in ('FOUNDER', 'SUPERVISOR', 'AGENT', 'AUDITOR', 'SYSTEM', 'ADMIN') then
    raise exception 'INVALID_TRANSITION_ACTOR' using errcode = '22023';
  end if;

  if least(search_delta, tool_delta, revision_delta) < 0 or cost_delta < 0 then
    raise exception 'NEGATIVE_COUNTER_DELTA' using errcode = '22023';
  end if;

  select * into current_run
  from public.runs
  where id = p_run_id and owner_id = auth.uid()
  for update;

  if not found then
    raise exception 'RUN_NOT_FOUND_OR_FORBIDDEN' using errcode = 'P0002';
  end if;

  if current_run.state_version <> p_expected_version then
    raise exception 'STALE_STATE_VERSION expected %, actual %', p_expected_version, current_run.state_version
      using errcode = '40001';
  end if;

  if current_run.status in ('COMPLETED', 'PARTIAL', 'SAFE_FAILED', 'CANCELLED') then
    raise exception 'TERMINAL_RUN_CANNOT_TRANSITION' using errcode = '22023';
  end if;

  if not exists (
    select 1 from public.allowed_run_transitions
    where from_status = current_run.status and to_status = p_new_status
  ) then
    raise exception 'DISALLOWED_TRANSITION: % -> %', current_run.status, p_new_status
      using errcode = '22023';
  end if;

  if current_run.deadline_at is not null and current_run.deadline_at <= now()
     and p_new_status not in ('PARTIAL', 'HUMAN_REVIEW', 'SAFE_FAILED', 'CANCELLED') then
    raise exception 'RUN_DEADLINE_EXCEEDED' using errcode = '57014';
  end if;

  if current_run.transition_count + 1 > 20
     or current_run.search_cycle_count + search_delta > 3
     or current_run.tool_call_count + tool_delta > 80
     or current_run.revision_count + revision_delta > 3 then
    raise exception 'RUN_BUDGET_EXCEEDED' using errcode = '54000';
  end if;

  perform set_config('blueprint.allow_state_transition', 'on', true);

  update public.runs
  set status = p_new_status,
      current_route = p_route,
      current_node = nullif(p_transition_record ->> 'current_node', ''),
      state_version = state_version + 1,
      transition_count = transition_count + 1,
      search_cycle_count = search_cycle_count + search_delta,
      tool_call_count = tool_call_count + tool_delta,
      revision_count = revision_count + revision_delta,
      cost_estimate_usd = cost_estimate_usd + cost_delta,
      updated_at = now()
  where id = current_run.id and state_version = p_expected_version
  returning * into updated_run;

  -- The bypass exists only for this one guarded UPDATE statement. Reset it
  -- immediately so later statements in the same transaction cannot mutate
  -- protected state fields directly.
  perform set_config('blueprint.allow_state_transition', 'off', true);

  if not found then
    raise exception 'CONCURRENT_STATE_UPDATE' using errcode = '40001';
  end if;

  insert into public.state_transitions (
    owner_id, project_id, run_id, from_status, to_status, route, actor,
    reason_code, detail, state_version, correlation_id
  ) values (
    current_run.owner_id,
    current_run.project_id,
    current_run.id,
    current_run.status,
    p_new_status,
    p_route,
    transition_actor,
    transition_reason,
    p_transition_record - array['actor', 'reason_code', 'search_cycle_delta', 'tool_call_delta', 'revision_delta', 'cost_delta_usd']::text[],
    updated_run.state_version,
    nullif(p_transition_record ->> 'correlation_id', '')
  );

  return updated_run;
end;
$$;

revoke all on function public.advance_run_state(uuid, integer, text, text, jsonb) from public, anon;
grant execute on function public.advance_run_state(uuid, integer, text, text, jsonb) to authenticated;

grant usage on schema public to authenticated;
grant select, insert, update on public.projects, public.runs, public.hypotheses,
  public.evidence, public.competitors, public.agent_runs, public.tool_calls,
  public.quality_checks, public.research_tasks, public.approvals, public.errors,
  public.artifacts, public.feedback to authenticated;
grant select on public.state_transitions to authenticated;
grant select, insert on public.dead_letter_events to authenticated;

commit;
