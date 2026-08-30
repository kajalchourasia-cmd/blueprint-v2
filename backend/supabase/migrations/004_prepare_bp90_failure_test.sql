-- Blueprint Evidence Dev
-- Migration 004: server-only setup helper for the BP-90 controlled failure test.
-- Creates synthetic, clearly labelled test records and returns their identifiers
-- to n8n without embedding an Auth user UUID in an exported workflow.

begin;

create or replace function public.prepare_bp90_failure_test()
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  test_owner_id uuid;
  test_project_id uuid;
  test_run_id uuid;
  test_key text := 'bp90-controlled-failure-' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS');
  test_correlation_id text := 'bp90-test-' || gen_random_uuid()::text;
begin
  select id into test_owner_id
  from auth.users
  order by created_at, id
  limit 1;

  if test_owner_id is null then
    raise exception 'BP90_TEST_REQUIRES_ONE_AUTH_USER' using errcode = 'P0001';
  end if;

  insert into public.projects (
    owner_id,
    idea_text,
    optional_industry,
    geography,
    constraints,
    normalized_frame
  ) values (
    test_owner_id,
    'Synthetic BP-90 controlled failure test. This record contains no founder research data.',
    'INTEGRATION_TEST',
    'Global',
    jsonb_build_object('synthetic', true, 'test_scope', 'BP-90'),
    jsonb_build_object('synthetic', true)
  )
  returning id into test_project_id;

  insert into public.runs (
    owner_id,
    project_id,
    idempotency_key,
    status,
    original_request,
    deadline_at
  ) values (
    test_owner_id,
    test_project_id,
    test_key,
    'NEW',
    jsonb_build_object('synthetic', true, 'test_scope', 'BP-90'),
    now() + interval '15 minutes'
  )
  returning id into test_run_id;

  return jsonb_build_object(
    'owner_id', test_owner_id,
    'project_id', test_project_id,
    'run_id', test_run_id,
    'correlation_id', test_correlation_id,
    'synthetic', true
  );
end;
$$;

revoke all on function public.prepare_bp90_failure_test() from public, anon, authenticated;
grant execute on function public.prepare_bp90_failure_test() to service_role;

commit;
