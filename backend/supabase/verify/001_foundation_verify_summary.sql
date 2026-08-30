-- Blueprint Evidence Dev — single-result verification for migration 001
-- Every returned row must show passed = true.

with
expected_tables(table_name) as (
  values
    ('projects'), ('runs'), ('hypotheses'), ('evidence'), ('competitors'),
    ('agent_runs'), ('tool_calls'), ('quality_checks'), ('state_transitions'),
    ('research_tasks'), ('approvals'), ('errors'), ('dead_letter_events'),
    ('artifacts'), ('feedback'), ('allowed_run_transitions')
),
table_check as (
  select
    count(t.table_name)::bigint as actual,
    coalesce(string_agg(e.table_name, ', ') filter (where t.table_name is null), 'none') as detail
  from expected_tables e
  left join information_schema.tables t
    on t.table_schema = 'public' and t.table_name = e.table_name
),
rls_check as (
  select
    count(*) filter (where rowsecurity)::bigint as actual,
    coalesce(string_agg(tablename, ', ') filter (where not rowsecurity), 'none') as detail
  from pg_tables
  where schemaname = 'public'
    and tablename in (select table_name from expected_tables)
),
policy_check as (
  select count(*)::bigint as actual
  from pg_policies
  where schemaname in ('public', 'storage')
    and (
      tablename in (select table_name from expected_tables)
      or policyname like 'blueprint_artifacts_%'
    )
),
bucket_check as (
  select count(*) filter (where id = 'blueprint-artifacts' and public = false)::bigint as actual
  from storage.buckets
),
transition_check as (
  select count(*)::bigint as actual from public.allowed_run_transitions
),
rpc_check as (
  select count(*)::bigint as actual
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace
  where n.nspname = 'public' and p.proname = 'advance_run_state'
),
index_check as (
  select count(*)::bigint as actual
  from pg_indexes
  where schemaname = 'public'
    and indexname in (
      'projects_owner_idx', 'runs_owner_project_idx', 'runs_status_route_idx',
      'hypotheses_run_status_idx', 'evidence_content_dedupe_idx',
      'evidence_run_verdict_idx', 'evidence_source_idx', 'competitors_run_idx',
      'agent_runs_run_idx', 'tool_calls_run_idx', 'quality_checks_run_idx',
      'state_transitions_run_idx', 'research_tasks_run_idx', 'approvals_run_idx',
      'errors_run_idx', 'dead_letter_status_idx', 'artifacts_run_idx'
    )
),
checks as (
  select 1 as display_order, 'tables'::text as check_name, actual, 16::bigint as expected, actual = 16 as passed, 'missing: ' || detail as detail from table_check
  union all
  select 2, 'rls', actual, 16, actual = 16, 'disabled: ' || detail from rls_check
  union all
  select 3, 'policies', actual, 47, actual >= 47, 'minimum required' from policy_check
  union all
  select 4, 'private_bucket', actual, 1, actual = 1, 'blueprint-artifacts must be private' from bucket_check
  union all
  select 5, 'allowed_transitions', actual, 52, actual = 52, 'state-machine edges' from transition_check
  union all
  select 6, 'state_rpc', actual, 1, actual = 1, 'advance_run_state' from rpc_check
  union all
  select 7, 'critical_indexes', actual, 17, actual >= 17, 'minimum required' from index_check
)
select check_name, actual, expected, passed, detail
from checks
order by display_order;

