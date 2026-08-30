-- Blueprint Evidence Dev
-- Migration 007: adaptive Supervisor context, grounded chat, agent commands,
-- expanded agent/route vocabulary, and final quality-gate persistence.

begin;

alter table public.runs drop constraint if exists runs_current_route_check;
alter table public.runs add constraint runs_current_route_check check (
  current_route is null or current_route in (
    'IDEA_FRAME', 'RESEARCH_SUITE', 'CUSTOMER_DEMAND', 'COMPETITOR_INTELLIGENCE',
    'MARKET_ECONOMICS', 'FINANCIAL_SCENARIO', 'EVIDENCE_AUDIT',
    'EXPERIMENT_DESIGN', 'BLUEPRINT_SYNTHESIS', 'BLUEPRINT_QUALITY',
    'RESEARCH_COPILOT', 'MEMORY_INDEX', 'FOUNDER_INPUT', 'HUMAN_REVIEW',
    'PARTIAL_COMPLETE', 'SAFE_FAIL', 'COMPLETE', 'CANCEL'
  )
);

alter table public.agent_runs drop constraint if exists agent_runs_agent_check;
alter table public.agent_runs add constraint agent_runs_agent_check check (
  agent in (
    'SUPERVISOR', 'IDEA_FRAME', 'RESEARCH_PLANNER', 'PROVIDER_GATEWAY',
    'CUSTOMER_DEMAND', 'COMPETITOR_INTELLIGENCE', 'MARKET_ECONOMICS',
    'FINANCIAL_SCENARIO', 'EVIDENCE_AUDITOR', 'EXPERIMENT_DESIGNER',
    'VALIDATION_DISTRIBUTION', 'BLUEPRINT_SYNTHESIS', 'BLUEPRINT_CRITIC',
    'RESEARCH_COPILOT', 'MEMORY_INDEXER'
  )
);

alter table public.research_tasks drop constraint if exists research_tasks_task_type_check;
alter table public.research_tasks add constraint research_tasks_task_type_check check (
  task_type in ('SEARCH', 'FETCH', 'EXTRACT', 'VERIFY', 'CALCULATE', 'ANALYZE', 'SYNTHESIZE', 'INDEX', 'CHAT')
);

alter table public.research_tasks
  add column if not exists input jsonb not null default '{}'::jsonb check (jsonb_typeof(input) = 'object'),
  add column if not exists idempotency_key text,
  add column if not exists depends_on uuid[] not null default '{}'::uuid[],
  add column if not exists requested_by text not null default 'SUPERVISOR' check (requested_by in ('FOUNDER', 'SUPERVISOR', 'RESEARCH_COPILOT', 'SYSTEM'));

create unique index if not exists research_tasks_idempotency_idx
  on public.research_tasks(owner_id, run_id, idempotency_key)
  where idempotency_key is not null;

alter table public.approvals drop constraint if exists approvals_proposal_type_check;
alter table public.approvals add constraint approvals_proposal_type_check check (
  proposal_type in ('EXPERIMENT', 'SCOPE_CHANGE', 'FINAL_RECOMMENDATION', 'MODULE_RUN', 'MEMORY_DELETE', 'OTHER')
);

create table public.run_contexts (
  run_id uuid primary key references public.runs(id) on delete restrict,
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  schema_version text not null default 'bp-supervisor-state-v1',
  normalized_intent jsonb not null default '{}'::jsonb check (jsonb_typeof(normalized_intent) = 'object'),
  normalized_constraints jsonb not null default '{}'::jsonb check (jsonb_typeof(normalized_constraints) = 'object'),
  current_plan jsonb not null default '[]'::jsonb check (jsonb_typeof(current_plan) = 'array'),
  pending_actions jsonb not null default '[]'::jsonb check (jsonb_typeof(pending_actions) = 'array'),
  structured_outputs jsonb not null default '{}'::jsonb check (jsonb_typeof(structured_outputs) = 'object'),
  missing_information jsonb not null default '[]'::jsonb check (jsonb_typeof(missing_information) = 'array'),
  safety_flags jsonb not null default '[]'::jsonb check (jsonb_typeof(safety_flags) = 'array'),
  route_decision jsonb not null default '{}'::jsonb check (jsonb_typeof(route_decision) = 'object'),
  route_confidence numeric(5,4) not null default 0 check (route_confidence between 0 and 1),
  route_evidence jsonb not null default '[]'::jsonb check (jsonb_typeof(route_evidence) = 'array'),
  quality_summary jsonb not null default '{}'::jsonb check (jsonb_typeof(quality_summary) = 'object'),
  memory_version integer not null default 0 check (memory_version >= 0),
  retention_until timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (run_id, owner_id),
  constraint run_contexts_project_owner_fk foreign key (project_id, owner_id)
    references public.projects(id, owner_id) on delete restrict,
  constraint run_contexts_run_owner_fk foreign key (run_id, owner_id)
    references public.runs(id, owner_id) on delete restrict
);

create table public.chat_threads (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid references public.runs(id) on delete restrict,
  title text not null default 'Blueprint research conversation' check (char_length(title) between 1 and 200),
  status text not null default 'ACTIVE' check (status in ('ACTIVE', 'ARCHIVED')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (id, owner_id),
  constraint chat_threads_project_owner_fk foreign key (project_id, owner_id)
    references public.projects(id, owner_id) on delete restrict,
  constraint chat_threads_run_owner_fk foreign key (run_id, owner_id)
    references public.runs(id, owner_id) on delete restrict
);

create table public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid references public.runs(id) on delete restrict,
  thread_id uuid not null references public.chat_threads(id) on delete restrict,
  role text not null check (role in ('USER', 'ASSISTANT', 'SYSTEM_SUMMARY')),
  intent text not null check (intent in ('QUESTION', 'EXPLAIN_PHASE', 'NEXT_STEP', 'RUN_MODULE', 'CORRECTION', 'CANCEL', 'OUT_OF_SCOPE', 'AMBIGUOUS')),
  content text not null check (char_length(content) between 1 and 12000),
  citation_ids uuid[] not null default '{}'::uuid[],
  suggested_actions jsonb not null default '[]'::jsonb check (jsonb_typeof(suggested_actions) = 'array'),
  route_evidence jsonb not null default '[]'::jsonb check (jsonb_typeof(route_evidence) = 'array'),
  correlation_id text,
  created_at timestamptz not null default now(),
  unique (id, owner_id),
  constraint chat_messages_project_owner_fk foreign key (project_id, owner_id)
    references public.projects(id, owner_id) on delete restrict,
  constraint chat_messages_run_owner_fk foreign key (run_id, owner_id)
    references public.runs(id, owner_id) on delete restrict,
  constraint chat_messages_thread_owner_fk foreign key (thread_id, owner_id)
    references public.chat_threads(id, owner_id) on delete restrict
);

create table public.agent_commands (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid references public.runs(id) on delete restrict,
  thread_id uuid references public.chat_threads(id) on delete restrict,
  idempotency_key text not null check (char_length(idempotency_key) between 8 and 200),
  command_type text not null check (command_type in ('RUN_MODULE', 'ASK_QUESTION', 'REQUEST_REPAIR', 'CANCEL', 'DELETE_MEMORY')),
  target_module text check (target_module is null or target_module in ('foundation', 'customer_demand', 'competitor_intelligence', 'market_economics', 'financial_readiness', 'validation', 'launch_distribution', 'growth_optimization')),
  payload jsonb not null default '{}'::jsonb check (jsonb_typeof(payload) = 'object'),
  approval_required boolean not null default false,
  approval_id uuid references public.approvals(id) on delete restrict,
  status text not null default 'PENDING' check (status in ('PENDING', 'WAITING_APPROVAL', 'EXECUTING', 'SUCCEEDED', 'PARTIAL', 'FAILED', 'REJECTED', 'CANCELLED')),
  result jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (owner_id, idempotency_key),
  unique (id, owner_id),
  constraint agent_commands_project_owner_fk foreign key (project_id, owner_id)
    references public.projects(id, owner_id) on delete restrict,
  constraint agent_commands_run_owner_fk foreign key (run_id, owner_id)
    references public.runs(id, owner_id) on delete restrict,
  constraint agent_commands_thread_owner_fk foreign key (thread_id, owner_id)
    references public.chat_threads(id, owner_id) on delete restrict
);

create index run_contexts_owner_project_idx on public.run_contexts(owner_id, project_id);
create index chat_threads_owner_project_idx on public.chat_threads(owner_id, project_id, updated_at desc);
create index chat_messages_thread_idx on public.chat_messages(thread_id, created_at);
create index agent_commands_run_status_idx on public.agent_commands(run_id, status, created_at);

create trigger run_contexts_set_updated_at before update on public.run_contexts
for each row execute function public.set_updated_at();
create trigger chat_threads_set_updated_at before update on public.chat_threads
for each row execute function public.set_updated_at();
create trigger agent_commands_set_updated_at before update on public.agent_commands
for each row execute function public.set_updated_at();

create trigger run_contexts_protect_identity before update on public.run_contexts
for each row execute function public.prevent_identity_change();
create trigger chat_threads_protect_identity before update on public.chat_threads
for each row execute function public.prevent_identity_change();
create trigger chat_messages_protect_identity before update on public.chat_messages
for each row execute function public.prevent_identity_change();
create trigger agent_commands_protect_identity before update on public.agent_commands
for each row execute function public.prevent_identity_change();

alter table public.run_contexts enable row level security;
alter table public.chat_threads enable row level security;
alter table public.chat_messages enable row level security;
alter table public.agent_commands enable row level security;

create policy run_contexts_select_own on public.run_contexts for select to authenticated using ((select auth.uid()) = owner_id);
create policy run_contexts_insert_own on public.run_contexts for insert to authenticated with check ((select auth.uid()) = owner_id);
create policy run_contexts_update_own on public.run_contexts for update to authenticated using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id);
create policy chat_threads_select_own on public.chat_threads for select to authenticated using ((select auth.uid()) = owner_id);
create policy chat_threads_insert_own on public.chat_threads for insert to authenticated with check ((select auth.uid()) = owner_id);
create policy chat_threads_update_own on public.chat_threads for update to authenticated using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id);
create policy chat_messages_select_own on public.chat_messages for select to authenticated using ((select auth.uid()) = owner_id);
create policy chat_messages_insert_own on public.chat_messages for insert to authenticated with check ((select auth.uid()) = owner_id);
create policy agent_commands_select_own on public.agent_commands for select to authenticated using ((select auth.uid()) = owner_id);
create policy agent_commands_insert_own on public.agent_commands for insert to authenticated with check ((select auth.uid()) = owner_id);
create policy agent_commands_update_own on public.agent_commands for update to authenticated using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id);

create or replace function public.get_supervisor_context(p_run_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  result jsonb;
begin
  if auth.uid() is null then
    raise exception 'AUTH_REQUIRED' using errcode = '42501';
  end if;

  select jsonb_build_object(
    'run', to_jsonb(r),
    'project', to_jsonb(p),
    'context', coalesce(to_jsonb(rc), '{}'::jsonb),
    'sections', coalesce((select jsonb_agg(to_jsonb(bs) order by bs.section_key) from public.blueprint_sections bs where bs.run_id = r.id and bs.owner_id = auth.uid()), '[]'::jsonb),
    'accepted_evidence', coalesce((select jsonb_agg(to_jsonb(e) order by e.created_at desc) from public.evidence e where e.run_id = r.id and e.owner_id = auth.uid() and e.auditor_verdict in ('ACCEPT', 'ACCEPT_WITH_LIMITATION')), '[]'::jsonb),
    'quality_checks', coalesce((select jsonb_agg(to_jsonb(q) order by q.created_at desc) from public.quality_checks q where q.run_id = r.id and q.owner_id = auth.uid()), '[]'::jsonb),
    'approvals', coalesce((select jsonb_agg(to_jsonb(a) order by a.created_at desc) from public.approvals a where a.run_id = r.id and a.owner_id = auth.uid()), '[]'::jsonb),
    'errors', coalesce((select jsonb_agg(to_jsonb(er) order by er.created_at desc) from public.errors er where er.run_id = r.id and er.owner_id = auth.uid()), '[]'::jsonb),
    'commands', coalesce((select jsonb_agg(to_jsonb(ac) order by ac.created_at desc) from public.agent_commands ac where ac.run_id = r.id and ac.owner_id = auth.uid()), '[]'::jsonb),
    'transitions', coalesce((select jsonb_agg(to_jsonb(st) order by st.state_version) from public.state_transitions st where st.run_id = r.id and st.owner_id = auth.uid()), '[]'::jsonb)
  ) into result
  from public.runs r
  join public.projects p on p.id = r.project_id and p.owner_id = r.owner_id
  left join public.run_contexts rc on rc.run_id = r.id and rc.owner_id = r.owner_id
  where r.id = p_run_id and r.owner_id = auth.uid();

  if result is null then
    raise exception 'RUN_NOT_FOUND_OR_FORBIDDEN' using errcode = 'P0002';
  end if;
  return result;
end;
$$;

revoke all on function public.get_supervisor_context(uuid) from public, anon;
grant execute on function public.get_supervisor_context(uuid) to authenticated;

grant select, insert, update on public.run_contexts, public.chat_threads, public.agent_commands to authenticated;
grant select, insert on public.chat_messages to authenticated;

commit;
