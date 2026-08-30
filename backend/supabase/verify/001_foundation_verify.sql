-- Blueprint Evidence Dev — read-only verification for migration 001
-- Run in Supabase SQL Editor after 001_foundation.sql succeeds.

with expected(table_name) as (
  values
    ('projects'), ('runs'), ('hypotheses'), ('evidence'), ('competitors'),
    ('agent_runs'), ('tool_calls'), ('quality_checks'), ('state_transitions'),
    ('research_tasks'), ('approvals'), ('errors'), ('dead_letter_events'),
    ('artifacts'), ('feedback'), ('allowed_run_transitions')
), present as (
  select table_name
  from information_schema.tables
  where table_schema = 'public'
)
select
  'tables' as check_name,
  count(*) filter (where p.table_name is not null) as actual,
  count(*) as expected,
  coalesce(string_agg(e.table_name, ', ') filter (where p.table_name is null), 'none') as missing
from expected e
left join present p using (table_name);

select
  'rls' as check_name,
  count(*) filter (where rowsecurity) as actual,
  16 as expected,
  coalesce(string_agg(tablename, ', ') filter (where not rowsecurity), 'none') as missing_or_disabled
from pg_tables
where schemaname = 'public'
  and tablename in (
    'projects', 'runs', 'hypotheses', 'evidence', 'competitors',
    'agent_runs', 'tool_calls', 'quality_checks', 'state_transitions',
    'research_tasks', 'approvals', 'errors', 'dead_letter_events',
    'artifacts', 'feedback', 'allowed_run_transitions'
  );

select
  'policies' as check_name,
  count(*) as actual,
  47 as expected_minimum
from pg_policies
where schemaname in ('public', 'storage')
  and (
    tablename in (
      'projects', 'runs', 'hypotheses', 'evidence', 'competitors',
      'agent_runs', 'tool_calls', 'quality_checks', 'state_transitions',
      'research_tasks', 'approvals', 'errors', 'dead_letter_events',
      'artifacts', 'feedback', 'allowed_run_transitions'
    )
    or policyname like 'blueprint_artifacts_%'
  );

select
  'private_bucket' as check_name,
  count(*) filter (where id = 'blueprint-artifacts' and public = false) as actual,
  1 as expected
from storage.buckets;

select
  'allowed_transitions' as check_name,
  count(*) as actual,
  52 as expected
from public.allowed_run_transitions;

select
  'state_rpc' as check_name,
  count(*) as actual,
  1 as expected
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
  and p.proname = 'advance_run_state';

select
  'critical_indexes' as check_name,
  count(*) as actual,
  17 as expected_minimum
from pg_indexes
where schemaname = 'public'
  and indexname in (
    'projects_owner_idx', 'runs_owner_project_idx', 'runs_status_route_idx',
    'hypotheses_run_status_idx', 'evidence_content_dedupe_idx',
    'evidence_run_verdict_idx', 'evidence_source_idx', 'competitors_run_idx',
    'agent_runs_run_idx', 'tool_calls_run_idx', 'quality_checks_run_idx',
    'state_transitions_run_idx', 'research_tasks_run_idx', 'approvals_run_idx',
    'errors_run_idx', 'dead_letter_status_idx', 'artifacts_run_idx'
  );
