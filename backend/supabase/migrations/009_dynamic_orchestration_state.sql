-- Blueprint Evidence Dev
-- Migration 009: durable dynamic-orchestration, versioning, HITL, rerun,
-- action, dashboard-signal, and external-memory projection state.

begin;

-- Extend existing controlled vocabularies without breaking the sequential baseline.
alter table public.runs drop constraint if exists runs_current_route_check;
alter table public.runs add constraint runs_current_route_check check (
  current_route is null or current_route in (
    'IDEA_FRAME', 'RESEARCH_SUITE', 'TASK_PLANNER', 'TASK_SCHEDULER',
    'FOUNDATION', 'CUSTOMER_DEMAND', 'COMPETITOR_INTELLIGENCE',
    'MARKET_ECONOMICS', 'OFFER_PRICING', 'ASSUMPTIONS_RISKS',
    'OPERATING_MODEL', 'FINANCIAL_SCENARIO', 'VALIDATION_PROOF',
    'EXPERIMENT_DESIGN', 'LAUNCH_DISTRIBUTION', 'GROWTH_OPTIMIZATION',
    'EVIDENCE_AUDIT', 'BLUEPRINT_SYNTHESIS', 'BLUEPRINT_QUALITY',
    'RESEARCH_COPILOT', 'MEMORY_RETRIEVE', 'MEMORY_INDEX', 'MEMORY_WRITE',
    'FOUNDER_INPUT', 'HUMAN_REVIEW', 'HITL_RESUME', 'RERUN_PLAN',
    'PARTIAL_COMPLETE', 'SAFE_FAIL', 'COMPLETE', 'CANCEL'
  )
);

alter table public.agent_runs drop constraint if exists agent_runs_agent_check;
alter table public.agent_runs add constraint agent_runs_agent_check check (
  agent in (
    'SUPERVISOR', 'TASK_PLANNER', 'TASK_SCHEDULER', 'IDEA_FRAME',
    'FOUNDATION', 'RESEARCH_PLANNER', 'PROVIDER_GATEWAY', 'CUSTOMER_DEMAND',
    'COMPETITOR_INTELLIGENCE', 'MARKET_ECONOMICS', 'OFFER_PRICING',
    'ASSUMPTIONS_RISKS', 'OPERATING_MODEL', 'FINANCIAL_SCENARIO',
    'EVIDENCE_AUDITOR', 'EXPERIMENT_DESIGNER', 'VALIDATION_PROOF',
    'VALIDATION_DISTRIBUTION', 'LAUNCH_DISTRIBUTION', 'GROWTH_OPTIMIZATION',
    'BLUEPRINT_SYNTHESIS', 'BLUEPRINT_CRITIC', 'RESEARCH_COPILOT',
    'MEMORY_RETRIEVER', 'MEMORY_INDEXER', 'FOUNDER_JOURNEY_MEMORY'
  )
);

alter table public.blueprint_sections drop constraint if exists blueprint_sections_section_key_check;
alter table public.blueprint_sections add constraint blueprint_sections_section_key_check check (
  section_key in (
    'foundation', 'customer_demand', 'competitor_intelligence', 'market_economics',
    'offer_pricing', 'assumptions_risks', 'operating_model', 'financial_readiness',
    'validation', 'validation_proof', 'launch_distribution',
    'growth_optimization', 'final_blueprint'
  )
);

alter table public.blueprint_sections drop constraint if exists blueprint_sections_status_check;
alter table public.blueprint_sections add constraint blueprint_sections_status_check check (
  status in (
    'NOT_REQUESTED', 'PLANNED', 'BLOCKED', 'READY', 'NEEDS_INPUT',
    'IN_PROGRESS', 'RUNNING', 'AGENT_DONE', 'HUMAN_REVIEW', 'COMPLETED',
    'PARTIAL', 'STALE', 'NOT_APPLICABLE', 'SAFE_FAILED', 'CANCELLED'
  )
);

alter table public.chat_messages drop constraint if exists chat_messages_intent_check;
alter table public.chat_messages add constraint chat_messages_intent_check check (
  intent in (
    'QUESTION', 'EXPLAIN_PHASE', 'NEXT_STEP', 'RUN_MODULE', 'SOURCE_TRACE',
    'COMPARE_VERSIONS', 'CORRECTION', 'CANCEL', 'OUT_OF_SCOPE', 'AMBIGUOUS'
  )
);

alter table public.agent_commands drop constraint if exists agent_commands_command_type_check;
alter table public.agent_commands add constraint agent_commands_command_type_check check (
  command_type in (
    'RUN_MODULE', 'RERUN_MODULE', 'RERUN_FULL', 'ASK_QUESTION',
    'REQUEST_REPAIR', 'UPDATE_PROFILE', 'RESPOND_CHECKPOINT',
    'UPDATE_MEMORY', 'CANCEL', 'DELETE_MEMORY'
  )
);

alter table public.agent_commands drop constraint if exists agent_commands_target_module_check;
alter table public.agent_commands add constraint agent_commands_target_module_check check (
  target_module is null or target_module in (
    'foundation', 'customer_demand', 'competitor_intelligence', 'market_economics',
    'offer_pricing', 'assumptions_risks', 'operating_model', 'financial_readiness',
    'validation', 'validation_proof', 'launch_distribution',
    'growth_optimization', 'final_blueprint'
  )
);

alter table public.approvals drop constraint if exists approvals_proposal_type_check;
alter table public.approvals add constraint approvals_proposal_type_check check (
  proposal_type in (
    'EXPERIMENT', 'SCOPE_CHANGE', 'FINAL_RECOMMENDATION', 'MODULE_RUN',
    'RERUN', 'PROFILE_CHANGE', 'MEMORY_UPDATE', 'MEMORY_DELETE',
    'GO_NO_GO', 'OTHER'
  )
);

alter table public.approvals drop constraint if exists approvals_decision_check;
alter table public.approvals add constraint approvals_decision_check check (
  decision in (
    'PENDING', 'APPROVE', 'REJECT', 'EDIT', 'REQUEST_CHANGES',
    'MORE_INFORMATION', 'RETRY', 'ESCALATE', 'OVERRIDE', 'CANCEL', 'EXPIRED'
  )
);

alter table public.approvals drop constraint if exists approvals_id_owner_unique;
alter table public.approvals add constraint approvals_id_owner_unique unique (id, owner_id);

-- Immutable founder truth versions. Editing creates a new row.
create table public.project_profiles (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  version integer not null check (version > 0),
  payload jsonb not null check (jsonb_typeof(payload) = 'object'),
  changed_fields text[] not null default '{}'::text[],
  change_reason text,
  source_run_id uuid references public.runs(id) on delete restrict,
  created_by text not null default 'FOUNDER' check (created_by in ('FOUNDER', 'SYSTEM')),
  created_at timestamptz not null default now(),
  unique (project_id, version),
  unique (id, owner_id),
  constraint project_profiles_project_owner_fk foreign key (project_id, owner_id)
    references public.projects(id, owner_id) on delete restrict,
  constraint project_profiles_run_owner_fk foreign key (source_run_id, owner_id)
    references public.runs(id, owner_id) on delete restrict
);

create table public.blueprint_versions (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid not null references public.runs(id) on delete restrict,
  profile_version integer not null check (profile_version > 0),
  version integer not null check (version > 0),
  status text not null check (status in ('COMPLETED', 'PARTIAL', 'HUMAN_REVIEW', 'SAFE_FAILED')),
  blueprint jsonb not null check (jsonb_typeof(blueprint) = 'object'),
  quality_summary jsonb not null default '{}'::jsonb check (jsonb_typeof(quality_summary) = 'object'),
  checksum text,
  supersedes_id uuid references public.blueprint_versions(id) on delete restrict,
  created_at timestamptz not null default now(),
  unique (project_id, version),
  unique (id, owner_id),
  constraint blueprint_versions_project_owner_fk foreign key (project_id, owner_id)
    references public.projects(id, owner_id) on delete restrict,
  constraint blueprint_versions_run_owner_fk foreign key (run_id, owner_id)
    references public.runs(id, owner_id) on delete restrict,
  constraint blueprint_versions_supersedes_owner_fk foreign key (supersedes_id, owner_id)
    references public.blueprint_versions(id, owner_id) on delete restrict
);

-- One durable row per dynamic task in a run.
create table public.orchestration_tasks (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid not null references public.runs(id) on delete restrict,
  task_key text not null check (char_length(task_key) between 1 and 120),
  profile_version integer not null check (profile_version > 0),
  module_key text not null check (module_key in (
    'foundation', 'customer_demand', 'competitor_intelligence', 'market_economics',
    'offer_pricing', 'assumptions_risks', 'operating_model', 'financial_readiness',
    'validation_proof', 'launch_distribution', 'growth_optimization',
    'evidence_audit', 'final_blueprint'
  )),
  goal text not null check (char_length(goal) between 1 and 2000),
  plan_decision text not null default 'RUN' check (plan_decision in (
    'RUN', 'REUSE', 'WAIT', 'BLOCKED', 'NOT_APPLICABLE', 'NOT_REQUESTED'
  )),
  status text not null default 'PLANNED' check (status in (
    'PLANNED', 'BLOCKED', 'READY', 'RUNNING', 'NEEDS_INPUT', 'HUMAN_REVIEW',
    'COMPLETED', 'REUSED', 'PARTIAL', 'STALE', 'NOT_APPLICABLE',
    'SAFE_FAILED', 'CANCELLED'
  )),
  dependency_keys text[] not null default '{}'::text[],
  input_refs jsonb not null default '[]'::jsonb check (jsonb_typeof(input_refs) = 'array'),
  output_schema_version text not null default 'bp-task-output-v1',
  allowed_tools text[] not null default '{}'::text[],
  model_role text not null default 'STRONG' check (model_role in ('NONE', 'FAST', 'STRONG', 'AUDIT')),
  budgets jsonb not null default '{}'::jsonb check (jsonb_typeof(budgets) = 'object'),
  completion_criteria jsonb not null default '[]'::jsonb check (jsonb_typeof(completion_criteria) = 'array'),
  attempt_count integer not null default 0 check (attempt_count >= 0),
  repair_count integer not null default 0 check (repair_count >= 0),
  observation_verdict text check (observation_verdict is null or observation_verdict in (
    'VALID', 'NEEDS_REPAIR', 'NEEDS_INPUT', 'CONTRADICTORY', 'TOOL_FAILED',
    'NOT_APPLICABLE', 'POLICY_DENIED', 'BUDGET_EXHAUSTED'
  )),
  route_reason text,
  output jsonb check (output is null or jsonb_typeof(output) = 'object'),
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (run_id, task_key),
  unique (id, owner_id),
  constraint orchestration_tasks_project_owner_fk foreign key (project_id, owner_id)
    references public.projects(id, owner_id) on delete restrict,
  constraint orchestration_tasks_run_owner_fk foreign key (run_id, owner_id)
    references public.runs(id, owner_id) on delete restrict
);

create table public.task_observations (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid not null references public.runs(id) on delete restrict,
  task_id uuid not null references public.orchestration_tasks(id) on delete restrict,
  verdict text not null check (verdict in (
    'VALID', 'NEEDS_REPAIR', 'NEEDS_INPUT', 'CONTRADICTORY', 'TOOL_FAILED',
    'NOT_APPLICABLE', 'POLICY_DENIED', 'BUDGET_EXHAUSTED'
  )),
  summary text not null check (char_length(summary) between 1 and 4000),
  evidence_ids uuid[] not null default '{}'::uuid[],
  limitations jsonb not null default '[]'::jsonb check (jsonb_typeof(limitations) = 'array'),
  retryable boolean not null default false,
  proposed_route text,
  output_hash text,
  created_at timestamptz not null default now(),
  unique (id, owner_id),
  constraint task_observations_project_owner_fk foreign key (project_id, owner_id)
    references public.projects(id, owner_id) on delete restrict,
  constraint task_observations_run_owner_fk foreign key (run_id, owner_id)
    references public.runs(id, owner_id) on delete restrict,
  constraint task_observations_task_owner_fk foreign key (task_id, owner_id)
    references public.orchestration_tasks(id, owner_id) on delete restrict
);

create table public.human_checkpoints (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid not null references public.runs(id) on delete restrict,
  task_id uuid references public.orchestration_tasks(id) on delete restrict,
  checkpoint_type text not null check (checkpoint_type in (
    'CLARIFICATION', 'CONTRADICTION', 'REPAIR_EXHAUSTED', 'PROFILE_CHANGE',
    'RERUN', 'EXPERIMENT', 'FINAL_DECISION', 'MEMORY', 'EXTERNAL_ACTION'
  )),
  status text not null default 'PENDING' check (status in ('PENDING', 'RESOLVED', 'EXPIRED', 'CANCELLED')),
  proposal_hash text not null,
  state_version integer not null check (state_version > 0),
  profile_version integer not null check (profile_version > 0),
  blueprint_version integer check (blueprint_version is null or blueprint_version > 0),
  payload jsonb not null default '{}'::jsonb check (jsonb_typeof(payload) = 'object'),
  available_decisions text[] not null default '{}'::text[],
  decision text check (decision is null or decision in (
    'APPROVE', 'REJECT', 'EDIT', 'REQUEST_CHANGES', 'MORE_INFORMATION',
    'RETRY', 'ESCALATE', 'OVERRIDE', 'CANCEL'
  )),
  decision_payload jsonb check (decision_payload is null or jsonb_typeof(decision_payload) = 'object'),
  expires_at timestamptz,
  resolved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (run_id, proposal_hash),
  unique (id, owner_id),
  constraint human_checkpoints_project_owner_fk foreign key (project_id, owner_id)
    references public.projects(id, owner_id) on delete restrict,
  constraint human_checkpoints_run_owner_fk foreign key (run_id, owner_id)
    references public.runs(id, owner_id) on delete restrict,
  constraint human_checkpoints_task_owner_fk foreign key (task_id, owner_id)
    references public.orchestration_tasks(id, owner_id) on delete restrict
);

create table public.next_actions (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid not null references public.runs(id) on delete restrict,
  blueprint_version integer,
  action_key text not null check (char_length(action_key) between 1 and 120),
  module_key text not null,
  title text not null check (char_length(title) between 1 and 300),
  why text not null check (char_length(why) between 1 and 2000),
  owner_type text not null default 'FOUNDER' check (owner_type in ('FOUNDER', 'SYSTEM')),
  priority integer not null check (priority between 1 and 100),
  effort text not null check (effort in ('LOW', 'MEDIUM', 'HIGH')),
  horizon text not null check (horizon in ('NOW', 'NEXT', 'LATER')),
  prerequisite_keys text[] not null default '{}'::text[],
  success_metric text not null,
  evidence_ids uuid[] not null default '{}'::uuid[],
  status text not null default 'OPEN' check (status in ('OPEN', 'IN_PROGRESS', 'DONE', 'BLOCKED', 'DISMISSED')),
  can_agent_run boolean not null default false,
  approval_required boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (run_id, action_key),
  unique (id, owner_id),
  constraint next_actions_project_owner_fk foreign key (project_id, owner_id)
    references public.projects(id, owner_id) on delete restrict,
  constraint next_actions_run_owner_fk foreign key (run_id, owner_id)
    references public.runs(id, owner_id) on delete restrict
);

create table public.dashboard_signals (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid not null references public.runs(id) on delete restrict,
  blueprint_version integer,
  signal_key text not null check (char_length(signal_key) between 1 and 120),
  label text not null check (char_length(label) between 1 and 120),
  value jsonb not null,
  unit text,
  value_status text not null check (value_status in ('MEASURED', 'DERIVED', 'ESTIMATED', 'UNKNOWN')),
  confidence numeric(5,4) not null check (confidence between 0 and 1),
  rule_id text not null,
  formula_description text not null,
  evidence_ids uuid[] not null default '{}'::uuid[],
  selection_reason text not null,
  next_action_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (run_id, signal_key),
  unique (id, owner_id),
  constraint dashboard_signals_project_owner_fk foreign key (project_id, owner_id)
    references public.projects(id, owner_id) on delete restrict,
  constraint dashboard_signals_run_owner_fk foreign key (run_id, owner_id)
    references public.runs(id, owner_id) on delete restrict,
  constraint dashboard_signals_action_owner_fk foreign key (next_action_id, owner_id)
    references public.next_actions(id, owner_id) on delete set null
);

create table public.rerun_requests (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  source_run_id uuid not null references public.runs(id) on delete restrict,
  target_run_id uuid references public.runs(id) on delete restrict,
  source_profile_version integer not null check (source_profile_version > 0),
  target_profile_version integer not null check (target_profile_version > 0),
  mode text not null check (mode in ('TARGETED', 'FULL')),
  requested_modules text[] not null default '{}'::text[],
  impact jsonb not null default '{}'::jsonb check (jsonb_typeof(impact) = 'object'),
  idempotency_key text not null check (char_length(idempotency_key) between 8 and 200),
  status text not null default 'PREVIEW' check (status in (
    'PREVIEW', 'WAITING_CONFIRMATION', 'APPROVED', 'EXECUTING', 'COMPLETED',
    'PARTIAL', 'REJECTED', 'CANCELLED', 'FAILED'
  )),
  approval_id uuid,
  checkpoint_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (owner_id, idempotency_key),
  unique (id, owner_id),
  constraint rerun_requests_project_owner_fk foreign key (project_id, owner_id)
    references public.projects(id, owner_id) on delete restrict,
  constraint rerun_requests_source_run_owner_fk foreign key (source_run_id, owner_id)
    references public.runs(id, owner_id) on delete restrict,
  constraint rerun_requests_target_run_owner_fk foreign key (target_run_id, owner_id)
    references public.runs(id, owner_id) on delete restrict,
  constraint rerun_requests_approval_owner_fk foreign key (approval_id, owner_id)
    references public.approvals(id, owner_id) on delete restrict,
  constraint rerun_requests_checkpoint_owner_fk foreign key (checkpoint_id, owner_id)
    references public.human_checkpoints(id, owner_id) on delete restrict
);

create table public.memory_projections (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid references public.runs(id) on delete restrict,
  provider text not null check (provider in ('PINECONE', 'MEM0')),
  external_id text not null,
  memory_type text not null check (memory_type in (
    'EVIDENCE', 'SECTION', 'ACTION', 'GOAL', 'PREFERENCE', 'CONSTRAINT',
    'CONFIRMED_DECISION', 'CORRECTION', 'LESSON', 'EPISODE_SUMMARY'
  )),
  profile_version integer,
  blueprint_version integer,
  content_hash text not null,
  source_event_ids text[] not null default '{}'::text[],
  status text not null default 'PENDING' check (status in (
    'PENDING', 'ACTIVE', 'SUPERSEDED', 'DELETED', 'FAILED'
  )),
  metadata jsonb not null default '{}'::jsonb check (jsonb_typeof(metadata) = 'object'),
  synced_at timestamptz,
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (owner_id, provider, external_id),
  unique (id, owner_id),
  constraint memory_projections_project_owner_fk foreign key (project_id, owner_id)
    references public.projects(id, owner_id) on delete restrict,
  constraint memory_projections_run_owner_fk foreign key (run_id, owner_id)
    references public.runs(id, owner_id) on delete restrict
);

-- Indexes used by the scheduler, resume endpoints, and dashboard.
create index project_profiles_latest_idx on public.project_profiles(project_id, version desc);
create index blueprint_versions_latest_idx on public.blueprint_versions(project_id, version desc);
create index orchestration_tasks_ready_idx on public.orchestration_tasks(run_id, status, module_key);
create index task_observations_task_idx on public.task_observations(task_id, created_at desc);
create index human_checkpoints_pending_idx on public.human_checkpoints(run_id, status, created_at);
create index next_actions_project_idx on public.next_actions(project_id, status, priority);
create index dashboard_signals_project_idx on public.dashboard_signals(project_id, updated_at desc);
create index rerun_requests_project_idx on public.rerun_requests(project_id, status, created_at desc);
create index memory_projections_lookup_idx on public.memory_projections(project_id, provider, memory_type, status);

-- Mutable rows get timestamp and immutable-identity protection.
create trigger orchestration_tasks_set_updated_at before update on public.orchestration_tasks
for each row execute function public.set_updated_at();
create trigger human_checkpoints_set_updated_at before update on public.human_checkpoints
for each row execute function public.set_updated_at();
create trigger next_actions_set_updated_at before update on public.next_actions
for each row execute function public.set_updated_at();
create trigger dashboard_signals_set_updated_at before update on public.dashboard_signals
for each row execute function public.set_updated_at();
create trigger rerun_requests_set_updated_at before update on public.rerun_requests
for each row execute function public.set_updated_at();
create trigger memory_projections_set_updated_at before update on public.memory_projections
for each row execute function public.set_updated_at();

create trigger orchestration_tasks_protect_identity before update on public.orchestration_tasks
for each row execute function public.prevent_identity_change();
create trigger human_checkpoints_protect_identity before update on public.human_checkpoints
for each row execute function public.prevent_identity_change();
create trigger next_actions_protect_identity before update on public.next_actions
for each row execute function public.prevent_identity_change();
create trigger dashboard_signals_protect_identity before update on public.dashboard_signals
for each row execute function public.prevent_identity_change();
create trigger rerun_requests_protect_identity before update on public.rerun_requests
for each row execute function public.prevent_identity_change();
create trigger memory_projections_protect_identity before update on public.memory_projections
for each row execute function public.prevent_identity_change();

-- Version rows are append-only, including for privileged application paths.
create trigger project_profiles_immutable before update or delete on public.project_profiles
for each row execute function public.reject_audit_mutation();
create trigger blueprint_versions_immutable before update or delete on public.blueprint_versions
for each row execute function public.reject_audit_mutation();
create trigger task_observations_immutable before update or delete on public.task_observations
for each row execute function public.reject_audit_mutation();

-- Owner-isolated RLS. Canonical versions and observations intentionally have no update/delete policy.
alter table public.project_profiles enable row level security;
alter table public.blueprint_versions enable row level security;
alter table public.orchestration_tasks enable row level security;
alter table public.task_observations enable row level security;
alter table public.human_checkpoints enable row level security;
alter table public.next_actions enable row level security;
alter table public.dashboard_signals enable row level security;
alter table public.rerun_requests enable row level security;
alter table public.memory_projections enable row level security;

create policy project_profiles_select_own on public.project_profiles for select to authenticated using ((select auth.uid()) = owner_id);
create policy project_profiles_insert_own on public.project_profiles for insert to authenticated with check ((select auth.uid()) = owner_id);
create policy blueprint_versions_select_own on public.blueprint_versions for select to authenticated using ((select auth.uid()) = owner_id);
create policy blueprint_versions_insert_own on public.blueprint_versions for insert to authenticated with check ((select auth.uid()) = owner_id);
create policy orchestration_tasks_select_own on public.orchestration_tasks for select to authenticated using ((select auth.uid()) = owner_id);
create policy orchestration_tasks_insert_own on public.orchestration_tasks for insert to authenticated with check ((select auth.uid()) = owner_id);
create policy orchestration_tasks_update_own on public.orchestration_tasks for update to authenticated using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id);
create policy task_observations_select_own on public.task_observations for select to authenticated using ((select auth.uid()) = owner_id);
create policy task_observations_insert_own on public.task_observations for insert to authenticated with check ((select auth.uid()) = owner_id);
create policy human_checkpoints_select_own on public.human_checkpoints for select to authenticated using ((select auth.uid()) = owner_id);
create policy human_checkpoints_insert_own on public.human_checkpoints for insert to authenticated with check ((select auth.uid()) = owner_id);
create policy human_checkpoints_update_own on public.human_checkpoints for update to authenticated using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id);
create policy next_actions_select_own on public.next_actions for select to authenticated using ((select auth.uid()) = owner_id);
create policy next_actions_insert_own on public.next_actions for insert to authenticated with check ((select auth.uid()) = owner_id);
create policy next_actions_update_own on public.next_actions for update to authenticated using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id);
create policy dashboard_signals_select_own on public.dashboard_signals for select to authenticated using ((select auth.uid()) = owner_id);
create policy dashboard_signals_insert_own on public.dashboard_signals for insert to authenticated with check ((select auth.uid()) = owner_id);
create policy dashboard_signals_update_own on public.dashboard_signals for update to authenticated using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id);
create policy rerun_requests_select_own on public.rerun_requests for select to authenticated using ((select auth.uid()) = owner_id);
create policy rerun_requests_insert_own on public.rerun_requests for insert to authenticated with check ((select auth.uid()) = owner_id);
create policy rerun_requests_update_own on public.rerun_requests for update to authenticated using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id);
create policy memory_projections_select_own on public.memory_projections for select to authenticated using ((select auth.uid()) = owner_id);
create policy memory_projections_insert_own on public.memory_projections for insert to authenticated with check ((select auth.uid()) = owner_id);
create policy memory_projections_update_own on public.memory_projections for update to authenticated using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id);

revoke all on public.project_profiles, public.blueprint_versions, public.orchestration_tasks,
  public.task_observations, public.human_checkpoints, public.next_actions,
  public.dashboard_signals, public.rerun_requests, public.memory_projections from anon;
grant select, insert on public.project_profiles, public.blueprint_versions, public.task_observations to authenticated;
grant select, insert, update on public.orchestration_tasks, public.human_checkpoints,
  public.next_actions, public.dashboard_signals, public.rerun_requests,
  public.memory_projections to authenticated;

-- Safe version allocator: serializes profile edits per project and verifies ownership.
create or replace function public.create_project_profile_version(
  p_project_id uuid,
  p_payload jsonb,
  p_changed_fields text[] default '{}'::text[],
  p_change_reason text default null,
  p_source_run_id uuid default null
)
returns public.project_profiles
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_owner_id uuid := auth.uid();
  v_version integer;
  v_row public.project_profiles;
begin
  if v_owner_id is null then
    raise exception 'AUTHENTICATION_REQUIRED' using errcode = '42501';
  end if;
  if p_payload is null or jsonb_typeof(p_payload) <> 'object' then
    raise exception 'PROFILE_PAYLOAD_MUST_BE_OBJECT' using errcode = '22023';
  end if;

  perform 1 from public.projects
  where id = p_project_id and owner_id = v_owner_id
  for update;
  if not found then
    raise exception 'PROJECT_NOT_FOUND' using errcode = 'P0002';
  end if;

  if p_source_run_id is not null and not exists (
    select 1 from public.runs where id = p_source_run_id
      and project_id = p_project_id and owner_id = v_owner_id
  ) then
    raise exception 'SOURCE_RUN_NOT_FOUND' using errcode = 'P0002';
  end if;

  select coalesce(max(version), 0) + 1 into v_version
  from public.project_profiles
  where project_id = p_project_id and owner_id = v_owner_id;

  insert into public.project_profiles (
    owner_id, project_id, version, payload, changed_fields,
    change_reason, source_run_id, created_by
  ) values (
    v_owner_id, p_project_id, v_version, p_payload,
    coalesce(p_changed_fields, '{}'::text[]), p_change_reason,
    p_source_run_id, 'FOUNDER'
  ) returning * into v_row;

  return v_row;
end;
$$;

revoke all on function public.create_project_profile_version(uuid, jsonb, text[], text, uuid) from public, anon;
grant execute on function public.create_project_profile_version(uuid, jsonb, text[], text, uuid) to authenticated;

-- One owner-scoped read for Streamlit and the Supervisor resume path.
create or replace function public.get_dynamic_blueprint_state(p_project_id uuid)
returns jsonb
language sql
stable
security invoker
set search_path = public, auth
as $$
  with owned_project as (
    select p.* from public.projects p
    where p.id = p_project_id and p.owner_id = auth.uid()
  ), latest_profile as (
    select pp.* from public.project_profiles pp
    where pp.project_id = p_project_id and pp.owner_id = auth.uid()
    order by pp.version desc limit 1
  ), latest_run as (
    select r.* from public.runs r
    where r.project_id = p_project_id and r.owner_id = auth.uid()
    order by r.created_at desc limit 1
  ), latest_blueprint as (
    select bv.* from public.blueprint_versions bv
    where bv.project_id = p_project_id and bv.owner_id = auth.uid()
    order by bv.version desc limit 1
  )
  select jsonb_build_object(
    'project', to_jsonb(p),
    'profile', (select to_jsonb(lp) from latest_profile lp),
    'run', (select to_jsonb(lr) from latest_run lr),
    'blueprint', (select to_jsonb(lb) from latest_blueprint lb),
    'tasks', coalesce((select jsonb_agg(to_jsonb(t) order by t.created_at)
      from public.orchestration_tasks t join latest_run lr on lr.id=t.run_id
      where t.owner_id=auth.uid()), '[]'::jsonb),
    'sections', coalesce((select jsonb_agg(to_jsonb(s) order by s.created_at)
      from public.blueprint_sections s join latest_run lr on lr.id=s.run_id
      where s.owner_id=auth.uid()), '[]'::jsonb),
    'pending_checkpoints', coalesce((select jsonb_agg(to_jsonb(h) order by h.created_at)
      from public.human_checkpoints h join latest_run lr on lr.id=h.run_id
      where h.owner_id=auth.uid() and h.status='PENDING'), '[]'::jsonb),
    'actions', coalesce((select jsonb_agg(to_jsonb(a) order by a.priority, a.created_at)
      from public.next_actions a where a.project_id=p_project_id and a.owner_id=auth.uid()), '[]'::jsonb),
    'signals', coalesce((select jsonb_agg(to_jsonb(ds) order by ds.updated_at desc)
      from public.dashboard_signals ds where ds.project_id=p_project_id and ds.owner_id=auth.uid()), '[]'::jsonb)
  )
  from owned_project p;
$$;

revoke all on function public.get_dynamic_blueprint_state(uuid) from public, anon;
grant execute on function public.get_dynamic_blueprint_state(uuid) to authenticated;

commit;
