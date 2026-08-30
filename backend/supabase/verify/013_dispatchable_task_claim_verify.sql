select 'dispatchable_claim_function' test,
       count(*)=1 and bool_and(p.prosecdef) passed,
       count(*)||'/1 security-definer function found' detail
from pg_proc p
join pg_namespace n on n.oid=p.pronamespace
where n.nspname='public'
  and p.proname='claim_dispatchable_orchestration_tasks'
  and p.pronargs=3
union all
select 'dispatchable_claim_authenticated_grant' test,
       count(*)=1 passed,
       count(*)||'/1 authenticated execute grant found' detail
from information_schema.routine_privileges
where routine_schema='public'
  and routine_name='claim_dispatchable_orchestration_tasks'
  and grantee='authenticated'
  and privilege_type='EXECUTE';
