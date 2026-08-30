-- Blueprint Evidence Dev
-- Migration 015: stage-gate waiting state plus idempotent, stale-safe founder resume.

begin;

insert into public.allowed_run_transitions(from_status,to_status) values
  ('RESEARCHING','WAITING_APPROVAL'),
  ('AUDITING','WAITING_APPROVAL'),
  ('PLANNING','PLANNING')
on conflict do nothing;

create or replace function public.enter_stage_gate_wait()
returns trigger
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_run public.runs;
  v_updated public.runs;
begin
  if new.checkpoint_type <> 'STAGE_GATE' or new.status <> 'PENDING' then
    return new;
  end if;

  select * into v_run
  from public.runs r
  where r.id=new.run_id and r.owner_id=new.owner_id
  for update;

  if v_run.id is null then
    raise exception 'RUN_NOT_FOUND' using errcode='P0002';
  end if;

  if v_run.status='WAITING_APPROVAL' then
    new.state_version := greatest(v_run.state_version,1);
    return new;
  end if;

  if not exists (
    select 1 from public.allowed_run_transitions a
    where a.from_status=v_run.status and a.to_status='WAITING_APPROVAL'
  ) then
    raise exception 'RUN_CANNOT_ENTER_STAGE_GATE_FROM_%',v_run.status using errcode='22023';
  end if;

  v_updated := public.advance_run_state(
    v_run.id,
    v_run.state_version,
    'WAITING_APPROVAL',
    'HUMAN_REVIEW',
    jsonb_build_object(
      'actor','SYSTEM',
      'reason_code','STAGE_GATE_CREATED',
      'current_node','PENDING_FOUNDER_DECISION'
    )
  );
  new.state_version := v_updated.state_version;
  return new;
end;
$$;

drop trigger if exists human_checkpoints_enter_stage_gate_wait on public.human_checkpoints;
create trigger human_checkpoints_enter_stage_gate_wait
before insert on public.human_checkpoints
for each row execute function public.enter_stage_gate_wait();

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
  v_target_status text;
  v_target_route text;
  v_planning_mode text;
begin
  if v_owner_id is null then
    raise exception 'AUTHENTICATION_REQUIRED' using errcode='42501';
  end if;
  if p_decision_payload is null or jsonb_typeof(p_decision_payload)<>'object' then
    raise exception 'DECISION_PAYLOAD_MUST_BE_OBJECT' using errcode='22023';
  end if;

  select * into v_checkpoint
  from public.human_checkpoints h
  where h.id=p_checkpoint_id and h.owner_id=v_owner_id
  for update;

  if v_checkpoint.id is null then
    raise exception 'CHECKPOINT_NOT_FOUND' using errcode='P0002';
  end if;

  if v_checkpoint.status='RESOLVED' then
    if v_checkpoint.decision=p_decision then
      select * into v_run from public.runs r where r.id=v_checkpoint.run_id and r.owner_id=v_owner_id;
      return jsonb_build_object(
        'resolved',true,'idempotent',true,'checkpoint_id',v_checkpoint.id,
        'decision',v_checkpoint.decision,'run_id',v_checkpoint.run_id,
        'state_version',v_run.state_version,'run_status',v_run.status,
        'route',v_run.current_route
      );
    end if;
    raise exception 'CHECKPOINT_ALREADY_RESOLVED_WITH_DIFFERENT_DECISION' using errcode='22023';
  end if;

  if v_checkpoint.status<>'PENDING' then
    raise exception 'CHECKPOINT_NOT_PENDING' using errcode='22023';
  end if;
  if not (p_decision=any(v_checkpoint.available_decisions)) then
    raise exception 'DECISION_NOT_ALLOWED_FOR_CHECKPOINT' using errcode='22023';
  end if;

  select * into v_run
  from public.runs r
  where r.id=v_checkpoint.run_id and r.owner_id=v_owner_id
  for update;

  if v_run.state_version<>p_expected_state_version
     or v_checkpoint.state_version<>p_expected_state_version then
    raise exception 'STALE_CHECKPOINT_STATE expected %, run %, checkpoint %',
      p_expected_state_version,v_run.state_version,v_checkpoint.state_version
      using errcode='40001';
  end if;

  if p_decision='RUN_MISSING_RESEARCH' then
    v_target_status:='PLANNING'; v_target_route:='TASK_PLANNER'; v_planning_mode:='DISCOVER';
  elsif p_decision in ('PROCEED','CONTINUE_ANYWAY','TARGETED_VALIDATION') then
    v_target_status:='PLANNING'; v_target_route:='STAGE_2_PLAN'; v_planning_mode:='PROVE_AND_DESIGN';
  elsif p_decision='PAUSE_OR_REVISE' then
    v_target_status:='HUMAN_REVIEW'; v_target_route:='HUMAN_REVIEW'; v_planning_mode:=null;
  elsif p_decision='CANCEL' then
    v_target_status:='CANCELLED'; v_target_route:='CANCEL'; v_planning_mode:=null;
  else
    raise exception 'UNSUPPORTED_STAGE_GATE_DECISION' using errcode='22023';
  end if;

  v_updated := public.advance_run_state(
    v_run.id,
    p_expected_state_version,
    v_target_status,
    v_target_route,
    jsonb_build_object(
      'actor','FOUNDER',
      'reason_code','FOUNDER_STAGE_GATE_DECISION',
      'current_node','CHECKPOINT_RESOLVED',
      'checkpoint_id',v_checkpoint.id,
      'decision',p_decision,
      'correlation_id',left(coalesce(p_correlation_id,''),200)
    )
  );

  update public.human_checkpoints
  set status='RESOLVED',decision=p_decision,decision_payload=p_decision_payload,
      resolved_at=now(),updated_at=now()
  where id=v_checkpoint.id and owner_id=v_owner_id and status='PENDING';

  update public.blueprint_stage_progress
  set status=case when p_decision='RUN_MISSING_RESEARCH' then 'IN_PROGRESS'
                  when p_decision in ('PROCEED','CONTINUE_ANYWAY','TARGETED_VALIDATION') then 'COMPLETED'
                  else 'WAITING_FOUNDER' end,
      blocked_reason=case when p_decision in ('PROCEED','CONTINUE_ANYWAY','TARGETED_VALIDATION') then null else p_decision end,
      updated_at=now()
  where run_id=v_run.id and owner_id=v_owner_id and stage='DISCOVER';

  return jsonb_build_object(
    'resolved',true,'idempotent',false,'checkpoint_id',v_checkpoint.id,
    'decision',p_decision,'run_id',v_run.id,'run_status',v_updated.status,
    'state_version',v_updated.state_version,'route',v_updated.current_route,
    'planning_mode',v_planning_mode,'requires_replan',v_planning_mode is not null
  );
end;
$$;

revoke all on function public.resolve_founder_checkpoint(uuid,integer,text,jsonb,text) from public, anon;
grant execute on function public.resolve_founder_checkpoint(uuid,integer,text,jsonb,text) to authenticated;

commit;
