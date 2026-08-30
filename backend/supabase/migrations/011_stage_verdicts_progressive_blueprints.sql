-- Blueprint Evidence Dev
-- Migration 011: append-only stage verdicts, progressive Blueprint versions,
-- stage progress, measured founder KPIs, and two-gate HITL vocabulary.

begin;

alter table public.runs drop constraint if exists runs_current_route_check;
alter table public.runs add constraint runs_current_route_check check (
  current_route is null or current_route in (
    'IDEA_FRAME', 'RESEARCH_SUITE', 'TASK_PLANNER', 'TASK_SCHEDULER',
    'FOUNDATION', 'CUSTOMER_DEMAND', 'COMPETITOR_INTELLIGENCE',
    'MARKET_ECONOMICS', 'RESEARCH_VERDICT', 'STAGE_2_PLAN',
    'OFFER_PRICING', 'ASSUMPTIONS_RISKS', 'OPERATING_MODEL',
    'FINANCIAL_SCENARIO', 'VALIDATION_PROOF', 'EXECUTION_READINESS',
    'ACTION_BLUEPRINT', 'EXPERIMENT_DESIGN', 'LAUNCH_DISTRIBUTION',
    'GROWTH_OPTIMIZATION', 'EVIDENCE_AUDIT', 'BLUEPRINT_SYNTHESIS',
    'BLUEPRINT_QUALITY', 'RESEARCH_COPILOT', 'MEMORY_RETRIEVE',
    'MEMORY_INDEX', 'MEMORY_WRITE', 'FOUNDER_INPUT', 'HUMAN_REVIEW',
    'HITL_RESUME', 'RERUN_PLAN', 'PARTIAL_COMPLETE', 'SAFE_FAIL',
    'COMPLETE', 'CANCEL'
  )
);

alter table public.orchestration_tasks drop constraint if exists orchestration_tasks_module_key_check;
alter table public.orchestration_tasks add constraint orchestration_tasks_module_key_check check (
  module_key in (
    'foundation', 'customer_demand', 'competitor_intelligence', 'market_economics',
    'research_verdict', 'offer_pricing', 'assumptions_risks', 'operating_model',
    'financial_readiness', 'validation_proof', 'execution_readiness',
    'launch_distribution', 'growth_optimization', 'evidence_audit',
    'action_blueprint', 'final_blueprint'
  )
);

alter table public.human_checkpoints drop constraint if exists human_checkpoints_checkpoint_type_check;
alter table public.human_checkpoints add constraint human_checkpoints_checkpoint_type_check check (
  checkpoint_type in (
    'CLARIFICATION', 'CONTRADICTION', 'REPAIR_EXHAUSTED', 'PROFILE_CHANGE',
    'RERUN', 'EXPERIMENT', 'FINAL_DECISION', 'STAGE_GATE', 'MEMORY',
    'EXTERNAL_ACTION'
  )
);

alter table public.human_checkpoints drop constraint if exists human_checkpoints_decision_check;
alter table public.human_checkpoints add constraint human_checkpoints_decision_check check (
  decision is null or decision in (
    'APPROVE', 'REJECT', 'EDIT', 'REQUEST_CHANGES', 'MORE_INFORMATION',
    'RETRY', 'ESCALATE', 'OVERRIDE', 'CANCEL', 'PROCEED',
    'TARGETED_VALIDATION', 'RUN_MISSING_RESEARCH', 'CONTINUE_ANYWAY',
    'PAUSE_OR_REVISE'
  )
);

alter table public.blueprint_versions
  add column if not exists version_kind text not null default 'ACTION',
  add column if not exists artifact_stage text not null default 'ACTION_BLUEPRINT',
  add column if not exists label text,
  add column if not exists change_summary text,
  add column if not exists source_verdict_ids uuid[] not null default '{}'::uuid[];

alter table public.blueprint_versions drop constraint if exists blueprint_versions_status_check;
alter table public.blueprint_versions add constraint blueprint_versions_status_check check (
  status in ('UNRESEARCHED', 'IN_PROGRESS', 'COMPLETED', 'PARTIAL', 'HUMAN_REVIEW', 'SAFE_FAILED')
);
alter table public.blueprint_versions drop constraint if exists blueprint_versions_version_kind_check;
alter table public.blueprint_versions add constraint blueprint_versions_version_kind_check check (
  version_kind in ('ORIGINAL', 'RESEARCH', 'ACTION')
);
alter table public.blueprint_versions drop constraint if exists blueprint_versions_artifact_stage_check;
alter table public.blueprint_versions add constraint blueprint_versions_artifact_stage_check check (
  artifact_stage in ('ONBOARDING', 'DISCOVER', 'PROVE_AND_DESIGN', 'ACTION_BLUEPRINT')
);

create table public.stage_verdicts (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid not null references public.runs(id) on delete restrict,
  profile_version integer not null check (profile_version > 0),
  verdict_version integer not null check (verdict_version > 0),
  stage text not null check (stage in ('DISCOVER', 'PROVE_AND_DESIGN')),
  gate text not null check (gate in ('RESEARCH_VERDICT', 'EXECUTION_READINESS')),
  verdict text not null check (verdict in (
    'STRONG_GO', 'CONDITIONAL_GO', 'HOLD_OR_PIVOT',
    'INSUFFICIENT_EVIDENCE', 'LIMITED_VERDICT',
    'READY', 'VALIDATE_MORE', 'HUMAN_REVIEW', 'PAUSE_OR_PIVOT'
  )),
  score numeric(6,2) check (score is null or score between 0 and 100),
  score_status text not null check (score_status in ('DECISION_CAPABLE', 'PROVISIONAL', 'WITHHELD')),
  dimension_scores jsonb not null default '{}'::jsonb check (jsonb_typeof(dimension_scores) = 'object'),
  weights jsonb not null default '{}'::jsonb check (jsonb_typeof(weights) = 'object'),
  evidence_coverage numeric(5,4) not null check (evidence_coverage between 0 and 1),
  requested_streams text[] not null default '{}'::text[],
  completed_streams text[] not null default '{}'::text[],
  evidence_ids uuid[] not null default '{}'::uuid[],
  critical_blockers jsonb not null default '[]'::jsonb check (jsonb_typeof(critical_blockers) = 'array'),
  calculation_version text not null,
  decision_capable boolean not null default false,
  route text not null check (route in ('HUMAN_CHECKPOINT', 'STAGE_2_PLAN', 'TARGETED_RESEARCH', 'PAUSE', 'SAFE_FAIL')),
  explanation text not null check (char_length(explanation) between 10 and 4000),
  created_at timestamptz not null default now(),
  unique (run_id, gate, verdict_version),
  unique (id, owner_id),
  constraint stage_verdicts_project_owner_fk foreign key (project_id, owner_id)
    references public.projects(id, owner_id) on delete restrict,
  constraint stage_verdicts_run_owner_fk foreign key (run_id, owner_id)
    references public.runs(id, owner_id) on delete restrict
);

create table public.blueprint_stage_progress (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid not null references public.runs(id) on delete restrict,
  stage text not null check (stage in ('DISCOVER', 'PROVE_AND_DESIGN', 'ACTION_BLUEPRINT')),
  status text not null default 'PLANNED' check (status in (
    'PLANNED', 'RUNNING', 'WAITING_FOUNDER', 'COMPLETED', 'PARTIAL',
    'SAFE_FAILED', 'CANCELLED'
  )),
  completion_percent integer not null default 0 check (completion_percent between 0 and 100),
  active_blueprint_version_id uuid,
  section_keys text[] not null default '{}'::text[],
  completed_section_keys text[] not null default '{}'::text[],
  blocked_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (run_id, stage),
  unique (id, owner_id),
  constraint blueprint_stage_progress_project_owner_fk foreign key (project_id, owner_id)
    references public.projects(id, owner_id) on delete restrict,
  constraint blueprint_stage_progress_run_owner_fk foreign key (run_id, owner_id)
    references public.runs(id, owner_id) on delete restrict,
  constraint blueprint_stage_progress_version_owner_fk foreign key (active_blueprint_version_id, owner_id)
    references public.blueprint_versions(id, owner_id) on delete restrict
);

create table public.founder_metric_observations (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete restrict,
  project_id uuid not null references public.projects(id) on delete restrict,
  run_id uuid references public.runs(id) on delete restrict,
  metric_key text not null check (char_length(metric_key) between 1 and 120),
  label text not null check (char_length(label) between 1 and 200),
  value numeric,
  unit text not null check (unit in ('COUNT', 'CURRENCY', 'PERCENT', 'DAYS', 'HOURS', 'OTHER')),
  numerator numeric,
  denominator numeric,
  sample_size integer check (sample_size is null or sample_size >= 0),
  period_start date,
  period_end date,
  source text not null default 'FOUNDER' check (source in ('FOUNDER', 'IMPORTED', 'DERIVED')),
  notes text,
  created_at timestamptz not null default now(),
  unique (id, owner_id),
  constraint founder_metric_period_check check (period_end is null or period_start is null or period_end >= period_start),
  constraint founder_metric_conversion_check check (
    metric_key <> 'conversion_rate' or (
      numerator is not null and denominator is not null and denominator > 0
      and numerator between 0 and denominator
      and value is not null
      and abs(value - ((numerator / denominator) * 100)) < 0.01
      and sample_size is not null and sample_size >= denominator
    )
  ),
  constraint founder_metric_project_owner_fk foreign key (project_id, owner_id)
    references public.projects(id, owner_id) on delete restrict,
  constraint founder_metric_run_owner_fk foreign key (run_id, owner_id)
    references public.runs(id, owner_id) on delete restrict
);

create index stage_verdicts_latest_idx on public.stage_verdicts(project_id, gate, verdict_version desc);
create index blueprint_stage_progress_run_idx on public.blueprint_stage_progress(run_id, stage);
create index founder_metric_latest_idx on public.founder_metric_observations(project_id, metric_key, created_at desc);

create trigger stage_verdicts_immutable before update or delete on public.stage_verdicts
for each row execute function public.reject_audit_mutation();
create trigger founder_metric_observations_immutable before update or delete on public.founder_metric_observations
for each row execute function public.reject_audit_mutation();
create trigger blueprint_stage_progress_set_updated_at before update on public.blueprint_stage_progress
for each row execute function public.set_updated_at();
create trigger blueprint_stage_progress_protect_identity before update on public.blueprint_stage_progress
for each row execute function public.prevent_identity_change();

alter table public.stage_verdicts enable row level security;
alter table public.blueprint_stage_progress enable row level security;
alter table public.founder_metric_observations enable row level security;

create policy stage_verdicts_select_own on public.stage_verdicts for select to authenticated using ((select auth.uid()) = owner_id);
create policy stage_verdicts_insert_own on public.stage_verdicts for insert to authenticated with check ((select auth.uid()) = owner_id);
create policy blueprint_stage_progress_select_own on public.blueprint_stage_progress for select to authenticated using ((select auth.uid()) = owner_id);
create policy blueprint_stage_progress_insert_own on public.blueprint_stage_progress for insert to authenticated with check ((select auth.uid()) = owner_id);
create policy blueprint_stage_progress_update_own on public.blueprint_stage_progress for update to authenticated using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id);
create policy founder_metric_observations_select_own on public.founder_metric_observations for select to authenticated using ((select auth.uid()) = owner_id);
create policy founder_metric_observations_insert_own on public.founder_metric_observations for insert to authenticated with check ((select auth.uid()) = owner_id);

revoke all on public.stage_verdicts, public.blueprint_stage_progress, public.founder_metric_observations from anon;
grant select, insert on public.stage_verdicts, public.founder_metric_observations to authenticated;
grant select, insert, update on public.blueprint_stage_progress to authenticated;

create or replace function public.persist_research_verdict(
  p_run_id uuid,
  p_profile_version integer,
  p_requested_streams text[],
  p_completed_streams text[],
  p_dimension_scores jsonb,
  p_evidence_coverage numeric,
  p_evidence_ids uuid[] default '{}'::uuid[],
  p_critical_blockers jsonb default '[]'::jsonb,
  p_explanation text default 'Research verdict calculated from audited evidence.'
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
  v_user_score numeric;
  v_competitor_score numeric;
  v_market_score numeric;
  v_score numeric(6,2);
  v_verdict text;
  v_score_status text;
  v_decision_capable boolean := false;
  v_full_requested boolean;
  v_full_completed boolean;
  v_verdict_id uuid;
  v_checkpoint_id uuid;
  v_decisions text[];
begin
  if v_owner_id is null then
    raise exception 'AUTHENTICATION_REQUIRED' using errcode = '42501';
  end if;
  if p_profile_version is null or p_profile_version < 1 then
    raise exception 'PROFILE_VERSION_INVALID' using errcode = '22023';
  end if;
  if p_dimension_scores is null or jsonb_typeof(p_dimension_scores) <> 'object' then
    raise exception 'DIMENSION_SCORES_MUST_BE_OBJECT' using errcode = '22023';
  end if;
  if p_evidence_coverage is null or p_evidence_coverage < 0 or p_evidence_coverage > 1 then
    raise exception 'EVIDENCE_COVERAGE_INVALID' using errcode = '22023';
  end if;
  if p_critical_blockers is null or jsonb_typeof(p_critical_blockers) <> 'array' then
    raise exception 'CRITICAL_BLOCKERS_MUST_BE_ARRAY' using errcode = '22023';
  end if;
  if coalesce(char_length(p_explanation), 0) not between 10 and 4000 then
    raise exception 'VERDICT_EXPLANATION_INVALID' using errcode = '22023';
  end if;

  select r.project_id, r.state_version into v_project_id, v_state_version
  from public.runs r
  where r.id=p_run_id and r.owner_id=v_owner_id
  for update;
  if v_project_id is null then
    raise exception 'RUN_NOT_FOUND' using errcode = 'P0002';
  end if;
  if not exists (
    select 1 from public.project_profiles pp
    where pp.project_id=v_project_id and pp.owner_id=v_owner_id and pp.version=p_profile_version
  ) then
    raise exception 'PROFILE_VERSION_NOT_FOUND' using errcode = 'P0002';
  end if;

  if exists (
    select 1 from unnest(coalesce(p_requested_streams, '{}'::text[])) s
    where s not in ('user_research','competitor_research','market_research')
  ) or exists (
    select 1 from unnest(coalesce(p_completed_streams, '{}'::text[])) s
    where s not in ('user_research','competitor_research','market_research')
  ) then
    raise exception 'RESEARCH_STREAM_INVALID' using errcode = '22023';
  end if;

  v_full_requested := cardinality(coalesce(p_requested_streams, '{}'::text[]))=3
    and p_requested_streams @> array['user_research','competitor_research','market_research'];
  v_full_completed := cardinality(coalesce(p_completed_streams, '{}'::text[]))=3
    and p_completed_streams @> array['user_research','competitor_research','market_research'];

  if not v_full_requested then
    v_verdict := 'LIMITED_VERDICT';
    v_score_status := 'WITHHELD';
  elsif not v_full_completed or p_evidence_coverage < 0.60 then
    v_verdict := 'INSUFFICIENT_EVIDENCE';
    v_score_status := 'WITHHELD';
  else
    v_user_score := nullif(p_dimension_scores #>> '{user_demand,score}', '')::numeric;
    v_competitor_score := nullif(p_dimension_scores #>> '{competitive_opportunity,score}', '')::numeric;
    v_market_score := nullif(p_dimension_scores #>> '{market_accessibility,score}', '')::numeric;
    if v_user_score is null or v_user_score not between 0 and 100
       or v_competitor_score is null or v_competitor_score not between 0 and 100
       or v_market_score is null or v_market_score not between 0 and 100 then
      v_verdict := 'INSUFFICIENT_EVIDENCE';
      v_score_status := 'WITHHELD';
    else
      v_score := round((v_user_score*0.40)+(v_competitor_score*0.30)+(v_market_score*0.30), 2);
      v_decision_capable := true;
      v_score_status := 'DECISION_CAPABLE';
      if jsonb_array_length(p_critical_blockers) > 0 then
        v_verdict := 'HOLD_OR_PIVOT';
      elsif v_score >= 75 then
        v_verdict := 'STRONG_GO';
      elsif v_score >= 60 then
        v_verdict := 'CONDITIONAL_GO';
      else
        v_verdict := 'HOLD_OR_PIVOT';
      end if;
    end if;
  end if;

  select coalesce(max(verdict_version),0)+1 into v_verdict_version
  from public.stage_verdicts
  where run_id=p_run_id and gate='RESEARCH_VERDICT' and owner_id=v_owner_id;

  insert into public.stage_verdicts (
    owner_id, project_id, run_id, profile_version, verdict_version,
    stage, gate, verdict, score, score_status, dimension_scores, weights,
    evidence_coverage, requested_streams, completed_streams, evidence_ids,
    critical_blockers, calculation_version, decision_capable, route, explanation
  ) values (
    v_owner_id, v_project_id, p_run_id, p_profile_version, v_verdict_version,
    'DISCOVER', 'RESEARCH_VERDICT', v_verdict, v_score, v_score_status,
    p_dimension_scores,
    '{"user_demand":0.40,"competitive_opportunity":0.30,"market_accessibility":0.30}'::jsonb,
    p_evidence_coverage, coalesce(p_requested_streams,'{}'::text[]),
    coalesce(p_completed_streams,'{}'::text[]), coalesce(p_evidence_ids,'{}'::uuid[]),
    p_critical_blockers, 'research-viability-v1', v_decision_capable,
    'HUMAN_CHECKPOINT', p_explanation
  ) returning id into v_verdict_id;

  insert into public.blueprint_stage_progress (
    owner_id, project_id, run_id, stage, status, completion_percent,
    section_keys, completed_section_keys
  ) values (
    v_owner_id, v_project_id, p_run_id, 'DISCOVER',
    case when v_verdict in ('INSUFFICIENT_EVIDENCE','LIMITED_VERDICT') then 'PARTIAL' else 'WAITING_FOUNDER' end,
    case when v_full_completed then 100 else 75 end,
    array['customer_demand','competitor_intelligence','market_economics'],
    case when v_full_completed then array['customer_demand','competitor_intelligence','market_economics'] else '{}'::text[] end
  ) on conflict (run_id, stage) do update set
    status=excluded.status,
    completion_percent=excluded.completion_percent,
    section_keys=excluded.section_keys,
    completed_section_keys=excluded.completed_section_keys,
    blocked_reason='RESEARCH_VERDICT_CHECKPOINT';

  v_decisions := case
    when v_verdict in ('STRONG_GO','CONDITIONAL_GO')
      then array['PROCEED','PAUSE_OR_REVISE']
    when v_verdict='LIMITED_VERDICT'
      then array['RUN_MISSING_RESEARCH','CONTINUE_ANYWAY','PAUSE_OR_REVISE']
    else array['TARGETED_VALIDATION','CONTINUE_ANYWAY','PAUSE_OR_REVISE']
  end;

  insert into public.human_checkpoints (
    owner_id, project_id, run_id, checkpoint_type, status, proposal_hash,
    state_version, profile_version, payload, available_decisions
  ) values (
    v_owner_id, v_project_id, p_run_id, 'STAGE_GATE', 'PENDING',
    md5(p_run_id::text||':RESEARCH_VERDICT:'||v_verdict_version::text),
    greatest(coalesce(v_state_version,1),1), p_profile_version,
    jsonb_build_object(
      'verdict_id',v_verdict_id,'verdict',v_verdict,'score',v_score,
      'score_status',v_score_status,'evidence_coverage',p_evidence_coverage,
      'primary_ui_actions',array['REVIEW_STAGE_1_RESULTS','CONTINUE_OR_CHOOSE_NEXT_STEP']
    ), v_decisions
  ) returning id into v_checkpoint_id;

  return jsonb_build_object(
    'persisted',true,'verdict_id',v_verdict_id,'verdict_version',v_verdict_version,
    'verdict',v_verdict,'score',v_score,'score_status',v_score_status,
    'decision_capable',v_decision_capable,'evidence_coverage',p_evidence_coverage,
    'checkpoint_id',v_checkpoint_id,'available_decisions',v_decisions,
    'route','HUMAN_CHECKPOINT'
  );
end;
$$;

create or replace function public.create_progressive_blueprint_version(
  p_run_id uuid,
  p_profile_version integer,
  p_version_kind text,
  p_artifact_stage text,
  p_status text,
  p_blueprint jsonb,
  p_change_summary text,
  p_source_verdict_ids uuid[] default '{}'::uuid[]
)
returns public.blueprint_versions
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_owner_id uuid := auth.uid();
  v_project_id uuid;
  v_version integer;
  v_supersedes_id uuid;
  v_row public.blueprint_versions;
begin
  if v_owner_id is null then
    raise exception 'AUTHENTICATION_REQUIRED' using errcode = '42501';
  end if;
  if p_version_kind not in ('ORIGINAL','RESEARCH','ACTION')
     or p_artifact_stage not in ('ONBOARDING','DISCOVER','PROVE_AND_DESIGN','ACTION_BLUEPRINT')
     or p_status not in ('UNRESEARCHED','IN_PROGRESS','COMPLETED','PARTIAL','HUMAN_REVIEW','SAFE_FAILED') then
    raise exception 'BLUEPRINT_VERSION_CLASSIFICATION_INVALID' using errcode = '22023';
  end if;
  if p_blueprint is null or jsonb_typeof(p_blueprint) <> 'object' then
    raise exception 'BLUEPRINT_MUST_BE_OBJECT' using errcode = '22023';
  end if;
  if coalesce(char_length(p_change_summary),0) not between 3 and 2000 then
    raise exception 'CHANGE_SUMMARY_INVALID' using errcode = '22023';
  end if;

  select r.project_id into v_project_id
  from public.runs r where r.id=p_run_id and r.owner_id=v_owner_id;
  if v_project_id is null then
    raise exception 'RUN_NOT_FOUND' using errcode = 'P0002';
  end if;
  perform 1 from public.projects p where p.id=v_project_id and p.owner_id=v_owner_id for update;
  if not exists (
    select 1 from public.project_profiles pp
    where pp.project_id=v_project_id and pp.owner_id=v_owner_id and pp.version=p_profile_version
  ) then
    raise exception 'PROFILE_VERSION_NOT_FOUND' using errcode = 'P0002';
  end if;
  if not coalesce(p_source_verdict_ids,'{}'::uuid[]) <@ array(
    select sv.id from public.stage_verdicts sv
    where sv.run_id=p_run_id and sv.owner_id=v_owner_id
  ) then
    raise exception 'SOURCE_VERDICT_NOT_OWNED_BY_RUN' using errcode = '42501';
  end if;

  select id, version into v_supersedes_id, v_version
  from public.blueprint_versions
  where project_id=v_project_id and owner_id=v_owner_id
  order by version desc limit 1;
  v_version := coalesce(v_version,0)+1;

  insert into public.blueprint_versions (
    owner_id, project_id, run_id, profile_version, version, status,
    blueprint, quality_summary, supersedes_id, version_kind, artifact_stage,
    label, change_summary, source_verdict_ids
  ) values (
    v_owner_id, v_project_id, p_run_id, p_profile_version, v_version, p_status,
    p_blueprint, '{}'::jsonb, v_supersedes_id, p_version_kind, p_artifact_stage,
    case p_version_kind when 'ORIGINAL' then 'Original Blueprint' when 'RESEARCH' then 'Research Blueprint' else 'Action Blueprint' end,
    p_change_summary, coalesce(p_source_verdict_ids,'{}'::uuid[])
  ) returning * into v_row;

  if p_version_kind='ORIGINAL' then
    insert into public.blueprint_stage_progress(owner_id,project_id,run_id,stage,status,completion_percent,active_blueprint_version_id)
    values
      (v_owner_id,v_project_id,p_run_id,'DISCOVER','PLANNED',0,v_row.id),
      (v_owner_id,v_project_id,p_run_id,'PROVE_AND_DESIGN','PLANNED',0,v_row.id),
      (v_owner_id,v_project_id,p_run_id,'ACTION_BLUEPRINT','PLANNED',0,v_row.id)
    on conflict (run_id,stage) do update set active_blueprint_version_id=excluded.active_blueprint_version_id;
  elsif p_version_kind='RESEARCH' then
    update public.blueprint_stage_progress set active_blueprint_version_id=v_row.id
    where run_id=p_run_id and owner_id=v_owner_id;
  else
    update public.blueprint_stage_progress set active_blueprint_version_id=v_row.id
    where run_id=p_run_id and owner_id=v_owner_id;
  end if;

  return v_row;
end;
$$;

create or replace function public.get_progressive_blueprint_dashboard(p_project_id uuid)
returns jsonb
language sql
stable
security invoker
set search_path = public, auth
as $$
  select jsonb_build_object(
    'project_id', p_project_id,
    'versions', coalesce((select jsonb_agg(jsonb_build_object(
      'id',bv.id,'version',bv.version,'label',bv.label,'version_kind',bv.version_kind,
      'artifact_stage',bv.artifact_stage,'status',bv.status,'profile_version',bv.profile_version,
      'change_summary',bv.change_summary,'created_at',bv.created_at
    ) order by bv.version) from public.blueprint_versions bv
      where bv.project_id=p_project_id and bv.owner_id=auth.uid()), '[]'::jsonb),
    'current_version', (select to_jsonb(bv) from public.blueprint_versions bv
      where bv.project_id=p_project_id and bv.owner_id=auth.uid()
      order by bv.version desc limit 1),
    'stage_progress', coalesce((select jsonb_agg(to_jsonb(sp) order by
      case sp.stage when 'DISCOVER' then 1 when 'PROVE_AND_DESIGN' then 2 else 3 end)
      from public.blueprint_stage_progress sp
      where sp.project_id=p_project_id and sp.owner_id=auth.uid()), '[]'::jsonb),
    'latest_verdicts', coalesce((select jsonb_agg(to_jsonb(v)) from (
      select distinct on (sv.gate) sv.* from public.stage_verdicts sv
      where sv.project_id=p_project_id and sv.owner_id=auth.uid()
      order by sv.gate, sv.verdict_version desc
    ) v), '[]'::jsonb),
    'measured_metrics', coalesce((select jsonb_agg(to_jsonb(m)) from (
      select distinct on (f.metric_key) f.* from public.founder_metric_observations f
      where f.project_id=p_project_id and f.owner_id=auth.uid()
      order by f.metric_key, f.created_at desc
    ) m), '[]'::jsonb),
    'contextual_actions', coalesce((select jsonb_agg(to_jsonb(a) order by a.priority,a.created_at)
      from public.next_actions a where a.project_id=p_project_id and a.owner_id=auth.uid()
      and a.status in ('OPEN','IN_PROGRESS','BLOCKED')), '[]'::jsonb)
  )
  where exists (select 1 from public.projects p where p.id=p_project_id and p.owner_id=auth.uid());
$$;

revoke all on function public.persist_research_verdict(uuid,integer,text[],text[],jsonb,numeric,uuid[],jsonb,text) from public, anon;
revoke all on function public.create_progressive_blueprint_version(uuid,integer,text,text,text,jsonb,text,uuid[]) from public, anon;
revoke all on function public.get_progressive_blueprint_dashboard(uuid) from public, anon;
grant execute on function public.persist_research_verdict(uuid,integer,text[],text[],jsonb,numeric,uuid[],jsonb,text) to authenticated;
grant execute on function public.create_progressive_blueprint_version(uuid,integer,text,text,text,jsonb,text,uuid[]) to authenticated;
grant execute on function public.get_progressive_blueprint_dashboard(uuid) to authenticated;

commit;
