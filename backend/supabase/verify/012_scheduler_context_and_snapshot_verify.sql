with expected(name) as (
  values
    ('get_orchestration_task_context'),
    ('get_orchestration_run_snapshot')
), found as (
  select p.proname name, p.pronargs,
         p.prosecdef security_definer
  from pg_proc p
  join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='public'
    and p.proname in ('get_orchestration_task_context','get_orchestration_run_snapshot')
    and p.pronargs=1
)
select 'scheduler_context_functions' test,
       count(*)=2 and bool_and(f.security_definer) passed,
       count(*)||'/2 owner-scoped functions found' detail
from expected e
join found f using (name)
union all
select 'scheduler_context_authenticated_grants' test,
       count(*)=2 passed,
       count(*)||'/2 authenticated execute grants found' detail
from information_schema.routine_privileges
where routine_schema='public'
  and routine_name in ('get_orchestration_task_context','get_orchestration_run_snapshot')
  and grantee='authenticated'
  and privilege_type='EXECUTE';
