-- Blueprint Evidence Dev
-- Migration 019: make authenticated start the canonical dynamic-orchestration entry point.
-- A start now creates immutable founder truth plus Original Blueprint V0, and
-- exposes an idempotent state preparation RPC for the bounded supervisor.

begin;

insert into public.allowed_run_transitions(from_status,to_status) values
  ('NEW','PLANNING')
on conflict do nothing;

create or replace function public.start_blueprint_run(
  p_idempotency_key text,
  p_idea_text text,
  p_optional_industry text default null,
  p_geography text default null,
  p_constraints jsonb default '{}'::jsonb,
  p_original_request jsonb default '{}'::jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  caller_id uuid := auth.uid();
  created_project public.projects%rowtype;
  created_run public.runs%rowtype;
  profile_row public.project_profiles%rowtype;
  original_blueprint_row public.blueprint_versions%rowtype;
  profile_payload jsonb;
  was_duplicate boolean := false;
begin
  if caller_id is null then
    raise exception 'AUTHENTICATION_REQUIRED' using errcode = '28000';
  end if;

  p_idempotency_key := btrim(coalesce(p_idempotency_key, ''));
  p_idea_text := btrim(coalesce(p_idea_text, ''));
  p_optional_industry := nullif(btrim(p_optional_industry), '');
  p_geography := nullif(btrim(p_geography), '');
  p_constraints := coalesce(p_constraints, '{}'::jsonb);
  p_original_request := coalesce(p_original_request, '{}'::jsonb);

  if char_length(p_idempotency_key) not between 8 and 200 then
    raise exception 'INVALID_IDEMPOTENCY_KEY' using errcode = '22023';
  end if;
  if char_length(p_idea_text) not between 10 and 10000 then
    raise exception 'INVALID_IDEA_TEXT' using errcode = '22023';
  end if;
  if p_optional_industry is not null and char_length(p_optional_industry) > 200 then
    raise exception 'INVALID_INDUSTRY' using errcode = '22023';
  end if;
  if p_geography is not null and char_length(p_geography) > 200 then
    raise exception 'INVALID_GEOGRAPHY' using errcode = '22023';
  end if;
  if jsonb_typeof(p_constraints) <> 'object' or jsonb_typeof(p_original_request) <> 'object' then
    raise exception 'INVALID_JSON_OBJECT' using errcode = '22023';
  end if;

  select r.* into created_run
  from public.runs r
  where r.owner_id = caller_id and r.idempotency_key = p_idempotency_key;

  if found then
    select p.* into created_project
    from public.projects p
    where p.id = created_run.project_id and p.owner_id = caller_id;
    was_duplicate := true;
  else
    begin
      insert into public.projects(owner_id,idea_text,optional_industry,geography,constraints)
      values (caller_id,p_idea_text,p_optional_industry,p_geography,p_constraints)
      returning * into created_project;

      insert into public.runs(owner_id,project_id,idempotency_key,original_request,deadline_at)
      values (caller_id,created_project.id,p_idempotency_key,p_original_request,now()+interval '20 minutes')
      returning * into created_run;
    exception when unique_violation then
      select r.* into created_run
      from public.runs r
      where r.owner_id=caller_id and r.idempotency_key=p_idempotency_key;
      if not found then raise; end if;
      select p.* into created_project
      from public.projects p
      where p.id=created_run.project_id and p.owner_id=caller_id;
      was_duplicate := true;
    end;
  end if;

  select * into profile_row
  from public.project_profiles pp
  where pp.project_id=created_project.id and pp.owner_id=caller_id
  order by pp.version asc limit 1;

  if profile_row.id is null then
    profile_payload := jsonb_build_object(
      'idea_text', created_project.idea_text,
      'optional_industry', created_project.optional_industry,
      'geography', created_project.geography,
      'constraints', created_project.constraints,
      'requested_research', coalesce(p_original_request->'requested_research',p_constraints->'requested_research','[]'::jsonb),
      'goal', coalesce(p_constraints->>'goal',p_original_request->>'goal'),
      'onboarding', p_original_request,
      'source', 'AUTHENTICATED_START'
    );
    profile_row := public.create_project_profile_version(
      created_project.id,
      profile_payload,
      array['idea_text','optional_industry','geography','constraints','requested_research','goal'],
      'Initial authenticated founder onboarding',
      created_run.id
    );
  end if;

  select * into original_blueprint_row
  from public.blueprint_versions bv
  where bv.run_id=created_run.id and bv.owner_id=caller_id and bv.version_kind='ORIGINAL'
  order by bv.version asc limit 1;

  if original_blueprint_row.id is null then
    original_blueprint_row := public.create_progressive_blueprint_version(
      created_run.id,
      profile_row.version,
      'ORIGINAL',
      'ONBOARDING',
      'UNRESEARCHED',
      jsonb_build_object(
        'schema_version','bp-original-blueprint-v1',
        'product_idea',created_project.idea_text,
        'starting_position',profile_row.payload,
        'requested_research',coalesce(profile_row.payload->'requested_research','[]'::jsonb),
        'stages',jsonb_build_array(
          jsonb_build_object('stage','DISCOVER','status','PLANNED'),
          jsonb_build_object('stage','PROVE_AND_DESIGN','status','PLANNED'),
          jsonb_build_object('stage','ACTION_BLUEPRINT','status','PLANNED')
        )
      ),
      'Original onboarding blueprint before autonomous research',
      '{}'::uuid[]
    );
  end if;

  return jsonb_build_object(
    'project_id',created_project.id,
    'run_id',created_run.id,
    'status',created_run.status,
    'state_version',created_run.state_version,
    'profile_version',profile_row.version,
    'original_blueprint_version',original_blueprint_row.version,
    'created_at',created_run.created_at,
    'duplicate',was_duplicate
  );
end;
$$;

create or replace function public.prepare_dynamic_run(p_run_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_owner_id uuid := auth.uid();
  v_run public.runs;
  v_task_count integer;
begin
  if v_owner_id is null then
    raise exception 'AUTHENTICATION_REQUIRED' using errcode='42501';
  end if;

  select * into v_run
  from public.runs r
  where r.id=p_run_id and r.owner_id=v_owner_id
  for update;
  if v_run.id is null then
    raise exception 'RUN_NOT_FOUND' using errcode='P0002';
  end if;

  if v_run.status='NEW' then
    v_run := public.advance_run_state(
      v_run.id,v_run.state_version,'PLANNING','TASK_PLANNER',
      jsonb_build_object('actor','SUPERVISOR','reason_code','CANONICAL_DYNAMIC_START','current_node','BP-00 Dynamic Supervisor')
    );
  elsif v_run.status='FRAMING' then
    v_run := public.advance_run_state(
      v_run.id,v_run.state_version,'PLANNING','TASK_PLANNER',
      jsonb_build_object('actor','SUPERVISOR','reason_code','RESUME_AFTER_FRAMING','current_node','BP-00 Dynamic Supervisor')
    );
  end if;

  select count(*) into v_task_count
  from public.orchestration_tasks t
  where t.run_id=v_run.id and t.owner_id=v_owner_id and t.status<>'CANCELLED';

  return jsonb_build_object(
    'prepared',true,
    'run',to_jsonb(v_run),
    'task_count',v_task_count,
    'should_plan',v_task_count=0 and v_run.status='PLANNING',
    'terminal',v_run.status in ('COMPLETED','PARTIAL','SAFE_FAILED','CANCELLED'),
    'waiting_for_human',v_run.status in ('WAITING_APPROVAL','HUMAN_REVIEW','NEEDS_INPUT')
  );
end;
$$;

revoke all on function public.start_blueprint_run(text,text,text,text,jsonb,jsonb) from public,anon;
grant execute on function public.start_blueprint_run(text,text,text,text,jsonb,jsonb) to authenticated;
revoke all on function public.prepare_dynamic_run(uuid) from public,anon;
grant execute on function public.prepare_dynamic_run(uuid) to authenticated;

comment on function public.start_blueprint_run(text,text,text,text,jsonb,jsonb) is
'Idempotently creates the owner-scoped project, run, immutable profile v1, and Original Blueprint v1 used by the canonical dynamic supervisor.';

commit;
