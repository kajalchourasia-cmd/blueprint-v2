-- Blueprint Evidence Dev
-- Migration 016: canonical accepted-evidence persistence plus rebuildable
-- Pinecone/Mem0 projection tracking and owner-scoped retrieval revalidation.

begin;

create or replace function public.persist_audited_stage1_evidence(
  p_run_id uuid,
  p_profile_version integer,
  p_audit_status text,
  p_items jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_owner_id uuid := auth.uid();
  v_project_id uuid;
  v_item jsonb;
  v_url text;
  v_excerpt text;
  v_hash text;
  v_provider text;
  v_source_type text;
  v_row public.evidence;
  v_rows jsonb := '[]'::jsonb;
begin
  if v_owner_id is null then
    raise exception 'AUTHENTICATION_REQUIRED' using errcode='42501';
  end if;
  if upper(coalesce(p_audit_status,'')) <> 'PASS' then
    raise exception 'ONLY_PASSED_AUDIT_EVIDENCE_CAN_BE_ACCEPTED' using errcode='22023';
  end if;
  if p_items is null or jsonb_typeof(p_items)<>'array' or jsonb_array_length(p_items)>50 then
    raise exception 'EVIDENCE_BATCH_INVALID' using errcode='22023';
  end if;

  select r.project_id into v_project_id
  from public.runs r where r.id=p_run_id and r.owner_id=v_owner_id;
  if v_project_id is null then
    raise exception 'RUN_NOT_FOUND' using errcode='P0002';
  end if;
  if not exists (
    select 1 from public.project_profiles pp
    where pp.project_id=v_project_id and pp.owner_id=v_owner_id and pp.version=p_profile_version
  ) then
    raise exception 'PROFILE_VERSION_NOT_FOUND' using errcode='P0002';
  end if;

  for v_item in select value from jsonb_array_elements(p_items) loop
    v_url := nullif(btrim(v_item->>'source_url'),'');
    v_excerpt := nullif(btrim(v_item->>'excerpt'),'');
    if v_url !~* '^https://' or coalesce(char_length(v_excerpt),0)<5 then
      continue;
    end if;
    v_hash := md5(v_url||'|'||v_excerpt);
    v_provider := upper(coalesce(v_item->>'provider','YOU'));
    if v_provider not in ('YOU','TAVILY','FIRECRAWL','DIRECT','FOUNDER','OTHER') then v_provider:='OTHER'; end if;
    v_source_type := case
      when v_url ~* '(reddit\.com|quora\.com)' then 'COMMUNITY'
      when v_url ~* '(g2\.com|capterra\.com|trustpilot\.com)' then 'REVIEW'
      else 'OTHER'
    end;

    insert into public.evidence(
      owner_id,project_id,run_id,claim,stance,source_url,source_title,
      source_domain,source_type,retrieved_at,excerpt,query,provider,
      content_hash,limitations,auditor_verdict
    ) values (
      v_owner_id,v_project_id,p_run_id,left(v_excerpt,8000),'NEUTRAL',v_url,
      left(coalesce(v_item->>'source_title','Untitled source'),1000),
      lower(coalesce(substring(v_url from '^https://([^/]+)'),'unknown.invalid')),
      v_source_type,now(),left(v_excerpt,12000),left(v_item->>'query',2000),v_provider,
      v_hash,
      case when jsonb_typeof(v_item->'limitations')='array' then v_item->'limitations'
           else jsonb_build_array('Search excerpt accepted with limitation after independent audit.') end,
      'ACCEPT_WITH_LIMITATION'
    ) on conflict do nothing
    returning * into v_row;

    if v_row.id is null then
      select * into v_row from public.evidence e
      where e.project_id=v_project_id and e.owner_id=v_owner_id
        and e.content_hash=v_hash and e.hypothesis_id is null
      order by e.created_at desc limit 1;
    end if;
    if v_row.id is not null then
      v_rows := v_rows || jsonb_build_array(jsonb_build_object(
        'id',v_row.id,'project_id',v_row.project_id,'run_id',v_row.run_id,
        'claim',v_row.claim,'source_url',v_row.source_url,'source_title',v_row.source_title,
        'source_type',v_row.source_type,'provider',v_row.provider,
        'content_hash',v_row.content_hash,'limitations',v_row.limitations,
        'auditor_verdict',v_row.auditor_verdict,
        'module_key',v_item->>'module_key'
      ));
    end if;
    v_row := null;
  end loop;

  return jsonb_build_object('persisted',true,'project_id',v_project_id,'run_id',p_run_id,
    'accepted_count',jsonb_array_length(v_rows),'accepted_evidence',v_rows);
end;
$$;

create or replace function public.get_pinecone_projection_batch(p_run_id uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, auth
as $$
declare
  v_owner_id uuid := auth.uid();
  v_project_id uuid;
begin
  if v_owner_id is null then raise exception 'AUTHENTICATION_REQUIRED' using errcode='42501'; end if;
  select r.project_id into v_project_id from public.runs r where r.id=p_run_id and r.owner_id=v_owner_id;
  if v_project_id is null then raise exception 'RUN_NOT_FOUND' using errcode='P0002'; end if;
  return jsonb_build_object(
    'owner_id',v_owner_id,'project_id',v_project_id,'run_id',p_run_id,
    'namespace','bp-'||v_owner_id::text||'-'||v_project_id::text,
    'records',coalesce((select jsonb_agg(jsonb_build_object(
      'external_id','ev:'||e.id::text,'evidence_id',e.id,'chunk_text',e.claim,
      'source_url',e.source_url,'source_title',e.source_title,'source_type',e.source_type,
      'provider',e.provider,'content_hash',e.content_hash,'auditor_verdict',e.auditor_verdict,
      'run_id',e.run_id,'project_id',e.project_id,'owner_id',e.owner_id
    ) order by e.created_at)
    from public.evidence e
    where e.run_id=p_run_id and e.owner_id=v_owner_id
      and e.auditor_verdict in ('ACCEPT','ACCEPT_WITH_LIMITATION')),'[]'::jsonb)
  );
end;
$$;

create or replace function public.upsert_memory_projection_batch(
  p_project_id uuid,
  p_run_id uuid,
  p_provider text,
  p_records jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_owner_id uuid := auth.uid();
  v_provider text := upper(coalesce(p_provider,''));
  v_item jsonb;
  v_count integer := 0;
begin
  if v_owner_id is null then raise exception 'AUTHENTICATION_REQUIRED' using errcode='42501'; end if;
  if v_provider not in ('PINECONE','MEM0') then raise exception 'PROJECTION_PROVIDER_INVALID' using errcode='22023'; end if;
  if p_records is null or jsonb_typeof(p_records)<>'array' or jsonb_array_length(p_records)>100 then
    raise exception 'PROJECTION_BATCH_INVALID' using errcode='22023';
  end if;
  if not exists(select 1 from public.projects p where p.id=p_project_id and p.owner_id=v_owner_id) then
    raise exception 'PROJECT_NOT_FOUND' using errcode='P0002';
  end if;
  if p_run_id is not null and not exists(select 1 from public.runs r where r.id=p_run_id and r.project_id=p_project_id and r.owner_id=v_owner_id) then
    raise exception 'RUN_NOT_FOUND' using errcode='P0002';
  end if;

  for v_item in select value from jsonb_array_elements(p_records) loop
    if coalesce(char_length(v_item->>'external_id'),0)<3
       or coalesce(char_length(v_item->>'content_hash'),0)<8
       or upper(coalesce(v_item->>'memory_type','')) not in (
         'EVIDENCE','SECTION','ACTION','GOAL','PREFERENCE','CONSTRAINT',
         'CONFIRMED_DECISION','CORRECTION','LESSON','EPISODE_SUMMARY'
       ) then
      continue;
    end if;
    insert into public.memory_projections(
      owner_id,project_id,run_id,provider,external_id,memory_type,
      profile_version,blueprint_version,content_hash,source_event_ids,
      status,metadata,synced_at,last_error
    ) values (
      v_owner_id,p_project_id,p_run_id,v_provider,left(v_item->>'external_id',500),
      upper(v_item->>'memory_type'),nullif(v_item->>'profile_version','')::integer,
      nullif(v_item->>'blueprint_version','')::integer,v_item->>'content_hash',
      array(select jsonb_array_elements_text(coalesce(v_item->'source_event_ids','[]'::jsonb))),
      case when upper(coalesce(v_item->>'status','ACTIVE')) in ('PENDING','ACTIVE','FAILED') then upper(coalesce(v_item->>'status','ACTIVE')) else 'FAILED' end,
      coalesce(v_item->'metadata','{}'::jsonb),now(),left(v_item->>'last_error',2000)
    ) on conflict(owner_id,provider,external_id) do update set
      project_id=excluded.project_id,run_id=excluded.run_id,memory_type=excluded.memory_type,
      profile_version=excluded.profile_version,blueprint_version=excluded.blueprint_version,
      content_hash=excluded.content_hash,source_event_ids=excluded.source_event_ids,
      status=excluded.status,metadata=excluded.metadata,synced_at=excluded.synced_at,
      last_error=excluded.last_error,updated_at=now();
    if v_provider='PINECONE' and upper(v_item->>'memory_type')='EVIDENCE' and (v_item->>'evidence_id')~*'^[0-9a-f-]{36}$' then
      update public.evidence set pinecone_record_id=v_item->>'external_id',updated_at=now()
      where id=(v_item->>'evidence_id')::uuid and owner_id=v_owner_id and project_id=p_project_id;
    end if;
    v_count:=v_count+1;
  end loop;
  return jsonb_build_object('recorded',true,'provider',v_provider,'count',v_count);
end;
$$;

create or replace function public.revalidate_memory_projection_hits(
  p_project_id uuid,
  p_provider text,
  p_external_ids text[]
)
returns jsonb
language sql
stable
security definer
set search_path = public, auth
as $$
  select jsonb_build_object(
    'project_id',p_project_id,'provider',upper(p_provider),
    'allowed_external_ids',coalesce(jsonb_agg(mp.external_id order by mp.external_id),'[]'::jsonb)
  )
  from public.memory_projections mp
  where mp.project_id=p_project_id and mp.owner_id=auth.uid()
    and mp.provider=upper(p_provider) and mp.status='ACTIVE'
    and mp.external_id=any(coalesce(p_external_ids,'{}'::text[]));
$$;

create or replace function public.mark_memory_projections_deleted(
  p_project_id uuid,
  p_provider text,
  p_external_ids text[]
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare v_count integer;
begin
  if auth.uid() is null then raise exception 'AUTHENTICATION_REQUIRED' using errcode='42501'; end if;
  update public.memory_projections set status='DELETED',updated_at=now()
  where project_id=p_project_id and owner_id=auth.uid() and provider=upper(p_provider)
    and external_id=any(coalesce(p_external_ids,'{}'::text[]));
  get diagnostics v_count=row_count;
  return jsonb_build_object('marked_deleted',true,'count',v_count);
end;
$$;

create or replace function public.revalidate_mem0_projection_hits(
  p_project_id uuid,
  p_hits jsonb
)
returns jsonb
language sql
stable
security definer
set search_path = public, auth
as $$
  with supplied as (
    select value->>'memory_id' memory_id,value->>'content_hash' content_hash
    from jsonb_array_elements(case when jsonb_typeof(p_hits)='array' then p_hits else '[]'::jsonb end)
  )
  select jsonb_build_object(
    'project_id',p_project_id,
    'allowed_memory_ids',coalesce(jsonb_agg(distinct s.memory_id) filter(where s.memory_id is not null),'[]'::jsonb)
  )
  from supplied s
  where exists (
    select 1 from public.memory_projections mp
    where mp.project_id=p_project_id and mp.owner_id=auth.uid()
      and mp.provider='MEM0' and mp.status in ('PENDING','ACTIVE')
      and (mp.external_id='mem:'||s.memory_id or (s.content_hash is not null and mp.content_hash=s.content_hash))
  );
$$;

create or replace function public.mark_mem0_projection_deleted(
  p_project_id uuid,
  p_memory_id text,
  p_content_hash text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare v_count integer;
begin
  if auth.uid() is null then raise exception 'AUTHENTICATION_REQUIRED' using errcode='42501'; end if;
  update public.memory_projections set status='DELETED',updated_at=now()
  where project_id=p_project_id and owner_id=auth.uid() and provider='MEM0'
    and (external_id='mem:'||p_memory_id or (p_content_hash is not null and content_hash=p_content_hash));
  get diagnostics v_count=row_count;
  return jsonb_build_object('marked_deleted',true,'count',v_count);
end;
$$;

revoke all on function public.persist_audited_stage1_evidence(uuid,integer,text,jsonb) from public,anon;
revoke all on function public.get_pinecone_projection_batch(uuid) from public,anon;
revoke all on function public.upsert_memory_projection_batch(uuid,uuid,text,jsonb) from public,anon;
revoke all on function public.revalidate_memory_projection_hits(uuid,text,text[]) from public,anon;
revoke all on function public.mark_memory_projections_deleted(uuid,text,text[]) from public,anon;
revoke all on function public.revalidate_mem0_projection_hits(uuid,jsonb) from public,anon;
revoke all on function public.mark_mem0_projection_deleted(uuid,text,text) from public,anon;
grant execute on function public.persist_audited_stage1_evidence(uuid,integer,text,jsonb) to authenticated;
grant execute on function public.get_pinecone_projection_batch(uuid) to authenticated;
grant execute on function public.upsert_memory_projection_batch(uuid,uuid,text,jsonb) to authenticated;
grant execute on function public.revalidate_memory_projection_hits(uuid,text,text[]) to authenticated;
grant execute on function public.mark_memory_projections_deleted(uuid,text,text[]) to authenticated;
grant execute on function public.revalidate_mem0_projection_hits(uuid,jsonb) to authenticated;
grant execute on function public.mark_mem0_projection_deleted(uuid,text,text) to authenticated;

commit;
