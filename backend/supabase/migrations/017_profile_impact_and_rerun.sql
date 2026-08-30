-- Blueprint Evidence Dev
-- Migration 017: immutable founder-profile edits, deterministic impact previews,
-- explicit human confirmation, and idempotent targeted/full rerun creation.

begin;

create or replace function public.preview_profile_rerun(
  p_project_id uuid,
  p_source_run_id uuid,
  p_target_profile_version integer,
  p_mode text default 'TARGETED',
  p_requested_modules text[] default '{}'::text[],
  p_idempotency_key text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_owner_id uuid := auth.uid();
  v_mode text := upper(btrim(coalesce(p_mode,'TARGETED')));
  v_key text := btrim(coalesce(p_idempotency_key,''));
  v_source_state integer;
  v_source_profile integer;
  v_changed text[];
  v_field text;
  v_modules text[] := '{}'::text[];
  v_uncertain text[] := '{}'::text[];
  v_request public.rerun_requests;
  v_checkpoint public.human_checkpoints;
  v_impact jsonb;
begin
  if v_owner_id is null then
    raise exception 'AUTHENTICATION_REQUIRED' using errcode='42501';
  end if;
  if v_mode not in ('TARGETED','FULL') then
    raise exception 'RERUN_MODE_INVALID' using errcode='22023';
  end if;
  if char_length(v_key) not between 8 and 200 then
    raise exception 'INVALID_IDEMPOTENCY_KEY' using errcode='22023';
  end if;

  select r.state_version into v_source_state
  from public.runs r
  where r.id=p_source_run_id and r.project_id=p_project_id and r.owner_id=v_owner_id
  for share;
  if v_source_state is null then
    raise exception 'SOURCE_RUN_NOT_FOUND' using errcode='P0002';
  end if;

  select pp.changed_fields into v_changed
  from public.project_profiles pp
  where pp.project_id=p_project_id and pp.owner_id=v_owner_id
    and pp.version=p_target_profile_version;
  if v_changed is null then
    raise exception 'TARGET_PROFILE_VERSION_NOT_FOUND' using errcode='P0002';
  end if;

  select coalesce(max(pp.version) filter (where pp.version < p_target_profile_version),1)
    into v_source_profile
  from public.project_profiles pp
  where pp.project_id=p_project_id and pp.owner_id=v_owner_id;

  if v_mode='FULL' then
    v_modules := array[
      'foundation','customer_demand','competitor_intelligence','market_economics',
      'evidence_audit','research_verdict','assumptions_risks','offer_pricing',
      'validation_proof','operating_model','financial_readiness','execution_readiness',
      'launch_distribution','growth_optimization','action_blueprint','final_blueprint'
    ];
  else
    foreach v_field in array coalesce(v_changed,'{}'::text[])
    loop
      v_field := lower(split_part(v_field,'.',1));
      if v_field ~ '^(idea|idea_text|problem|problem_hypothesis|target_customer|customer|industry|optional_industry|geography)$' then
        v_modules := v_modules || array['foundation','customer_demand','competitor_intelligence','market_economics','evidence_audit','research_verdict','final_blueprint'];
      elsif v_field ~ '^(requested_research|research_selection|selected_research)$' then
        v_modules := v_modules || array['customer_demand','competitor_intelligence','market_economics','evidence_audit','research_verdict','final_blueprint'];
      elsif v_field ~ '^(goal|goals|goal_type|success_metric|target_outcome)$' then
        v_modules := v_modules || array['assumptions_risks','offer_pricing','validation_proof','operating_model','financial_readiness','execution_readiness','launch_distribution','growth_optimization','action_blueprint','final_blueprint'];
      elsif v_field ~ '^(budget|available_budget|currency|runway|revenue|pricing|financial_constraints)$' then
        v_modules := v_modules || array['offer_pricing','operating_model','financial_readiness','execution_readiness','action_blueprint','final_blueprint'];
      elsif v_field ~ '^(hours_per_week|time|team|team_size|skills|constraints|current_stage)$' then
        v_modules := v_modules || array['foundation','validation_proof','operating_model','execution_readiness','launch_distribution','action_blueprint','final_blueprint'];
      else
        v_uncertain := array_append(v_uncertain,v_field);
        v_modules := v_modules || array['foundation','customer_demand','competitor_intelligence','market_economics','evidence_audit','research_verdict','final_blueprint'];
      end if;
    end loop;
    v_modules := v_modules || coalesce(p_requested_modules,'{}'::text[]);
  end if;

  select coalesce(array_agg(distinct lower(x) order by lower(x)),'{}'::text[])
    into v_modules from unnest(v_modules) x where btrim(x)<>'';
  select coalesce(array_agg(distinct lower(x) order by lower(x)),'{}'::text[])
    into v_uncertain from unnest(v_uncertain) x where btrim(x)<>'';

  if cardinality(v_modules)=0 then
    v_modules := array['final_blueprint'];
  end if;

  v_impact := jsonb_build_object(
    'schema_version','bp-rerun-impact-v1',
    'changed_fields',coalesce(v_changed,'{}'::text[]),
    'affected_modules',v_modules,
    'uncertain_fields',v_uncertain,
    'requires_human_confirmation',true,
    'source_state_version',v_source_state,
    'explanation',case when cardinality(v_uncertain)>0
      then 'Some changed fields have no narrow dependency rule, so the safe research closure is included.'
      else 'Affected modules were calculated from the declared profile-field dependency map.' end
  );

  select * into v_request from public.rerun_requests
  where owner_id=v_owner_id and idempotency_key=v_key;
  if found then
    if v_request.project_id<>p_project_id or v_request.target_profile_version<>p_target_profile_version then
      raise exception 'IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_SCOPE' using errcode='23505';
    end if;
    select * into v_checkpoint from public.human_checkpoints
      where id=v_request.checkpoint_id and owner_id=v_owner_id;
    return jsonb_build_object('duplicate',true,'rerun_request',to_jsonb(v_request),'checkpoint',to_jsonb(v_checkpoint));
  end if;

  insert into public.rerun_requests(
    owner_id,project_id,source_run_id,source_profile_version,target_profile_version,
    mode,requested_modules,impact,idempotency_key,status
  ) values (
    v_owner_id,p_project_id,p_source_run_id,v_source_profile,p_target_profile_version,
    v_mode,v_modules,v_impact,v_key,'WAITING_CONFIRMATION'
  ) returning * into v_request;

  insert into public.human_checkpoints(
    owner_id,project_id,run_id,checkpoint_type,status,proposal_hash,
    state_version,profile_version,payload,available_decisions
  ) values (
    v_owner_id,p_project_id,p_source_run_id,'RERUN','PENDING','rerun:'||v_request.id::text,
    greatest(v_source_state,1),p_target_profile_version,
    jsonb_build_object('rerun_request_id',v_request.id,'mode',v_mode,'impact',v_impact),
    array['APPROVE','EDIT','CANCEL']
  ) returning * into v_checkpoint;

  update public.rerun_requests set checkpoint_id=v_checkpoint.id
  where id=v_request.id and owner_id=v_owner_id
  returning * into v_request;

  return jsonb_build_object('duplicate',false,'rerun_request',to_jsonb(v_request),'checkpoint',to_jsonb(v_checkpoint));
end;
$$;

create or replace function public.resolve_profile_rerun(
  p_rerun_request_id uuid,
  p_decision text,
  p_expected_source_state_version integer
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_owner_id uuid := auth.uid();
  v_decision text := upper(btrim(coalesce(p_decision,'')));
  v_request public.rerun_requests;
  v_source public.runs;
  v_target public.runs;
  v_profile jsonb;
begin
  if v_owner_id is null then
    raise exception 'AUTHENTICATION_REQUIRED' using errcode='42501';
  end if;
  if v_decision not in ('APPROVE','CANCEL') then
    raise exception 'RERUN_DECISION_INVALID' using errcode='22023';
  end if;

  select * into v_request from public.rerun_requests
  where id=p_rerun_request_id and owner_id=v_owner_id for update;
  if not found then
    raise exception 'RERUN_REQUEST_NOT_FOUND' using errcode='P0002';
  end if;

  if v_request.status='APPROVED' and v_request.target_run_id is not null then
    select * into v_target from public.runs where id=v_request.target_run_id and owner_id=v_owner_id;
    select payload into v_profile from public.project_profiles
      where project_id=v_request.project_id and owner_id=v_owner_id and version=v_request.target_profile_version;
    return jsonb_build_object('duplicate',true,'decision','APPROVE','rerun_request',to_jsonb(v_request),'target_run',to_jsonb(v_target),'profile',v_profile);
  end if;
  if v_request.status not in ('WAITING_CONFIRMATION','PREVIEW') then
    raise exception 'RERUN_REQUEST_NOT_RESOLVABLE' using errcode='P0001';
  end if;

  select * into v_source from public.runs
  where id=v_request.source_run_id and owner_id=v_owner_id for share;
  if not found then
    raise exception 'SOURCE_RUN_NOT_FOUND' using errcode='P0002';
  end if;
  if p_expected_source_state_version is null or v_source.state_version<>p_expected_source_state_version then
    raise exception 'STALE_RERUN_PREVIEW' using errcode='40001';
  end if;

  if v_decision='CANCEL' then
    update public.rerun_requests set status='CANCELLED'
      where id=v_request.id returning * into v_request;
    update public.human_checkpoints set status='CANCELLED',decision='CANCEL',resolved_at=now()
      where id=v_request.checkpoint_id and owner_id=v_owner_id and status='PENDING';
    return jsonb_build_object('duplicate',false,'decision','CANCEL','rerun_request',to_jsonb(v_request),'target_run',null);
  end if;

  insert into public.runs(
    owner_id,project_id,idempotency_key,status,current_route,state_version,
    original_request,deadline_at
  ) values (
    v_owner_id,v_request.project_id,
    'rerun:'||v_request.id::text,'NEW',null,0,
    coalesce(v_source.original_request,'{}'::jsonb) || jsonb_build_object(
      'rerun_request_id',v_request.id,'rerun_mode',v_request.mode,
      'requested_modules',v_request.requested_modules,
      'source_run_id',v_request.source_run_id,
      'source_profile_version',v_request.source_profile_version,
      'profile_version',v_request.target_profile_version
    ),now()+interval '20 minutes'
  ) returning * into v_target;

  update public.rerun_requests set status='APPROVED',target_run_id=v_target.id
    where id=v_request.id returning * into v_request;
  update public.human_checkpoints set status='RESOLVED',decision='APPROVE',resolved_at=now(),
    decision_payload=jsonb_build_object('target_run_id',v_target.id)
    where id=v_request.checkpoint_id and owner_id=v_owner_id and status='PENDING';
  select payload into v_profile from public.project_profiles
    where project_id=v_request.project_id and owner_id=v_owner_id and version=v_request.target_profile_version;

  return jsonb_build_object(
    'duplicate',false,'decision','APPROVE','rerun_request',to_jsonb(v_request),
    'target_run',to_jsonb(v_target),'profile',v_profile
  );
end;
$$;

revoke all on function public.preview_profile_rerun(uuid,uuid,integer,text,text[],text) from public,anon;
revoke all on function public.resolve_profile_rerun(uuid,text,integer) from public,anon;
grant execute on function public.preview_profile_rerun(uuid,uuid,integer,text,text[],text) to authenticated;
grant execute on function public.resolve_profile_rerun(uuid,text,integer) to authenticated;

commit;
