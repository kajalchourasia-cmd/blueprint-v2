-- Blueprint Evidence Dev
-- Migration 014: a single owner-scoped control-panel projection for Streamlit.
-- It deliberately exposes actionable states instead of making the UI infer them.

begin;

create or replace function public.get_founder_control_panel(p_run_id uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, auth
as $$
declare
  v_owner_id uuid := auth.uid();
  v_run public.runs;
begin
  if v_owner_id is null then
    raise exception 'AUTHENTICATION_REQUIRED' using errcode = '42501';
  end if;

  select * into v_run
  from public.runs r
  where r.id=p_run_id and r.owner_id=v_owner_id;

  if v_run.id is null then
    raise exception 'RUN_NOT_FOUND' using errcode = 'P0002';
  end if;

  return jsonb_build_object(
    'schema_version','bp-founder-control-panel-v1',
    'run_id',p_run_id,
    'run_status',v_run.status,
    'current_route',v_run.current_route,
    'blocking',exists(
      select 1 from public.human_checkpoints h
      where h.run_id=p_run_id and h.owner_id=v_owner_id and h.status='PENDING'
    ) or exists(
      select 1 from public.orchestration_tasks t
      where t.run_id=p_run_id and t.owner_id=v_owner_id
        and t.status in ('NEEDS_INPUT','HUMAN_REVIEW','SAFE_FAILED')
    ),
    'summary',jsonb_build_object(
      'completed', (select count(*) from public.orchestration_tasks t where t.run_id=p_run_id and t.owner_id=v_owner_id and t.status in ('COMPLETED','REUSED','NOT_APPLICABLE')),
      'in_progress', (select count(*) from public.orchestration_tasks t where t.run_id=p_run_id and t.owner_id=v_owner_id and t.status in ('READY','RUNNING')),
      'needs_attention', (select count(*) from public.orchestration_tasks t where t.run_id=p_run_id and t.owner_id=v_owner_id and t.status in ('NEEDS_INPUT','HUMAN_REVIEW','PARTIAL','SAFE_FAILED')),
      'pending_approvals', (select count(*) from public.human_checkpoints h where h.run_id=p_run_id and h.owner_id=v_owner_id and h.status='PENDING')
    ),
    'panel_items',coalesce((
      select jsonb_agg(item order by priority, created_at)
      from (
        select
          case
            when t.status='NEEDS_INPUT' then 10
            when t.status='HUMAN_REVIEW' then 20
            when t.status='SAFE_FAILED' then 30
            when t.status='PARTIAL' then 40
            when t.status='RUNNING' then 70
            else 80
          end as priority,
          t.updated_at as created_at,
          jsonb_build_object(
            'item_id','task:'||t.id::text,
            'item_type',case
              when t.status='NEEDS_INPUT' then 'NEEDS_INPUT'
              when t.observation_verdict='CONTRADICTORY' then 'CONTRADICTION'
              when t.observation_verdict='TOOL_FAILED' then 'TOOL_FAILURE'
              when t.status in ('HUMAN_REVIEW','SAFE_FAILED') then 'HUMAN_REVIEW'
              else 'TASK_STATUS'
            end,
            'severity',case when t.status in ('SAFE_FAILED','HUMAN_REVIEW') then 'HIGH' when t.status in ('NEEDS_INPUT','PARTIAL') then 'MEDIUM' else 'INFO' end,
            'blocking',t.status in ('NEEDS_INPUT','HUMAN_REVIEW','SAFE_FAILED'),
            'title',case
              when t.status='NEEDS_INPUT' then 'Founder input needed: '||replace(t.module_key,'_',' ')
              when t.observation_verdict='CONTRADICTORY' then 'Contradictory evidence needs a decision'
              when t.observation_verdict='TOOL_FAILED' then 'A research tool failed'
              when t.status='SAFE_FAILED' then 'Task stopped safely'
              when t.status='PARTIAL' then 'Partial result available'
              when t.status='RUNNING' then 'Research in progress'
              else 'Ready to run'
            end,
            'message',coalesce(o.summary,t.route_reason,t.goal),
            'task_id',t.id,
            'task_key',t.task_key,
            'module_key',t.module_key,
            'task_status',t.status,
            'observation_verdict',t.observation_verdict,
            'limitations',coalesce(o.limitations,'[]'::jsonb),
            'allowed_decisions',case
              when t.status='NEEDS_INPUT' then jsonb_build_array('MORE_INFORMATION','CANCEL')
              when t.observation_verdict='CONTRADICTORY' then jsonb_build_array('MORE_INFORMATION','OVERRIDE','PAUSE_OR_REVISE')
              when t.observation_verdict='TOOL_FAILED' then jsonb_build_array('RETRY','CONTINUE_ANYWAY','PAUSE_OR_REVISE')
              when t.status in ('HUMAN_REVIEW','SAFE_FAILED') then jsonb_build_array('RETRY','REQUEST_CHANGES','CANCEL')
              when t.status='PARTIAL' then jsonb_build_array('RETRY','CONTINUE_ANYWAY')
              else '[]'::jsonb
            end,
            'next_route',case
              when t.status='NEEDS_INPUT' then 'FOUNDER_INPUT'
              when t.status in ('HUMAN_REVIEW','SAFE_FAILED') then 'HUMAN_REVIEW'
              when t.status='PARTIAL' then 'PARTIAL_COMPLETE'
              when t.status='READY' then 'TASK_SCHEDULER'
              else 'SUPERVISOR_REEVALUATE'
            end,
            'updated_at',t.updated_at
          ) as item
        from public.orchestration_tasks t
        left join lateral (
          select x.summary,x.limitations
          from public.task_observations x
          where x.task_id=t.id and x.owner_id=v_owner_id
          order by x.created_at desc limit 1
        ) o on true
        where t.run_id=p_run_id and t.owner_id=v_owner_id
          and t.status in ('NEEDS_INPUT','HUMAN_REVIEW','PARTIAL','SAFE_FAILED','READY','RUNNING')

        union all

        select
          5 as priority,
          h.created_at,
          jsonb_build_object(
            'item_id','checkpoint:'||h.id::text,
            'item_type','HUMAN_CHECKPOINT',
            'severity','HIGH',
            'blocking',true,
            'title',case when h.checkpoint_type='STAGE_GATE' then 'Research verdict ready for your decision' else 'Your review is required' end,
            'message',coalesce(h.payload->>'explanation','Review the evidence and select one permitted decision.'),
            'checkpoint_id',h.id,
            'checkpoint_type',h.checkpoint_type,
            'payload',h.payload,
            'allowed_decisions',to_jsonb(h.available_decisions),
            'state_version',h.state_version,
            'profile_version',h.profile_version,
            'next_route','HITL_RESUME',
            'created_at',h.created_at
          ) as item
        from public.human_checkpoints h
        where h.run_id=p_run_id and h.owner_id=v_owner_id and h.status='PENDING'
      ) q
    ),'[]'::jsonb),
    'latest_verdict',(
      select jsonb_build_object(
        'id',sv.id,'gate',sv.gate,'verdict',sv.verdict,'score',sv.score,
        'score_status',sv.score_status,'decision_capable',sv.decision_capable,
        'evidence_coverage',sv.evidence_coverage,'explanation',sv.explanation,
        'created_at',sv.created_at
      )
      from public.stage_verdicts sv
      where sv.run_id=p_run_id and sv.owner_id=v_owner_id
      order by sv.created_at desc limit 1
    )
  );
end;
$$;

revoke all on function public.get_founder_control_panel(uuid) from public, anon;
grant execute on function public.get_founder_control_panel(uuid) to authenticated;

commit;
