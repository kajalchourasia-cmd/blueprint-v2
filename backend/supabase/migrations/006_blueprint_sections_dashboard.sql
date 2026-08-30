-- Blueprint Evidence Dev
-- Migration 006: durable module status and owner-scoped dashboard projection.

begin;

create table if not exists public.blueprint_sections (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid not null references public.runs(id) on delete restrict,
  section_key text not null check (section_key in (
    'foundation', 'customer_demand', 'competitor_intelligence', 'market_economics',
    'operating_model', 'financial_readiness', 'validation', 'launch_distribution',
    'growth_optimization', 'final_blueprint'
  )),
  status text not null default 'BLOCKED' check (status in (
    'NOT_REQUESTED', 'BLOCKED', 'NEEDS_INPUT', 'IN_PROGRESS', 'AGENT_DONE',
    'HUMAN_REVIEW', 'COMPLETED', 'PARTIAL', 'SAFE_FAILED'
  )),
  completion_percent integer not null default 0 check (completion_percent between 0 and 100),
  summary jsonb not null default '{}'::jsonb,
  open_questions jsonb not null default '[]'::jsonb check (jsonb_typeof(open_questions) = 'array'),
  evidence_ids uuid[] not null default '{}'::uuid[],
  dependency_keys text[] not null default '{}'::text[],
  source_count integer not null default 0 check (source_count >= 0),
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (run_id, section_key),
  unique (id, owner_id)
);

alter table public.blueprint_sections
  add constraint blueprint_sections_project_owner_fk foreign key (project_id, owner_id)
  references public.projects(id, owner_id) on delete restrict;
alter table public.blueprint_sections
  add constraint blueprint_sections_run_owner_fk foreign key (run_id, owner_id)
  references public.runs(id, owner_id) on delete restrict;

create index if not exists blueprint_sections_project_idx
  on public.blueprint_sections(project_id, status, section_key);
create index if not exists blueprint_sections_run_idx
  on public.blueprint_sections(run_id, section_key);

drop trigger if exists set_updated_at on public.blueprint_sections;
create trigger set_updated_at before update on public.blueprint_sections
for each row execute function public.set_updated_at();

alter table public.blueprint_sections enable row level security;

drop policy if exists blueprint_sections_select_own on public.blueprint_sections;
create policy blueprint_sections_select_own on public.blueprint_sections
for select to authenticated using (owner_id = auth.uid());
drop policy if exists blueprint_sections_insert_own on public.blueprint_sections;
create policy blueprint_sections_insert_own on public.blueprint_sections
for insert to authenticated with check (owner_id = auth.uid());
drop policy if exists blueprint_sections_update_own on public.blueprint_sections;
create policy blueprint_sections_update_own on public.blueprint_sections
for update to authenticated using (owner_id = auth.uid()) with check (owner_id = auth.uid());
drop policy if exists blueprint_sections_delete_own on public.blueprint_sections;
create policy blueprint_sections_delete_own on public.blueprint_sections
for delete to authenticated using (owner_id = auth.uid());

grant select, insert, update, delete on public.blueprint_sections to authenticated;
revoke all on public.blueprint_sections from anon;

create or replace function public.get_blueprint_dashboard(p_project_id uuid)
returns jsonb
language sql
stable
security invoker
set search_path = public, auth
as $$
  select jsonb_build_object(
    'project_id', p.id,
    'product_idea', p.idea_text,
    'starting_position', jsonb_build_object(
      'industry', p.optional_industry,
      'geography', p.geography,
      'constraints', p.constraints,
      'normalized_frame', p.normalized_frame
    ),
    'latest_run', case when r.id is null then null else jsonb_build_object(
      'run_id', r.id, 'status', r.status, 'current_route', r.current_route,
      'missing_information', r.missing_information, 'updated_at', r.updated_at
    ) end,
    'completion_percent', coalesce(sec.completion_percent, 0),
    'open_assumptions', coalesce((select count(*) from public.hypotheses h where h.project_id=p.id and h.owner_id=auth.uid() and h.status='OPEN'), 0),
    'positive_signals', coalesce((select count(*) from public.hypotheses h where h.project_id=p.id and h.owner_id=auth.uid() and h.status='SUPPORTED'), 0),
    'open_risks', coalesce((select count(*) from public.hypotheses h where h.project_id=p.id and h.owner_id=auth.uid() and h.hypothesis_type='RISK' and h.status in ('OPEN','CONTRADICTED')), 0),
    'sections', coalesce(sec.sections, '[]'::jsonb)
  )
  from public.projects p
  left join lateral (
    select rr.* from public.runs rr
    where rr.project_id=p.id and rr.owner_id=auth.uid()
    order by rr.created_at desc limit 1
  ) r on true
  left join lateral (
    select
      coalesce(round(avg(bs.completion_percent))::integer, 0) as completion_percent,
      coalesce(jsonb_agg(jsonb_build_object(
        'section_key', bs.section_key, 'status', bs.status,
        'completion_percent', bs.completion_percent, 'summary', bs.summary,
        'open_questions', bs.open_questions, 'source_count', bs.source_count,
        'updated_at', bs.updated_at
      ) order by bs.created_at) filter (where bs.id is not null), '[]'::jsonb) as sections
    from public.blueprint_sections bs
    where bs.run_id=r.id and bs.owner_id=auth.uid()
  ) sec on true
  where p.id=p_project_id and p.owner_id=auth.uid();
$$;

revoke all on function public.get_blueprint_dashboard(uuid) from public, anon;
grant execute on function public.get_blueprint_dashboard(uuid) to authenticated;

commit;
