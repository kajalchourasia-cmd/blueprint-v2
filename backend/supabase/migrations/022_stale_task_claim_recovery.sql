-- Blueprint Evidence Dev
-- Migration 022: lease-style recovery for workers that were claimed but never observed.

begin;

create or replace function public.claim_dispatchable_orchestration_tasks(
  p_run_id uuid,
  p_limit integer default 3,
  p_allowed_modules text[] default array['foundation','customer_demand','competitor_intelligence','market_economics']::text[]
)
returns setof public.orchestration_tasks
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_owner_id uuid := auth.uid();
  v_known_modules constant text[] := array[
    'foundation','customer_demand','competitor_intelligence','market_economics',
    'evidence_audit','research_verdict','final_blueprint','assumptions_risks',
    'offer_pricing','validation_proof','operating_model','financial_readiness',
    'execution_readiness','launch_distribution','growth_optimization','action_blueprint'
  ]::text[];
begin
  if v_owner_id is null then
    raise exception 'AUTHENTICATION_REQUIRED' using errcode = '42501';
  end if;
  if p_limit is null or p_limit < 1 or p_limit > 5 then
    raise exception 'CLAIM_LIMIT_MUST_BE_1_TO_5' using errcode = '22023';
  end if;
  if p_allowed_modules is null or cardinality(p_allowed_modules) < 1
     or cardinality(p_allowed_modules) > 8 then
    raise exception 'ALLOWED_MODULES_MUST_HAVE_1_TO_8_ITEMS' using errcode = '22023';
  end if;
  if exists (
    select 1 from unnest(p_allowed_modules) module_key
    where not (module_key=any(v_known_modules))
  ) then
    raise exception 'UNKNOWN_DISPATCH_MODULE' using errcode = '22023';
  end if;
  if not exists (
    select 1 from public.runs r
    where r.id=p_run_id and r.owner_id=v_owner_id
  ) then
    raise exception 'RUN_NOT_FOUND' using errcode = 'P0002';
  end if;

  -- n8n gives a worker at most 150 seconds. A RUNNING task with no update for
  -- three minutes is therefore an abandoned claim, not valid progress.
  update public.orchestration_tasks ot
  set status=case when ot.attempt_count < 3 then 'READY' else 'SAFE_FAILED' end,
      route_reason=case when ot.attempt_count < 3
        then 'STALE_CLAIM_RECOVERED_FOR_RETRY'
        else 'STALE_CLAIM_RETRY_LIMIT_REACHED'
      end,
      completed_at=case when ot.attempt_count < 3 then null else now() end
  where ot.run_id=p_run_id
    and ot.owner_id=v_owner_id
    and ot.status='RUNNING'
    and ot.updated_at < now() - interval '3 minutes';

  return query
  with claimable as (
    select ot.id
    from public.orchestration_tasks ot
    where ot.run_id=p_run_id
      and ot.owner_id=v_owner_id
      and ot.status='READY'
      and ot.module_key=any(p_allowed_modules)
    order by ot.created_at, ot.task_key
    for update skip locked
    limit p_limit
  )
  update public.orchestration_tasks ot
  set status='RUNNING',
      started_at=now(),
      attempt_count=ot.attempt_count+1,
      route_reason='DISPATCHABLE_SCHEDULER_CLAIMED'
  from claimable c
  where ot.id=c.id
  returning ot.*;
end;
$$;

revoke all on function public.claim_dispatchable_orchestration_tasks(uuid,integer,text[]) from public, anon;
grant execute on function public.claim_dispatchable_orchestration_tasks(uuid,integer,text[]) to authenticated;

commit;
