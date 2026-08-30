-- Blueprint Evidence Dev — Gate A RLS and state-machine test
-- Prerequisite: at least two confirmed Supabase Auth users.
-- All inserted rows live inside an inner subtransaction that is deliberately
-- rolled back. The final SELECT is the only visible result.

do $gate_a$
declare
  user_a uuid;
  user_b uuid;
  project_a uuid;
  run_a uuid;
  visible_count integer := 0;
  transition_rows integer := 0;
  same_user_read boolean := false;
  cross_user_read_blocked boolean := false;
  cross_user_write_blocked boolean := false;
  cross_user_rpc_blocked boolean := false;
  legal_transition_passed boolean := false;
  stale_version_blocked boolean := false;
  illegal_transition_blocked boolean := false;
  direct_state_bypass_blocked boolean := false;
  duplicate_run_blocked boolean := false;
  result_payload jsonb;
begin
  select id into user_a
  from auth.users
  order by created_at, id
  limit 1;

  select id into user_b
  from auth.users
  order by created_at, id
  offset 1 limit 1;

  if user_a is null or user_b is null then
    raise exception 'GATE_A_REQUIRES_TWO_AUTH_USERS';
  end if;

  begin
    perform set_config('request.jwt.claim.role', 'authenticated', true);
    perform set_config('request.jwt.claim.sub', user_a::text, true);
    execute 'set local role authenticated';

    insert into public.projects (idea_text, optional_industry, geography)
    values (
      'Rollback-only Gate A test idea for authenticated ownership verification.',
      'Testing',
      'Global'
    )
    returning id into project_a;

    insert into public.runs (
      project_id,
      idempotency_key,
      original_request,
      deadline_at
    ) values (
      project_a,
      'gate-a-idempotency-key-001',
      '{"source":"gate_a_test"}'::jsonb,
      now() + interval '15 minutes'
    )
    returning id into run_a;

    select count(*) into visible_count
    from public.projects
    where id = project_a;
    same_user_read := visible_count = 1;

    begin
      insert into public.runs (project_id, idempotency_key, original_request)
      values (project_a, 'gate-a-idempotency-key-001', '{}'::jsonb);
      raise exception 'DUPLICATE_RUN_WAS_ALLOWED';
    exception
      when unique_violation then duplicate_run_blocked := true;
    end;

    perform set_config('request.jwt.claim.sub', user_b::text, true);

    select count(*) into visible_count
    from public.projects
    where id = project_a;
    cross_user_read_blocked := visible_count = 0;

    begin
      insert into public.runs (project_id, idempotency_key, original_request)
      values (project_a, 'gate-a-cross-user-write-001', '{}'::jsonb);
      raise exception 'CROSS_USER_WRITE_WAS_ALLOWED';
    exception
      when insufficient_privilege or foreign_key_violation then
        cross_user_write_blocked := true;
    end;

    begin
      perform public.advance_run_state(
        run_a,
        0,
        'FRAMING',
        'IDEA_FRAME',
        '{"actor":"SUPERVISOR","reason_code":"GATE_A_CROSS_USER_TEST"}'::jsonb
      );
      raise exception 'CROSS_USER_RPC_WAS_ALLOWED';
    exception
      when no_data_found then cross_user_rpc_blocked := true;
    end;

    perform set_config('request.jwt.claim.sub', user_a::text, true);

    perform public.advance_run_state(
      run_a,
      0,
      'FRAMING',
      'IDEA_FRAME',
      '{"actor":"SUPERVISOR","reason_code":"GATE_A_LEGAL_TRANSITION","correlation_id":"gate-a-001"}'::jsonb
    );

    select count(*) into visible_count
    from public.runs
    where id = run_a
      and status = 'FRAMING'
      and state_version = 1
      and transition_count = 1;

    select count(*) into transition_rows
    from public.state_transitions
    where run_id = run_a
      and from_status = 'NEW'
      and to_status = 'FRAMING'
      and state_version = 1;

    legal_transition_passed := visible_count = 1 and transition_rows = 1;

    begin
      perform public.advance_run_state(
        run_a,
        0,
        'PLANNING',
        'CUSTOMER_DEMAND',
        '{"actor":"SUPERVISOR","reason_code":"GATE_A_STALE_TEST"}'::jsonb
      );
      raise exception 'STALE_VERSION_WAS_ALLOWED';
    exception
      when serialization_failure then stale_version_blocked := true;
    end;

    begin
      perform public.advance_run_state(
        run_a,
        1,
        'COMPLETED',
        'COMPLETE',
        '{"actor":"SUPERVISOR","reason_code":"GATE_A_ILLEGAL_ROUTE_TEST"}'::jsonb
      );
      raise exception 'ILLEGAL_TRANSITION_WAS_ALLOWED';
    exception
      when invalid_parameter_value then illegal_transition_blocked := true;
    end;

    begin
      update public.runs
      set status = 'COMPLETED', state_version = 99
      where id = run_a;
      raise exception 'DIRECT_STATE_BYPASS_WAS_ALLOWED';
    exception
      when insufficient_privilege then direct_state_bypass_blocked := true;
    end;

    raise exception 'BP_GATE_A_TEST_ROLLBACK';
  exception
    when raise_exception then
      if sqlerrm <> 'BP_GATE_A_TEST_ROLLBACK' then
        raise;
      end if;
  end;

  result_payload := jsonb_build_object(
    'same_user_read', same_user_read,
    'cross_user_read_blocked', cross_user_read_blocked,
    'cross_user_write_blocked', cross_user_write_blocked,
    'cross_user_rpc_blocked', cross_user_rpc_blocked,
    'legal_transition_passed', legal_transition_passed,
    'stale_version_blocked', stale_version_blocked,
    'illegal_transition_blocked', illegal_transition_blocked,
    'direct_state_bypass_blocked', direct_state_bypass_blocked,
    'duplicate_run_blocked', duplicate_run_blocked
  );

  if result_payload @> '{
    "same_user_read": true,
    "cross_user_read_blocked": true,
    "cross_user_write_blocked": true,
    "cross_user_rpc_blocked": true,
    "legal_transition_passed": true,
    "stale_version_blocked": true,
    "illegal_transition_blocked": true,
    "direct_state_bypass_blocked": true,
    "duplicate_run_blocked": true
  }'::jsonb is not true then
    raise exception 'BP_GATE_A_TEST_FAILED: %', result_payload;
  end if;

  perform set_config('blueprint.gate_a_result', result_payload::text, false);
end;
$gate_a$;

select
  key as check_name,
  value::boolean as passed
from jsonb_each_text(current_setting('blueprint.gate_a_result')::jsonb)
order by key;
