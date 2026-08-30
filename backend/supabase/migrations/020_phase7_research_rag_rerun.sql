-- Blueprint Evidence Dev
-- Migration 020: retrieval context for "Ask this Research" plus an atomic,
-- human-approved research-rerun preview contract.

begin;

create or replace function public.get_supervisor_context(p_run_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_owner_id uuid := auth.uid();
  result jsonb;
begin
  if v_owner_id is null then
    raise exception 'AUTH_REQUIRED' using errcode='42501';
  end if;

  select jsonb_build_object(
    'run',to_jsonb(r),
    'project',to_jsonb(p),
    'context',coalesce(to_jsonb(rc),'{}'::jsonb),
    'sections',coalesce((select jsonb_agg(to_jsonb(bs) order by bs.section_key)
      from public.blueprint_sections bs where bs.run_id=r.id and bs.owner_id=v_owner_id),'[]'::jsonb),
    'orchestration_tasks',coalesce((select jsonb_agg(jsonb_build_object(
      'task_key',t.task_key,'module_key',t.module_key,'status',t.status,
      'observation_verdict',t.observation_verdict,'route_reason',t.route_reason,
      'output',t.output,'updated_at',t.updated_at
    ) order by t.created_at) from public.orchestration_tasks t
      where t.run_id=r.id and t.owner_id=v_owner_id),'[]'::jsonb),
    'current_blueprint',(select to_jsonb(bv) from public.blueprint_versions bv
      where bv.run_id=r.id and bv.owner_id=v_owner_id order by bv.version desc limit 1),
    'latest_verdict',(select to_jsonb(sv) from public.stage_verdicts sv
      where sv.run_id=r.id and sv.owner_id=v_owner_id order by sv.created_at desc limit 1),
    'next_actions',coalesce((select jsonb_agg(to_jsonb(a) order by a.priority,a.created_at)
      from public.next_actions a where a.run_id=r.id and a.owner_id=v_owner_id
      and a.status in ('OPEN','IN_PROGRESS','BLOCKED')),'[]'::jsonb),
    'accepted_evidence',coalesce((select jsonb_agg(to_jsonb(e) order by e.created_at desc)
      from public.evidence e where e.run_id=r.id and e.owner_id=v_owner_id
      and e.auditor_verdict in ('ACCEPT','ACCEPT_WITH_LIMITATION')),'[]'::jsonb),
    'quality_checks',coalesce((select jsonb_agg(to_jsonb(q) order by q.created_at desc)
      from public.quality_checks q where q.run_id=r.id and q.owner_id=v_owner_id),'[]'::jsonb),
    'approvals',coalesce((select jsonb_agg(to_jsonb(a) order by a.created_at desc)
      from public.approvals a where a.run_id=r.id and a.owner_id=v_owner_id),'[]'::jsonb),
    'errors',coalesce((select jsonb_agg(to_jsonb(er) order by er.created_at desc)
      from public.errors er where er.run_id=r.id and er.owner_id=v_owner_id),'[]'::jsonb),
    'commands',coalesce((select jsonb_agg(to_jsonb(ac) order by ac.created_at desc)
      from public.agent_commands ac where ac.run_id=r.id and ac.owner_id=v_owner_id),'[]'::jsonb),
    'transitions',coalesce((select jsonb_agg(to_jsonb(st) order by st.state_version)
      from public.state_transitions st where st.run_id=r.id and st.owner_id=v_owner_id),'[]'::jsonb)
  ) into result
  from public.runs r
  join public.projects p on p.id=r.project_id and p.owner_id=r.owner_id
  left join public.run_contexts rc on rc.run_id=r.id and rc.owner_id=r.owner_id
  where r.id=p_run_id and r.owner_id=v_owner_id;

  if result is null then
    raise exception 'RUN_NOT_FOUND_OR_FORBIDDEN' using errcode='P0002';
  end if;
  return result;
end;
$$;

create or replace function public.preview_research_rerun(
  p_project_id uuid,
  p_source_run_id uuid,
  p_target_module text,
  p_idempotency_key text
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_owner_id uuid := auth.uid();
  v_target text := lower(btrim(coalesce(p_target_module,'')));
  v_profile public.project_profiles;
  v_new_profile public.project_profiles;
  v_payload jsonb;
begin
  if v_owner_id is null then
    raise exception 'AUTHENTICATION_REQUIRED' using errcode='42501';
  end if;
  if v_target not in ('customer_demand','competitor_intelligence','market_economics') then
    raise exception 'RESEARCH_RERUN_MODULE_INVALID' using errcode='22023';
  end if;
  if not exists(select 1 from public.runs r where r.id=p_source_run_id and r.project_id=p_project_id and r.owner_id=v_owner_id) then
    raise exception 'SOURCE_RUN_NOT_FOUND' using errcode='P0002';
  end if;

  select * into v_profile from public.project_profiles pp
  where pp.project_id=p_project_id and pp.owner_id=v_owner_id
  order by pp.version desc limit 1;
  if v_profile.id is null then
    raise exception 'FOUNDER_PROFILE_NOT_FOUND' using errcode='P0002';
  end if;

  -- Replaying the same preview key must not mint additional profile versions.
  if exists(select 1 from public.rerun_requests rr where rr.owner_id=v_owner_id and rr.idempotency_key=p_idempotency_key) then
    return public.preview_profile_rerun(
      p_project_id,p_source_run_id,
      (select rr.target_profile_version from public.rerun_requests rr where rr.owner_id=v_owner_id and rr.idempotency_key=p_idempotency_key),
      'TARGETED',array[v_target],p_idempotency_key
    );
  end if;

  v_payload := v_profile.payload || jsonb_build_object(
    'requested_research',jsonb_build_array(v_target),
    'rerun_reason','FOUNDER_REQUESTED_RESEARCH_REFRESH',
    'rerun_source_run_id',p_source_run_id
  );
  v_new_profile := public.create_project_profile_version(
    p_project_id,v_payload,array['requested_research'],
    'Founder requested a fresh '||replace(v_target,'_',' ')||' research run',p_source_run_id
  );

  return public.preview_profile_rerun(
    p_project_id,p_source_run_id,v_new_profile.version,
    'TARGETED',array[v_target],p_idempotency_key
  );
end;
$$;

revoke all on function public.get_supervisor_context(uuid) from public,anon;
grant execute on function public.get_supervisor_context(uuid) to authenticated;
revoke all on function public.preview_research_rerun(uuid,uuid,text,text) from public,anon;
grant execute on function public.preview_research_rerun(uuid,uuid,text,text) to authenticated;

commit;
