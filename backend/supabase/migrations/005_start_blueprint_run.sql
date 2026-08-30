-- Blueprint Evidence Dev
-- Migration 005: authenticated, atomic, idempotent run creation.

begin;

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
set search_path = public, auth
as $$
declare
  caller_id uuid := auth.uid();
  created_project public.projects%rowtype;
  created_run public.runs%rowtype;
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
  where r.owner_id = caller_id
    and r.idempotency_key = p_idempotency_key;

  if found then
    select p.* into created_project
    from public.projects p
    where p.id = created_run.project_id
      and p.owner_id = caller_id;
    was_duplicate := true;
  else
    begin
      insert into public.projects (
        owner_id, idea_text, optional_industry, geography, constraints
      ) values (
        caller_id, p_idea_text, p_optional_industry, p_geography, p_constraints
      )
      returning * into created_project;

      insert into public.runs (
        owner_id, project_id, idempotency_key, original_request, deadline_at
      ) values (
        caller_id,
        created_project.id,
        p_idempotency_key,
        p_original_request,
        now() + interval '20 minutes'
      )
      returning * into created_run;
    exception
      when unique_violation then
        select r.* into created_run
        from public.runs r
        where r.owner_id = caller_id
          and r.idempotency_key = p_idempotency_key;

        if not found then
          raise;
        end if;

        select p.* into created_project
        from public.projects p
        where p.id = created_run.project_id
          and p.owner_id = caller_id;
        was_duplicate := true;
    end;
  end if;

  return jsonb_build_object(
    'project_id', created_project.id,
    'run_id', created_run.id,
    'status', created_run.status,
    'state_version', created_run.state_version,
    'created_at', created_run.created_at,
    'duplicate', was_duplicate
  );
end;
$$;

revoke all on function public.start_blueprint_run(text, text, text, text, jsonb, jsonb)
from public, anon;
grant execute on function public.start_blueprint_run(text, text, text, text, jsonb, jsonb)
to authenticated;

comment on function public.start_blueprint_run(text, text, text, text, jsonb, jsonb) is
'Creates one owner-scoped project and NEW run atomically. Replays return the original run by owner plus idempotency key.';

commit;
