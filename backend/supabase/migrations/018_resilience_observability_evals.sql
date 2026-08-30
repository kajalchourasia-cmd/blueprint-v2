-- Blueprint Evidence Dev
-- Migration 018: caught-failure observability and durable evaluation summaries.

begin;

alter table public.errors drop constraint if exists errors_error_class_check;
alter table public.errors add constraint errors_error_class_check check (error_class in (
  'AUTH','VALIDATION','PROVIDER','RATE_LIMIT','TIMEOUT','EMPTY_RESULT','SCHEMA',
  'GROUNDING','QUALITY','CONFLICT','BUDGET','POLICY','INTERNAL','UNKNOWN'
));

create table if not exists public.eval_suite_runs (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid references public.projects(id) on delete restrict,
  suite_name text not null check (char_length(suite_name) between 3 and 120),
  suite_version text not null check (char_length(suite_version) between 1 and 80),
  status text not null check (status in ('RUNNING','PASSED','FAILED','PARTIAL')),
  total_cases integer not null default 0 check (total_cases >= 0),
  passed_cases integer not null default 0 check (passed_cases >= 0),
  failed_cases integer not null default 0 check (failed_cases >= 0),
  metrics jsonb not null default '{}'::jsonb check (jsonb_typeof(metrics)='object'),
  environment jsonb not null default '{}'::jsonb check (jsonb_typeof(environment)='object'),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  unique (id,owner_id),
  constraint eval_suite_runs_project_owner_fk foreign key (project_id,owner_id)
    references public.projects(id,owner_id) on delete restrict
);

create table if not exists public.eval_case_results (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  suite_run_id uuid not null references public.eval_suite_runs(id) on delete cascade,
  case_id text not null check (char_length(case_id) between 3 and 160),
  category text not null check (category in (
    'SCOPE','ROUTING','GROUNDING','HITL','MEMORY','RERUN','FAILURE','BUDGET',
    'SECURITY','STATE','QUALITY','COMPLETION'
  )),
  status text not null check (status in ('PASS','FAIL','SKIP')),
  expected jsonb not null default '{}'::jsonb check (jsonb_typeof(expected)='object'),
  actual jsonb not null default '{}'::jsonb check (jsonb_typeof(actual)='object'),
  assertions jsonb not null default '[]'::jsonb check (jsonb_typeof(assertions)='array'),
  duration_ms integer check (duration_ms is null or duration_ms >= 0),
  created_at timestamptz not null default now(),
  unique (suite_run_id,case_id),
  unique (id,owner_id),
  constraint eval_case_results_suite_owner_fk foreign key (suite_run_id,owner_id)
    references public.eval_suite_runs(id,owner_id) on delete cascade
);

alter table public.eval_suite_runs enable row level security;
alter table public.eval_case_results enable row level security;

drop policy if exists eval_suite_runs_select_own on public.eval_suite_runs;
create policy eval_suite_runs_select_own on public.eval_suite_runs for select to authenticated
  using ((select auth.uid())=owner_id);
drop policy if exists eval_suite_runs_insert_own on public.eval_suite_runs;
create policy eval_suite_runs_insert_own on public.eval_suite_runs for insert to authenticated
  with check ((select auth.uid())=owner_id);
drop policy if exists eval_suite_runs_update_own on public.eval_suite_runs;
create policy eval_suite_runs_update_own on public.eval_suite_runs for update to authenticated
  using ((select auth.uid())=owner_id) with check ((select auth.uid())=owner_id);
drop policy if exists eval_case_results_select_own on public.eval_case_results;
create policy eval_case_results_select_own on public.eval_case_results for select to authenticated
  using ((select auth.uid())=owner_id);
drop policy if exists eval_case_results_insert_own on public.eval_case_results;
create policy eval_case_results_insert_own on public.eval_case_results for insert to authenticated
  with check ((select auth.uid())=owner_id);

revoke all on public.eval_suite_runs,public.eval_case_results from anon;
grant select,insert,update on public.eval_suite_runs to authenticated;
grant select,insert on public.eval_case_results to authenticated;

create or replace function public.record_resilience_decision(
  p_run_id uuid,
  p_task_id uuid,
  p_error_class text,
  p_retryable boolean,
  p_attempt integer,
  p_provider text,
  p_component text,
  p_safe_message text,
  p_route text,
  p_correlation_id text,
  p_redacted_details jsonb default '{}'::jsonb,
  p_metrics jsonb default '{}'::jsonb
)
returns jsonb
language plpgsql
security definer
set search_path=public,auth
as $$
declare
  v_owner_id uuid := auth.uid();
  v_run public.runs;
  v_task public.orchestration_tasks;
  v_error public.errors;
  v_tool_call_id uuid;
  v_duration integer;
begin
  if v_owner_id is null then raise exception 'AUTHENTICATION_REQUIRED' using errcode='42501'; end if;
  if p_error_class not in (
    'AUTH','VALIDATION','PROVIDER','RATE_LIMIT','TIMEOUT','EMPTY_RESULT','SCHEMA',
    'GROUNDING','QUALITY','CONFLICT','BUDGET','POLICY','INTERNAL','UNKNOWN'
  ) then raise exception 'INVALID_ERROR_CLASS' using errcode='22023'; end if;
  if p_attempt is null or p_attempt < 0 or p_attempt > 5 then
    raise exception 'INVALID_ATTEMPT' using errcode='22023';
  end if;
  if jsonb_typeof(coalesce(p_redacted_details,'{}'::jsonb))<>'object'
     or jsonb_typeof(coalesce(p_metrics,'{}'::jsonb))<>'object' then
    raise exception 'DETAILS_AND_METRICS_MUST_BE_OBJECTS' using errcode='22023';
  end if;
  select * into v_run from public.runs where id=p_run_id and owner_id=v_owner_id;
  if not found then raise exception 'RUN_NOT_FOUND' using errcode='P0002'; end if;
  if p_task_id is not null then
    select * into v_task from public.orchestration_tasks
      where id=p_task_id and run_id=p_run_id and owner_id=v_owner_id;
    if not found then raise exception 'TASK_NOT_FOUND' using errcode='P0002'; end if;
  end if;

  insert into public.errors(
    owner_id,project_id,run_id,error_class,retryable,workflow_name,node_name,
    safe_message,redacted_technical_details,recovery_action,correlation_id
  ) values (
    v_owner_id,v_run.project_id,v_run.id,p_error_class,coalesce(p_retryable,false),
    left(coalesce(nullif(p_component,''),'BP-RESILIENCE-01'),300),
    case when p_task_id is null then null else left(v_task.task_key,300) end,
    left(coalesce(nullif(p_safe_message,''),'A workflow step failed safely.'),1000),
    coalesce(p_redacted_details,'{}'::jsonb),left(coalesce(p_route,'HUMAN_REVIEW'),1000),
    left(coalesce(nullif(p_correlation_id,''),'bp-resilience-'||gen_random_uuid()::text),300)
  ) returning * into v_error;

  if nullif(btrim(coalesce(p_provider,'')),'') is not null then
    v_duration := greatest(0,least(3600000,coalesce((p_metrics->>'duration_ms')::integer,0)));
    insert into public.tool_calls(
      owner_id,project_id,run_id,tool,provider,status,duration_ms,retry_count,
      provenance,redacted_error
    ) values (
      v_owner_id,v_run.project_id,v_run.id,
      left(coalesce(nullif(p_component,''),'UNKNOWN_TOOL'),200),left(p_provider,200),
      case when p_retryable and p_route='RETRY' then 'RETRYING' else 'FAILED' end,
      v_duration,least(p_attempt,5),
      jsonb_build_object('correlation_id',p_correlation_id,'route',p_route,'task_id',p_task_id),
      jsonb_build_object('error_id',v_error.id,'error_class',p_error_class)
    ) returning id into v_tool_call_id;
  end if;

  return jsonb_build_object(
    'recorded',true,'error_id',v_error.id,'tool_call_id',v_tool_call_id,
    'run_id',v_run.id,'project_id',v_run.project_id,'route',p_route
  );
end;
$$;

create or replace function public.get_run_observability(p_run_id uuid)
returns jsonb
language sql
stable
security invoker
set search_path=public,auth
as $$
  select jsonb_build_object(
    'run_id',r.id,'status',r.status,'current_route',r.current_route,
    'state_version',r.state_version,'transition_count',r.transition_count,
    'tool_call_count',r.tool_call_count,'revision_count',r.revision_count,
    'cost_estimate_usd',r.cost_estimate_usd,
    'task_counts',coalesce((select jsonb_object_agg(status,n) from (
      select status,count(*) n from public.orchestration_tasks
      where run_id=r.id and owner_id=auth.uid() group by status
    ) q),'{}'::jsonb),
    'error_counts',coalesce((select jsonb_object_agg(error_class,n) from (
      select error_class,count(*) n from public.errors
      where run_id=r.id and owner_id=auth.uid() group by error_class
    ) q),'{}'::jsonb),
    'tool_summary',coalesce((select jsonb_build_object(
      'calls',count(*),'failed',count(*) filter(where status='FAILED'),
      'retrying',count(*) filter(where status='RETRYING'),
      'average_duration_ms',round(avg(duration_ms))
    ) from public.tool_calls where run_id=r.id and owner_id=auth.uid()),'{}'::jsonb),
    'pending_checkpoints',coalesce((select jsonb_agg(jsonb_build_object(
      'id',id,'type',checkpoint_type,'available_decisions',available_decisions,'created_at',created_at
    ) order by created_at) from public.human_checkpoints
      where run_id=r.id and owner_id=auth.uid() and status='PENDING'),'[]'::jsonb),
    'terminal_visible',r.status in ('COMPLETED','PARTIAL','HUMAN_REVIEW','SAFE_FAILED','CANCELLED')
  )
  from public.runs r where r.id=p_run_id and r.owner_id=auth.uid();
$$;

revoke all on function public.record_resilience_decision(uuid,uuid,text,boolean,integer,text,text,text,text,text,jsonb,jsonb) from public,anon;
revoke all on function public.get_run_observability(uuid) from public,anon;
grant execute on function public.record_resilience_decision(uuid,uuid,text,boolean,integer,text,text,text,text,text,jsonb,jsonb) to authenticated;
grant execute on function public.get_run_observability(uuid) to authenticated;

commit;
