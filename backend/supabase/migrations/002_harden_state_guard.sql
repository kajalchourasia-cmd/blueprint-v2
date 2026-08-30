-- Blueprint Evidence Dev
-- Migration 002: reset the internal state-update bypass immediately after the
-- guarded UPDATE so it cannot leak to a later statement in the transaction.

begin;

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

commit;
