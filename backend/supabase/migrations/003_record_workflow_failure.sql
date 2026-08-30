-- Blueprint Evidence Dev
-- Migration 003: narrow server-only RPC used by BP-90 Error and Audit.
-- The function is executable only by the Supabase service_role assigned to a
-- backend secret key. Ordinary authenticated/anonymous users cannot call it.

begin;

create or replace function public.record_workflow_failure(
  p_owner_id uuid,
  p_error_class text,
  p_retryable boolean,
  p_workflow_name text,
  p_safe_message text,
  p_correlation_id text,
  p_project_id uuid default null,
  p_run_id uuid default null,
  p_node_name text default null,
  p_redacted_details jsonb default '{}'::jsonb,
  p_recovery_action text default null,
  p_retry_exhausted boolean default false,
  p_payload_reference jsonb default '{}'::jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  current_run public.runs%rowtype;
  error_row public.errors%rowtype;
  dead_letter_id uuid;
  target_status text;
  next_version integer;
begin
  if p_owner_id is null or not exists (select 1 from auth.users where id = p_owner_id) then
    raise exception 'VALID_OWNER_REQUIRED' using errcode = '22023';
  end if;

  if p_error_class not in (
    'AUTH', 'VALIDATION', 'PROVIDER', 'RATE_LIMIT', 'TIMEOUT', 'SCHEMA',
    'QUALITY', 'CONFLICT', 'BUDGET', 'INTERNAL', 'UNKNOWN'
  ) then
    raise exception 'INVALID_ERROR_CLASS' using errcode = '22023';
  end if;

  if char_length(btrim(coalesce(p_workflow_name, ''))) = 0
     or char_length(btrim(coalesce(p_safe_message, ''))) = 0
     or char_length(btrim(coalesce(p_correlation_id, ''))) = 0 then
    raise exception 'WORKFLOW_MESSAGE_AND_CORRELATION_REQUIRED' using errcode = '22023';
  end if;

  if jsonb_typeof(coalesce(p_redacted_details, '{}'::jsonb)) <> 'object'
     or jsonb_typeof(coalesce(p_payload_reference, '{}'::jsonb)) <> 'object' then
    raise exception 'DETAILS_MUST_BE_JSON_OBJECTS' using errcode = '22023';
  end if;

  if p_project_id is not null and not exists (
    select 1 from public.projects where id = p_project_id and owner_id = p_owner_id
  ) then
    raise exception 'PROJECT_OWNER_MISMATCH' using errcode = '22023';
  end if;

  if p_run_id is not null then
    select * into current_run
    from public.runs
    where id = p_run_id and owner_id = p_owner_id
    for update;

    if not found then
      raise exception 'RUN_OWNER_MISMATCH' using errcode = '22023';
    end if;

    if p_project_id is not null and current_run.project_id <> p_project_id then
      raise exception 'RUN_PROJECT_MISMATCH' using errcode = '22023';
    end if;
  end if;

  insert into public.errors (
    owner_id,
    project_id,
    run_id,
    error_class,
    retryable,
    workflow_name,
    node_name,
    safe_message,
    redacted_technical_details,
    recovery_action,
    correlation_id
  ) values (
    p_owner_id,
    coalesce(p_project_id, current_run.project_id),
    p_run_id,
    p_error_class,
    p_retryable,
    left(p_workflow_name, 300),
    left(p_node_name, 300),
    left(p_safe_message, 1000),
    coalesce(p_redacted_details, '{}'::jsonb),
    left(p_recovery_action, 1000),
    left(p_correlation_id, 300)
  )
  returning * into error_row;

  if p_retry_exhausted then
    insert into public.dead_letter_events (
      owner_id,
      project_id,
      run_id,
      error_id,
      payload_reference,
      originating_workflow,
      originating_node,
      failure_class,
      correlation_id,
      replay_eligible
    ) values (
      p_owner_id,
      coalesce(p_project_id, current_run.project_id),
      p_run_id,
      error_row.id,
      coalesce(p_payload_reference, '{}'::jsonb),
      left(p_workflow_name, 300),
      left(p_node_name, 300),
      p_error_class,
      left(p_correlation_id, 300),
      p_retryable
    )
    returning id into dead_letter_id;
  end if;

  if p_run_id is not null
     and current_run.status not in ('COMPLETED', 'PARTIAL', 'SAFE_FAILED', 'CANCELLED') then
    target_status := case
      when p_retry_exhausted or not p_retryable then 'SAFE_FAILED'
      else 'HUMAN_REVIEW'
    end;

    if not exists (
      select 1 from public.allowed_run_transitions
      where from_status = current_run.status and to_status = target_status
    ) then
      target_status := 'SAFE_FAILED';
    end if;

    if exists (
      select 1 from public.allowed_run_transitions
      where from_status = current_run.status and to_status = target_status
    ) then
      perform set_config('blueprint.allow_state_transition', 'on', true);

      update public.runs
      set status = target_status,
          current_route = 'SAFE_FAIL',
          current_node = p_node_name,
          state_version = state_version + 1,
          transition_count = least(20, transition_count + 1),
          updated_at = now()
      where id = current_run.id
      returning state_version into next_version;

      perform set_config('blueprint.allow_state_transition', 'off', true);

      insert into public.state_transitions (
        owner_id,
        project_id,
        run_id,
        from_status,
        to_status,
        route,
        actor,
        reason_code,
        detail,
        state_version,
        correlation_id
      ) values (
        p_owner_id,
        current_run.project_id,
        current_run.id,
        current_run.status,
        target_status,
        'SAFE_FAIL',
        'SYSTEM',
        'WORKFLOW_ERROR',
        jsonb_build_object(
          'error_id', error_row.id,
          'error_class', p_error_class,
          'retryable', p_retryable,
          'retry_exhausted', p_retry_exhausted
        ),
        next_version,
        left(p_correlation_id, 300)
      );
    end if;
  end if;

  return jsonb_build_object(
    'recorded', true,
    'error_id', error_row.id,
    'dead_letter_id', dead_letter_id,
    'run_id', p_run_id,
    'run_status', coalesce(target_status, current_run.status),
    'correlation_id', p_correlation_id
  );
end;
$$;

revoke all on function public.record_workflow_failure(
  uuid, text, boolean, text, text, text, uuid, uuid, text, jsonb, text, boolean, jsonb
) from public, anon, authenticated;

grant execute on function public.record_workflow_failure(
  uuid, text, boolean, text, text, text, uuid, uuid, text, jsonb, text, boolean, jsonb
) to service_role;

commit;
