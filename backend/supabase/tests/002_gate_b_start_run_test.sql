-- Blueprint Evidence Dev — Gate B authenticated start-run test
-- Requires two Supabase Auth users. All test rows are rolled back.

do $gate_b$
declare
  user_a uuid;
  user_b uuid;
  first_result jsonb;
  replay_result jsonb;
  user_b_result jsonb;
  same_run_replayed boolean := false;
  first_marked_new boolean := false;
  replay_marked_duplicate boolean := false;
  owner_isolation_passed boolean := false;
  anon_execute_blocked boolean := false;
  invalid_input_blocked boolean := false;
  visible_count integer := 0;
  result_payload jsonb;
begin
  select id into user_a from auth.users order by created_at, id limit 1;
  select id into user_b from auth.users order by created_at, id offset 1 limit 1;

  if user_a is null or user_b is null then
    raise exception 'GATE_B_REQUIRES_TWO_AUTH_USERS';
  end if;

  begin
    perform set_config('request.jwt.claim.role', 'authenticated', true);
    perform set_config('request.jwt.claim.sub', user_a::text, true);
    execute 'set local role authenticated';

    first_result := public.start_blueprint_run(
      'gate-b-start-key-0001',
      'An evidence-first founder validation assistant for a rollback-only Gate B test.',
      'Founder tools',
      'Global',
      '{"time_budget_hours":24}'::jsonb,
      '{"source":"gate_b_test"}'::jsonb
    );

    replay_result := public.start_blueprint_run(
      'gate-b-start-key-0001',
      'This changed replay body must not create a second project or run.',
      null,
      null,
      '{}'::jsonb,
      '{"source":"gate_b_replay"}'::jsonb
    );

    same_run_replayed := first_result->>'run_id' = replay_result->>'run_id'
      and first_result->>'project_id' = replay_result->>'project_id';
    first_marked_new := (first_result->>'duplicate')::boolean is false
      and first_result->>'status' = 'NEW';
    replay_marked_duplicate := (replay_result->>'duplicate')::boolean is true;

    begin
      perform public.start_blueprint_run(
        'short', 'too short', null, null, '{}'::jsonb, '{}'::jsonb
      );
      raise exception 'INVALID_INPUT_WAS_ALLOWED';
    exception
      when invalid_parameter_value then invalid_input_blocked := true;
    end;

    perform set_config('request.jwt.claim.sub', user_b::text, true);
    select count(*) into visible_count
    from public.runs
    where id = (first_result->>'run_id')::uuid;

    user_b_result := public.start_blueprint_run(
      'gate-b-start-key-0001',
      'A second owner can reuse the same idempotency key without crossing tenant boundaries.',
      'Testing', 'Global', '{}'::jsonb, '{}'::jsonb
    );

    owner_isolation_passed := visible_count = 0
      and user_b_result->>'run_id' <> first_result->>'run_id';

    execute 'set local role anon';
    perform set_config('request.jwt.claim.role', 'anon', true);
    perform set_config('request.jwt.claim.sub', '', true);
    begin
      perform public.start_blueprint_run(
        'gate-b-anon-key-001',
        'Anonymous users must not be allowed to create Blueprint runs.',
        null, null, '{}'::jsonb, '{}'::jsonb
      );
      raise exception 'ANON_EXECUTE_WAS_ALLOWED';
    exception
      when insufficient_privilege then anon_execute_blocked := true;
    end;

    raise exception 'BP_GATE_B_TEST_ROLLBACK';
  exception
    when raise_exception then
      if sqlerrm <> 'BP_GATE_B_TEST_ROLLBACK' then
        raise;
      end if;
  end;

  result_payload := jsonb_build_object(
    'same_run_replayed', same_run_replayed,
    'first_marked_new', first_marked_new,
    'replay_marked_duplicate', replay_marked_duplicate,
    'owner_isolation_passed', owner_isolation_passed,
    'anon_execute_blocked', anon_execute_blocked,
    'invalid_input_blocked', invalid_input_blocked
  );

  if result_payload @> '{
    "same_run_replayed": true,
    "first_marked_new": true,
    "replay_marked_duplicate": true,
    "owner_isolation_passed": true,
    "anon_execute_blocked": true,
    "invalid_input_blocked": true
  }'::jsonb is not true then
    raise exception 'BP_GATE_B_TEST_FAILED: %', result_payload;
  end if;

  perform set_config('blueprint.gate_b_result', result_payload::text, false);
end;
$gate_b$;

select key as check_name, value::boolean as passed
from jsonb_each_text(current_setting('blueprint.gate_b_result')::jsonb)
order by key;
