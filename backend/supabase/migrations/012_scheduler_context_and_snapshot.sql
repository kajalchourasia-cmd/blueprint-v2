-- Blueprint Evidence Dev
-- Migration 012: owner-scoped execution context and observable run snapshot.

begin;

create or replace function public.get_orchestration_task_context(p_task_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_owner_id uuid := auth.uid();
  v_task public.orchestration_tasks;
  v_profile jsonb;
begin
  if v_owner_id is null then
    raise exception 'AUTHENTICATION_REQUIRED' using errcode = '42501';
  end if;

  select * into v_task
  from public.orchestration_tasks ot
  where ot.id=p_task_id and ot.owner_id=v_owner_id;

  if v_task.id is null then
    raise exception 'TASK_NOT_FOUND' using errcode = 'P0002';
  end if;
  if v_task.status <> 'RUNNING' then
    raise exception 'ONLY_CLAIMED_RUNNING_TASKS_HAVE_EXECUTION_CONTEXT' using errcode = '22023';
  end if;

  select pp.payload into v_profile
  from public.project_profiles pp
  where pp.project_id=v_task.project_id
    and pp.owner_id=v_owner_id
    and pp.version=v_task.profile_version;

  if v_profile is null then
    raise exception 'PROFILE_VERSION_NOT_FOUND' using errcode = 'P0002';
  end if;

  return jsonb_build_object(
    'schema_version', 'bp-task-execution-context-v1',
    'owner_id', v_owner_id,
    'project_id', v_task.project_id,
    'run_id', v_task.run_id,
    'profile_version', v_task.profile_version,
    'profile', v_profile,
    'task', to_jsonb(v_task),
    'dependency_outputs', coalesce((
      select jsonb_agg(jsonb_build_object(
        'task_id', dep.id,
        'task_key', dep.task_key,
        'module_key', dep.module_key,
        'status', dep.status,
        'observation_verdict', dep.observation_verdict,
        'output', dep.output,
        'route_reason', dep.route_reason
      ) order by dep.task_key)
      from public.orchestration_tasks dep
      where dep.run_id=v_task.run_id
        and dep.owner_id=v_owner_id
        and dep.task_key=any(v_task.dependency_keys)
    ), '[]'::jsonb),
    'latest_stage_verdict', (
      select to_jsonb(sv)
      from public.stage_verdicts sv
      where sv.run_id=v_task.run_id and sv.owner_id=v_owner_id
      order by sv.created_at desc
      limit 1
    ),
    'pending_checkpoints', coalesce((
      select jsonb_agg(to_jsonb(h) order by h.created_at)
      from public.human_checkpoints h
      where h.run_id=v_task.run_id and h.owner_id=v_owner_id and h.status='PENDING'
    ), '[]'::jsonb)
  );
end;
$$;

create or replace function public.get_orchestration_run_snapshot(p_run_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_owner_id uuid := auth.uid();
  v_run public.runs;
begin
  if v_owner_id is null then
    raise exception 'AUTHENTICATION_REQUIRED' using errcode = '42501';
  end if;

  select * into v_run
  from public.runs r
  where r.id=p_run_id and r.owner_id=v_owner_id;

  if v_run.id is null then
    raise exception 'RUN_NOT_FOUND' using errcode = 'P0002';
  end if;

  return jsonb_build_object(
    'schema_version', 'bp-orchestration-run-snapshot-v1',
    'run', to_jsonb(v_run),
    'task_counts', coalesce((
      select jsonb_object_agg(status, total)
      from (
        select status, count(*) total
        from public.orchestration_tasks
        where run_id=p_run_id and owner_id=v_owner_id
        group by status
      ) counts
    ), '{}'::jsonb),
    'tasks', coalesce((
      select jsonb_agg(jsonb_build_object(
        'id', ot.id,
        'task_key', ot.task_key,
        'module_key', ot.module_key,
        'status', ot.status,
        'plan_decision', ot.plan_decision,
        'dependency_keys', ot.dependency_keys,
        'attempt_count', ot.attempt_count,
        'repair_count', ot.repair_count,
        'observation_verdict', ot.observation_verdict,
        'route_reason', ot.route_reason,
        'updated_at', ot.updated_at
      ) order by ot.created_at, ot.task_key)
      from public.orchestration_tasks ot
      where ot.run_id=p_run_id and ot.owner_id=v_owner_id
    ), '[]'::jsonb),
    'pending_checkpoints', coalesce((
      select jsonb_agg(to_jsonb(h) order by h.created_at)
      from public.human_checkpoints h
      where h.run_id=p_run_id and h.owner_id=v_owner_id and h.status='PENDING'
    ), '[]'::jsonb),
    'stage_progress', coalesce((
      select jsonb_agg(to_jsonb(sp) order by sp.created_at)
      from public.blueprint_stage_progress sp
      where sp.run_id=p_run_id and sp.owner_id=v_owner_id
    ), '[]'::jsonb),
    'latest_verdict', (
      select to_jsonb(sv)
      from public.stage_verdicts sv
      where sv.run_id=p_run_id and sv.owner_id=v_owner_id
      order by sv.created_at desc
      limit 1
    )
  );
end;
$$;

revoke all on function public.get_orchestration_task_context(uuid) from public, anon;
revoke all on function public.get_orchestration_run_snapshot(uuid) from public, anon;
grant execute on function public.get_orchestration_task_context(uuid) to authenticated;
grant execute on function public.get_orchestration_run_snapshot(uuid) to authenticated;

commit;
