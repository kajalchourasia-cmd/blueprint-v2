-- Blueprint Evidence Dev
-- Migration 021: deterministic Gate 2 plus gate-aware founder resume.

begin;

create or replace function public.persist_execution_readiness(
  p_run_id uuid,
  p_profile_version integer,
  p_completed_modules text[],
  p_required_modules text[],
  p_evidence_coverage numeric,
  p_open_critical_risks jsonb,
  p_explanation text
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_owner_id uuid := auth.uid();
  v_project_id uuid;
  v_state_version integer;
  v_verdict_version integer;
  v_verdict_id uuid;
  v_checkpoint_id uuid;
  v_completion numeric;
  v_score numeric;
  v_verdict text;
  v_decisions text[];
begin
  if v_owner_id is null then raise exception 'AUTHENTICATION_REQUIRED' using errcode='42501'; end if;
  if p_profile_version < 1 then raise exception 'PROFILE_VERSION_INVALID' using errcode='22023'; end if;
  if p_evidence_coverage is null or p_evidence_coverage not between 0 and 1 then
    raise exception 'EVIDENCE_COVERAGE_INVALID' using errcode='22023';
  end if;
  if p_open_critical_risks is null or jsonb_typeof(p_open_critical_risks)<>'array' then
    raise exception 'OPEN_CRITICAL_RISKS_MUST_BE_ARRAY' using errcode='22023';
  end if;
  if coalesce(char_length(p_explanation),0) not between 10 and 4000 then
    raise exception 'READINESS_EXPLANATION_INVALID' using errcode='22023';
  end if;

  select r.project_id,r.state_version into v_project_id,v_state_version
  from public.runs r where r.id=p_run_id and r.owner_id=v_owner_id for update;
  if v_project_id is null then raise exception 'RUN_NOT_FOUND' using errcode='P0002'; end if;

  v_completion := case when cardinality(coalesce(p_required_modules,'{}'::text[]))=0 then 0
    else cardinality(array(select unnest(coalesce(p_completed_modules,'{}'::text[])) intersect select unnest(p_required_modules)))::numeric
      / cardinality(p_required_modules)::numeric end;
  v_score := round(100 * ((v_completion * 0.55) + (p_evidence_coverage * 0.30)
    + (case when jsonb_array_length(p_open_critical_risks)=0 then 0.15 else 0 end)),2);

  if v_completion=1 and p_evidence_coverage>=0.60 and jsonb_array_length(p_open_critical_risks)=0 then
    v_verdict:='READY_FOR_ACTION_BLUEPRINT';
    v_decisions:=array['PROCEED','PAUSE_OR_REVISE'];
  elsif v_completion>=0.60 then
    v_verdict:='CONDITIONAL_READINESS';
    v_decisions:=array['TARGETED_VALIDATION','CONTINUE_ANYWAY','PAUSE_OR_REVISE'];
  else
    v_verdict:='NEEDS_MORE_VALIDATION';
    v_decisions:=array['TARGETED_VALIDATION','PAUSE_OR_REVISE'];
  end if;

  select coalesce(max(verdict_version),0)+1 into v_verdict_version
  from public.stage_verdicts where run_id=p_run_id and gate='EXECUTION_READINESS' and owner_id=v_owner_id;

  insert into public.stage_verdicts(
    owner_id,project_id,run_id,profile_version,verdict_version,stage,gate,verdict,
    score,score_status,dimension_scores,weights,evidence_coverage,requested_streams,
    completed_streams,evidence_ids,critical_blockers,calculation_version,
    decision_capable,route,explanation
  ) values (
    v_owner_id,v_project_id,p_run_id,p_profile_version,v_verdict_version,
    'PROVE_AND_DESIGN','EXECUTION_READINESS',v_verdict,v_score,'DECISION_CAPABLE',
    jsonb_build_object('module_completion',round(v_completion*100,2),'evidence_coverage',round(p_evidence_coverage*100,2),'critical_risk_count',jsonb_array_length(p_open_critical_risks)),
    '{"module_completion":0.55,"evidence_coverage":0.30,"critical_risk_clearance":0.15}'::jsonb,
    p_evidence_coverage,coalesce(p_required_modules,'{}'::text[]),coalesce(p_completed_modules,'{}'::text[]),
    '{}'::uuid[],p_open_critical_risks,'execution-readiness-v1',true,'HUMAN_CHECKPOINT',p_explanation
  ) returning id into v_verdict_id;

  insert into public.human_checkpoints(
    owner_id,project_id,run_id,checkpoint_type,status,proposal_hash,state_version,
    profile_version,payload,available_decisions
  ) values (
    v_owner_id,v_project_id,p_run_id,'STAGE_GATE','PENDING',
    md5(p_run_id::text||':EXECUTION_READINESS:'||v_verdict_version::text),
    greatest(coalesce(v_state_version,1),1),p_profile_version,
    jsonb_build_object('gate','EXECUTION_READINESS','verdict_id',v_verdict_id,'verdict',v_verdict,'score',v_score,
      'evidence_coverage',p_evidence_coverage,'primary_ui_actions',array['REVIEW_STAGE_2_RESULTS','CONTINUE_TO_ACTION_BLUEPRINT']),
    v_decisions
  ) returning id into v_checkpoint_id;

  insert into public.blueprint_stage_progress(owner_id,project_id,run_id,stage,status,completion_percent,section_keys,completed_section_keys,blocked_reason)
  values(v_owner_id,v_project_id,p_run_id,'PROVE_AND_DESIGN','WAITING_FOUNDER',100,
    coalesce(p_required_modules,'{}'::text[]),coalesce(p_completed_modules,'{}'::text[]),'EXECUTION_READINESS_CHECKPOINT')
  on conflict(run_id,stage) do update set status='WAITING_FOUNDER',completion_percent=100,
    section_keys=excluded.section_keys,completed_section_keys=excluded.completed_section_keys,
    blocked_reason='EXECUTION_READINESS_CHECKPOINT',updated_at=now();

  return jsonb_build_object('persisted',true,'gate','EXECUTION_READINESS','verdict_id',v_verdict_id,
    'verdict_version',v_verdict_version,'verdict',v_verdict,'score',v_score,
    'checkpoint_id',v_checkpoint_id,'available_decisions',v_decisions,'route','HUMAN_CHECKPOINT');
end;
$$;

create or replace function public.resolve_founder_checkpoint(
  p_checkpoint_id uuid,
  p_expected_state_version integer,
  p_decision text,
  p_decision_payload jsonb default '{}'::jsonb,
  p_correlation_id text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_owner_id uuid := auth.uid();
  v_checkpoint public.human_checkpoints;
  v_run public.runs;
  v_updated public.runs;
  v_gate text;
  v_target_status text;
  v_target_route text;
  v_planning_mode text;
begin
  if v_owner_id is null then raise exception 'AUTHENTICATION_REQUIRED' using errcode='42501'; end if;
  if p_decision_payload is null or jsonb_typeof(p_decision_payload)<>'object' then raise exception 'DECISION_PAYLOAD_MUST_BE_OBJECT' using errcode='22023'; end if;
  select * into v_checkpoint from public.human_checkpoints h where h.id=p_checkpoint_id and h.owner_id=v_owner_id for update;
  if v_checkpoint.id is null then raise exception 'CHECKPOINT_NOT_FOUND' using errcode='P0002'; end if;
  if v_checkpoint.status='RESOLVED' then
    if v_checkpoint.decision=p_decision then
      select * into v_run from public.runs r where r.id=v_checkpoint.run_id and r.owner_id=v_owner_id;
      return jsonb_build_object('resolved',true,'idempotent',true,'checkpoint_id',v_checkpoint.id,'decision',v_checkpoint.decision,
        'run_id',v_checkpoint.run_id,'state_version',v_run.state_version,'run_status',v_run.status,'route',v_run.current_route);
    end if;
    raise exception 'CHECKPOINT_ALREADY_RESOLVED_WITH_DIFFERENT_DECISION' using errcode='22023';
  end if;
  if v_checkpoint.status<>'PENDING' then raise exception 'CHECKPOINT_NOT_PENDING' using errcode='22023'; end if;
  if not (p_decision=any(v_checkpoint.available_decisions)) then raise exception 'DECISION_NOT_ALLOWED_FOR_CHECKPOINT' using errcode='22023'; end if;
  select * into v_run from public.runs r where r.id=v_checkpoint.run_id and r.owner_id=v_owner_id for update;
  if v_run.state_version<>p_expected_state_version or v_checkpoint.state_version<>p_expected_state_version then
    raise exception 'STALE_CHECKPOINT_STATE expected %, run %, checkpoint %',p_expected_state_version,v_run.state_version,v_checkpoint.state_version using errcode='40001';
  end if;
  v_gate:=coalesce(v_checkpoint.payload->>'gate','RESEARCH_VERDICT');

  if p_decision='RUN_MISSING_RESEARCH' then
    v_target_status:='PLANNING';v_target_route:='TASK_PLANNER';v_planning_mode:='DISCOVER';
  elsif v_gate='EXECUTION_READINESS' and p_decision in ('PROCEED','CONTINUE_ANYWAY') then
    v_target_status:='PLANNING';v_target_route:='STAGE_3_PLAN';v_planning_mode:='COMPLETE_ACTION_BLUEPRINT';
  elsif p_decision in ('PROCEED','CONTINUE_ANYWAY','TARGETED_VALIDATION') then
    v_target_status:='PLANNING';v_target_route:='STAGE_2_PLAN';v_planning_mode:='PROVE_AND_DESIGN';
  elsif p_decision='PAUSE_OR_REVISE' then
    v_target_status:='HUMAN_REVIEW';v_target_route:='HUMAN_REVIEW';v_planning_mode:=null;
  elsif p_decision='CANCEL' then
    v_target_status:='CANCELLED';v_target_route:='CANCEL';v_planning_mode:=null;
  else raise exception 'UNSUPPORTED_STAGE_GATE_DECISION' using errcode='22023'; end if;

  v_updated:=public.advance_run_state(v_run.id,p_expected_state_version,v_target_status,v_target_route,
    jsonb_build_object('actor','FOUNDER','reason_code','FOUNDER_STAGE_GATE_DECISION','current_node','CHECKPOINT_RESOLVED',
      'checkpoint_id',v_checkpoint.id,'gate',v_gate,'decision',p_decision,'correlation_id',left(coalesce(p_correlation_id,''),200)));
  update public.human_checkpoints set status='RESOLVED',decision=p_decision,decision_payload=p_decision_payload,resolved_at=now(),updated_at=now()
    where id=v_checkpoint.id and owner_id=v_owner_id and status='PENDING';
  update public.blueprint_stage_progress set
    status=case when v_planning_mode is not null then 'COMPLETED' else 'WAITING_FOUNDER' end,
    blocked_reason=case when v_planning_mode is not null then null else p_decision end,updated_at=now()
    where run_id=v_run.id and owner_id=v_owner_id and stage=case when v_gate='EXECUTION_READINESS' then 'PROVE_AND_DESIGN' else 'DISCOVER' end;
  return jsonb_build_object('resolved',true,'idempotent',false,'checkpoint_id',v_checkpoint.id,'gate',v_gate,
    'decision',p_decision,'run_id',v_run.id,'run_status',v_updated.status,'state_version',v_updated.state_version,
    'route',v_updated.current_route,'planning_mode',v_planning_mode,'requires_replan',v_planning_mode is not null);
end;
$$;

revoke all on function public.persist_execution_readiness(uuid,integer,text[],text[],numeric,jsonb,text) from public, anon;
grant execute on function public.persist_execution_readiness(uuid,integer,text[],text[],numeric,jsonb,text) to authenticated;
revoke all on function public.resolve_founder_checkpoint(uuid,integer,text,jsonb,text) from public, anon;
grant execute on function public.resolve_founder_checkpoint(uuid,integer,text,jsonb,text) to authenticated;

commit;
