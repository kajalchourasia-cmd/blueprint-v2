-- Run after migration 010. Every row should return passed = true.

with expected(name) as (
  values
    ('persist_dynamic_task_plan'),
    ('claim_ready_orchestration_tasks'),
    ('observe_orchestration_task')
), functions as (
  select count(*)=3 as passed, format('%s/3 scheduler functions exist', count(*)) detail
  from expected e
  join pg_proc p on p.proname=e.name
  join pg_namespace n on n.oid=p.pronamespace and n.nspname='public'
), authenticated_grants as (
  select count(*)=3 as passed, format('%s/3 functions executable by authenticated', count(*)) detail
  from expected e
  where has_function_privilege(
    'authenticated',
    case e.name
      when 'persist_dynamic_task_plan' then 'public.persist_dynamic_task_plan(uuid,integer,jsonb,text)'
      when 'claim_ready_orchestration_tasks' then 'public.claim_ready_orchestration_tasks(uuid,integer)'
      else 'public.observe_orchestration_task(uuid,text,text,jsonb,uuid[],jsonb,boolean,text)'
    end,
    'EXECUTE'
  )
), anon_denied as (
  select count(*)=3 as passed, format('%s/3 functions denied to anon', count(*)) detail
  from expected e
  where not has_function_privilege(
    'anon',
    case e.name
      when 'persist_dynamic_task_plan' then 'public.persist_dynamic_task_plan(uuid,integer,jsonb,text)'
      when 'claim_ready_orchestration_tasks' then 'public.claim_ready_orchestration_tasks(uuid,integer)'
      else 'public.observe_orchestration_task(uuid,text,text,jsonb,uuid[],jsonb,boolean,text)'
    end,
    'EXECUTE'
  )
)
select 'functions_exist' check_name, passed, detail from functions
union all select 'authenticated_execute', passed, detail from authenticated_grants
union all select 'anon_denied', passed, detail from anon_denied
order by check_name;
