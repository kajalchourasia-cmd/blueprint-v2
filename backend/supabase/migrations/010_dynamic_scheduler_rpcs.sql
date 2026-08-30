-- Blueprint Evidence Dev
-- Migration 010: atomic task-plan persistence, ready-task claiming,
-- observation recording, and dependency unlocking for Phase 6B.

begin;

create or replace function public.persist_dynamic_task_plan(
  p_run_id uuid,
  p_profile_version integer,
  p_tasks jsonb,
  p_route_reason text default 'SUPERVISOR_PLAN'
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_owner_id uuid := auth.uid();
  v_project_id uuid;
  v_task jsonb;
  v_task_key text;
  v_module_key text;
  v_plan_decision text;
  v_dependency_keys text[];
  v_allowed_tools text[];
  v_status text;
  v_keys text[];
begin
  if v_owner_id is null then
    raise exception 'AUTHENTICATION_REQUIRED' using errcode = '42501';
  end if;
  if p_profile_version is null or p_profile_version < 1 then
    raise exception 'PROFILE_VERSION_INVALID' using errcode = '22023';
  end if;
  if p_tasks is null or jsonb_typeof(p_tasks) <> 'array'
     or jsonb_array_length(p_tasks) < 1 or jsonb_array_length(p_tasks) > 20 then
    raise exception 'TASK_PLAN_MUST_HAVE_1_TO_20_TASKS' using errcode = '22023';
  end if;

  select r.project_id into v_project_id
  from public.runs r
  where r.id=p_run_id and r.owner_id=v_owner_id
  for update;
  if v_project_id is null then
    raise exception 'RUN_NOT_FOUND' using errcode = 'P0002';
  end if;

  if not exists (
    select 1 from public.project_profiles pp
    where pp.project_id=v_project_id and pp.owner_id=v_owner_id
      and pp.version=p_profile_version
  ) then
    raise exception 'PROFILE_VERSION_NOT_FOUND' using errcode = 'P0002';
  end if;

  if exists (select 1 from jsonb_array_elements(p_tasks) x where jsonb_typeof(x) <> 'object') then
    raise exception 'TASK_PLAN_ITEMS_MUST_BE_OBJECTS' using errcode = '22023';
  end if;

  select array_agg(x->>'task_key' order by x->>'task_key') into v_keys
  from jsonb_array_elements(p_tasks) x;

  if array_position(v_keys, null) is not null
     or exists (select 1 from unnest(v_keys) k where char_length(k) not between 1 and 120)
     or cardinality(v_keys) <> (select count(distinct k) from unnest(v_keys) k) then
    raise exception 'TASK_KEYS_MUST_BE_UNIQUE_AND_VALID' using errcode = '22023';
  end if;

  if exists (
    select 1
    from jsonb_array_elements(p_tasks) t
    cross join lateral jsonb_array_elements_text(coalesce(t->'dependency_keys', '[]'::jsonb)) d
    where not (d.value = any(v_keys)) or d.value = t->>'task_key'
  ) then
    raise exception 'TASK_DEPENDENCY_UNKNOWN_OR_SELF_REFERENTIAL' using errcode = '22023';
  end if;

  if exists (
    with recursive edges(task_key, dep_key) as (
      select t->>'task_key', d.value
      from jsonb_array_elements(p_tasks) t
      cross join lateral jsonb_array_elements_text(coalesce(t->'dependency_keys', '[]'::jsonb)) d
    ), walk(start_key, node_key, path, cycle) as (
      select e.task_key, e.dep_key, array[e.task_key, e.dep_key], e.dep_key=e.task_key
      from edges e
      union all
      select w.start_key, e.dep_key, w.path || e.dep_key, e.dep_key=any(w.path)
      from walk w
      join edges e on e.task_key=w.node_key
      where not w.cycle
    )
    select 1 from walk where cycle limit 1
  ) then
    raise exception 'TASK_PLAN_CONTAINS_CYCLE' using errcode = '22023';
  end if;

  -- A replan cancels obsolete nonterminal tasks but preserves completed history.
  update public.orchestration_tasks ot
  set status='CANCELLED', route_reason='REMOVED_BY_REPLAN'
  where ot.run_id=p_run_id and ot.owner_id=v_owner_id
    and not (ot.task_key = any(v_keys))
    and ot.status in ('PLANNED','BLOCKED','READY','NEEDS_INPUT','HUMAN_REVIEW','STALE');

  for v_task in select value from jsonb_array_elements(p_tasks)
  loop
    v_task_key := v_task->>'task_key';
    v_module_key := v_task->>'module_key';
    v_plan_decision := coalesce(v_task->>'plan_decision', 'RUN');
    select coalesce(array_agg(value), '{}'::text[]) into v_dependency_keys
      from jsonb_array_elements_text(coalesce(v_task->'dependency_keys', '[]'::jsonb));
    select coalesce(array_agg(value), '{}'::text[]) into v_allowed_tools
      from jsonb_array_elements_text(coalesce(v_task->'allowed_tools', '[]'::jsonb));

    v_status := case
      when v_plan_decision='NOT_APPLICABLE' then 'NOT_APPLICABLE'
      when v_plan_decision='NOT_REQUESTED' then 'NOT_REQUESTED'
      when v_plan_decision='REUSE' then 'REUSED'
      when cardinality(v_dependency_keys)=0 then 'READY'
      else 'BLOCKED'
    end;

    insert into public.orchestration_tasks (
      owner_id, project_id, run_id, task_key, profile_version, module_key,
      goal, plan_decision, status, dependency_keys, input_refs,
      output_schema_version, allowed_tools, model_role, budgets,
      completion_criteria, route_reason
    ) values (
      v_owner_id, v_project_id, p_run_id, v_task_key, p_profile_version,
      v_module_key, coalesce(v_task->>'goal', v_module_key), v_plan_decision,
      v_status, v_dependency_keys, coalesce(v_task->'input_refs', '[]'::jsonb),
      coalesce(v_task->>'output_schema_version', 'bp-task-output-v1'),
      v_allowed_tools, coalesce(v_task->>'model_role', 'STRONG'),
      coalesce(v_task->'budgets', '{}'::jsonb),
      coalesce(v_task->'completion_criteria', '[]'::jsonb), p_route_reason
    )
    on conflict (run_id, task_key) do update set
      profile_version=excluded.profile_version,
      module_key=excluded.module_key,
      goal=excluded.goal,
      plan_decision=excluded.plan_decision,
      status=case
        when public.orchestration_tasks.status in ('COMPLETED','REUSED','NOT_APPLICABLE')
          then public.orchestration_tasks.status
        else excluded.status
      end,
      dependency_keys=excluded.dependency_keys,
      input_refs=excluded.input_refs,
      output_schema_version=excluded.output_schema_version,
      allowed_tools=excluded.allowed_tools,
      model_role=excluded.model_role,
      budgets=excluded.budgets,
      completion_criteria=excluded.completion_criteria,
      route_reason=excluded.route_reason;
  end loop;

  return jsonb_build_object(
    'persisted', true,
    'run_id', p_run_id,
    'project_id', v_project_id,
    'profile_version', p_profile_version,
    'task_count', cardinality(v_keys),
    'ready_task_keys', coalesce((
      select jsonb_agg(task_key order by task_key)
      from public.orchestration_tasks
      where run_id=p_run_id and owner_id=v_owner_id and status='READY'
    ), '[]'::jsonb)
  );
end;
$$;

create or replace function public.claim_ready_orchestration_tasks(
  p_run_id uuid,
  p_limit integer default 3
)
returns setof public.orchestration_tasks
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_owner_id uuid := auth.uid();
begin
  if v_owner_id is null then
    raise exception 'AUTHENTICATION_REQUIRED' using errcode = '42501';
  end if;
  if p_limit is null or p_limit < 1 or p_limit > 5 then
    raise exception 'CLAIM_LIMIT_MUST_BE_1_TO_5' using errcode = '22023';
  end if;

  return query
  with claimable as (
    select ot.id
    from public.orchestration_tasks ot
    where ot.run_id=p_run_id and ot.owner_id=v_owner_id and ot.status='READY'
    order by ot.created_at, ot.task_key
    for update skip locked
    limit p_limit
  )
  update public.orchestration_tasks ot
  set status='RUNNING', started_at=coalesce(ot.started_at, now()),
      attempt_count=ot.attempt_count+1, route_reason='SCHEDULER_CLAIMED'
  from claimable c
  where ot.id=c.id
  returning ot.*;
end;
$$;

create or replace function public.observe_orchestration_task(
  p_task_id uuid,
  p_verdict text,
  p_summary text,
  p_output jsonb default null,
  p_evidence_ids uuid[] default '{}'::uuid[],
  p_limitations jsonb default '[]'::jsonb,
  p_retryable boolean default false,
  p_proposed_route text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_owner_id uuid := auth.uid();
  v_task public.orchestration_tasks;
  v_status text;
  v_unlocked integer := 0;
begin
  if v_owner_id is null then
    raise exception 'AUTHENTICATION_REQUIRED' using errcode = '42501';
  end if;
  if p_verdict not in (
    'VALID', 'NEEDS_REPAIR', 'NEEDS_INPUT', 'CONTRADICTORY', 'TOOL_FAILED',
    'NOT_APPLICABLE', 'POLICY_DENIED', 'BUDGET_EXHAUSTED'
  ) then
    raise exception 'OBSERVATION_VERDICT_INVALID' using errcode = '22023';
  end if;
  if coalesce(char_length(p_summary), 0) not between 1 and 4000 then
    raise exception 'OBSERVATION_SUMMARY_INVALID' using errcode = '22023';
  end if;
  if p_output is not null and jsonb_typeof(p_output) <> 'object' then
    raise exception 'TASK_OUTPUT_MUST_BE_OBJECT' using errcode = '22023';
  end if;
  if p_limitations is null or jsonb_typeof(p_limitations) <> 'array' then
    raise exception 'LIMITATIONS_MUST_BE_ARRAY' using errcode = '22023';
  end if;

  select * into v_task
  from public.orchestration_tasks ot
  where ot.id=p_task_id and ot.owner_id=v_owner_id
  for update;
  if v_task.id is null then
    raise exception 'TASK_NOT_FOUND' using errcode = 'P0002';
  end if;
  if v_task.status <> 'RUNNING' then
    raise exception 'TASK_MUST_BE_RUNNING_TO_OBSERVE' using errcode = '22023';
  end if;

  v_status := case
    when p_verdict='VALID' then 'COMPLETED'
    when p_verdict='NOT_APPLICABLE' then 'NOT_APPLICABLE'
    when p_verdict='NEEDS_INPUT' then 'NEEDS_INPUT'
    when p_verdict='CONTRADICTORY' then 'HUMAN_REVIEW'
    when p_verdict='NEEDS_REPAIR' then case when v_task.repair_count < 2 then 'READY' else 'HUMAN_REVIEW' end
    when p_verdict='TOOL_FAILED' then case when p_retryable and v_task.attempt_count < 3 then 'READY' else 'PARTIAL' end
    when p_verdict='BUDGET_EXHAUSTED' then 'PARTIAL'
    else 'SAFE_FAILED'
  end;

  insert into public.task_observations (
    owner_id, project_id, run_id, task_id, verdict, summary, evidence_ids,
    limitations, retryable, proposed_route, output_hash
  ) values (
    v_owner_id, v_task.project_id, v_task.run_id, v_task.id, p_verdict,
    p_summary, coalesce(p_evidence_ids, '{}'::uuid[]), p_limitations,
    p_retryable, p_proposed_route, md5(coalesce(p_output::text, ''))
  );

  update public.orchestration_tasks
  set status=v_status,
      observation_verdict=p_verdict,
      route_reason=coalesce(p_proposed_route, p_verdict),
      output=coalesce(p_output, output),
      repair_count=repair_count + case when p_verdict='NEEDS_REPAIR' then 1 else 0 end,
      completed_at=case when v_status in ('COMPLETED','NOT_APPLICABLE','PARTIAL','SAFE_FAILED') then now() else null end
  where id=v_task.id;

  if v_status in ('COMPLETED','NOT_APPLICABLE') then
    update public.orchestration_tasks candidate
    set status='READY', route_reason='DEPENDENCIES_SATISFIED'
    where candidate.run_id=v_task.run_id and candidate.owner_id=v_owner_id
      and candidate.status='BLOCKED'
      and candidate.dependency_keys <@ array(
        select done.task_key
        from public.orchestration_tasks done
        where done.run_id=v_task.run_id and done.owner_id=v_owner_id
          and done.status in ('COMPLETED','REUSED','NOT_APPLICABLE')
      );
    get diagnostics v_unlocked = row_count;
  end if;

  return jsonb_build_object(
    'recorded', true,
    'task_id', v_task.id,
    'task_key', v_task.task_key,
    'task_status', v_status,
    'unlocked_task_count', v_unlocked,
    'next_route', coalesce(p_proposed_route, p_verdict)
  );
end;
$$;

revoke all on function public.persist_dynamic_task_plan(uuid, integer, jsonb, text) from public, anon;
revoke all on function public.claim_ready_orchestration_tasks(uuid, integer) from public, anon;
revoke all on function public.observe_orchestration_task(uuid, text, text, jsonb, uuid[], jsonb, boolean, text) from public, anon;
grant execute on function public.persist_dynamic_task_plan(uuid, integer, jsonb, text) to authenticated;
grant execute on function public.claim_ready_orchestration_tasks(uuid, integer) to authenticated;
grant execute on function public.observe_orchestration_task(uuid, text, text, jsonb, uuid[], jsonb, boolean, text) to authenticated;

commit;
