-- Run after migration 011. Every row should return passed = true.

with expected_tables(name) as (
  values ('stage_verdicts'),('blueprint_stage_progress'),('founder_metric_observations')
), tables as (
  select count(*)=3 passed, format('%s/3 new tables exist',count(*)) detail
  from expected_tables e join information_schema.tables t
    on t.table_schema='public' and t.table_name=e.name
), rls as (
  select count(*)=3 and bool_and(c.relrowsecurity) passed,
    format('%s/3 new tables have RLS',count(*)) detail
  from expected_tables e
  join pg_class c on c.relname=e.name
  join pg_namespace n on n.oid=c.relnamespace and n.nspname='public'
), policies as (
  select count(*)=7 passed, format('%s/7 owner policies exist',count(*)) detail
  from pg_policies p join expected_tables e on e.name=p.tablename
  where p.schemaname='public'
), functions as (
  select count(*)=3 passed, format('%s/3 progressive-state functions exist',count(*)) detail
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace and n.nspname='public'
  where p.proname in ('persist_research_verdict','create_progressive_blueprint_version','get_progressive_blueprint_dashboard')
), version_columns as (
  select count(*)=5 passed, format('%s/5 Blueprint version columns exist',count(*)) detail
  from information_schema.columns
  where table_schema='public' and table_name='blueprint_versions'
    and column_name in ('version_kind','artifact_stage','label','change_summary','source_verdict_ids')
), constraints as (
  select count(*)=6 passed, format('%s/6 expanded constraints exist',count(*)) detail
  from pg_constraint where conname in (
    'runs_current_route_check','orchestration_tasks_module_key_check',
    'human_checkpoints_checkpoint_type_check','human_checkpoints_decision_check',
    'blueprint_versions_version_kind_check','blueprint_versions_artifact_stage_check'
  )
)
select 'new_tables' check_name,passed,detail from tables
union all select 'rls_enabled',passed,detail from rls
union all select 'owner_policies',passed,detail from policies
union all select 'functions',passed,detail from functions
union all select 'version_columns',passed,detail from version_columns
union all select 'expanded_constraints',passed,detail from constraints
order by check_name;
