-- Run after migration 009. Every row should return passed = true.

with expected_tables(name) as (
  values
    ('project_profiles'), ('blueprint_versions'), ('orchestration_tasks'),
    ('task_observations'), ('human_checkpoints'), ('next_actions'),
    ('dashboard_signals'), ('rerun_requests'), ('memory_projections')
), table_result as (
  select
    count(*) = 9 as passed,
    format('%s/9 required tables exist', count(*)) as detail
  from expected_tables e
  join information_schema.tables t
    on t.table_schema='public' and t.table_name=e.name
), rls_result as (
  select
    count(*) = 9 and bool_and(c.relrowsecurity) as passed,
    format('%s/9 required tables have RLS enabled', count(*)) as detail
  from expected_tables e
  join pg_class c on c.relname=e.name
  join pg_namespace n on n.oid=c.relnamespace and n.nspname='public'
), policy_result as (
  select
    count(*) >= 24 as passed,
    format('%s owner-scoped policies found (minimum 24)', count(*)) as detail
  from pg_policies p
  join expected_tables e on e.name=p.tablename
  where p.schemaname='public'
), function_result as (
  select
    count(*) = 2 as passed,
    format('%s/2 required functions exist', count(*)) as detail
  from pg_proc p
  join pg_namespace n on n.oid=p.pronamespace and n.nspname='public'
  where p.proname in ('create_project_profile_version', 'get_dynamic_blueprint_state')
), constraint_result as (
  select
    count(*) = 7 as passed,
    format('%s/7 expanded legacy constraints exist', count(*)) as detail
  from pg_constraint c
  where c.conname in (
    'runs_current_route_check', 'agent_runs_agent_check',
    'blueprint_sections_section_key_check', 'blueprint_sections_status_check',
    'chat_messages_intent_check', 'agent_commands_command_type_check',
    'approvals_proposal_type_check'
  )
)
select 'required_tables' as check_name, passed, detail from table_result
union all select 'rls_enabled', passed, detail from rls_result
union all select 'owner_policies', passed, detail from policy_result
union all select 'required_functions', passed, detail from function_result
union all select 'expanded_constraints', passed, detail from constraint_result
order by check_name;
