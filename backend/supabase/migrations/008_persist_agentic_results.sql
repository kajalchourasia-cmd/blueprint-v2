-- Blueprint Evidence Dev
-- Migration 008: atomic owner-scoped persistence for Supervisor results and chat exchanges.

begin;

alter table public.chat_messages
  alter column citation_ids type text[] using citation_ids::text[];

create or replace function public.persist_supervisor_result(p_result jsonb)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  caller_id uuid := auth.uid();
  v_project_id uuid;
  v_run_id uuid;
  v_run public.runs%rowtype;
  v_status text;
  v_route text;
  v_version integer;
  v_item jsonb;
  v_section_key text;
  v_section_status text;
  v_claim text;
  v_url text;
  v_source_type text;
  v_provider text;
  v_quality jsonb := coalesce(p_result->'quality', '{}'::jsonb);
begin
  if caller_id is null then
    raise exception 'AUTH_REQUIRED' using errcode = '42501';
  end if;
  if jsonb_typeof(p_result) <> 'object' then
    raise exception 'RESULT_OBJECT_REQUIRED' using errcode = '22023';
  end if;

  v_project_id := coalesce(
    nullif(p_result->>'project_id', '')::uuid,
    nullif(p_result#>>'{persistence_envelope,project_id}', '')::uuid
  );
  v_run_id := coalesce(
    nullif(p_result->>'run_id', '')::uuid,
    nullif(p_result#>>'{persistence_envelope,run_id}', '')::uuid
  );

  select * into v_run
  from public.runs
  where id = v_run_id and project_id = v_project_id and owner_id = caller_id
  for update;
  if not found then
    raise exception 'RUN_NOT_FOUND_OR_FORBIDDEN' using errcode = 'P0002';
  end if;

  v_status := upper(coalesce(p_result->>'status', 'SAFE_FAILED'));
  if v_status not in ('NEEDS_INPUT', 'RESEARCHING', 'COMPLETED', 'PARTIAL', 'HUMAN_REVIEW', 'SAFE_FAILED', 'CANCELLED') then
    v_status := 'SAFE_FAILED';
  end if;
  v_route := upper(coalesce(p_result->>'route', 'SAFE_FAIL'));
  if v_route not in (
    'IDEA_FRAME', 'RESEARCH_SUITE', 'CUSTOMER_DEMAND', 'COMPETITOR_INTELLIGENCE',
    'MARKET_ECONOMICS', 'FINANCIAL_SCENARIO', 'EVIDENCE_AUDIT',
    'EXPERIMENT_DESIGN', 'BLUEPRINT_SYNTHESIS', 'BLUEPRINT_QUALITY',
    'RESEARCH_COPILOT', 'MEMORY_INDEX', 'FOUNDER_INPUT', 'HUMAN_REVIEW',
    'PARTIAL_COMPLETE', 'SAFE_FAIL', 'COMPLETE', 'CANCEL'
  ) then
    v_route := 'SAFE_FAIL';
  end if;
  v_version := v_run.state_version + 1;

  update public.runs
  set status = v_status,
      current_route = v_route,
      current_node = 'BP-00 Adaptive Supervisor',
      state_version = v_version,
      transition_count = least(20, transition_count + 1),
      revision_count = least(3, greatest(revision_count, coalesce((p_result->>'revision_count')::integer, 0))),
      missing_information = case when jsonb_typeof(p_result->'missing_information') = 'array' then p_result->'missing_information' else '[]'::jsonb end,
      safety_flags = case when v_status = 'SAFE_FAILED' then jsonb_build_array(coalesce(p_result->>'message', 'Safe failure')) else safety_flags end,
      final_output = p_result - 'owner_id',
      updated_at = now()
  where id = v_run_id and owner_id = caller_id;

  insert into public.run_contexts (
    run_id, owner_id, project_id, normalized_intent, normalized_constraints,
    current_plan, pending_actions, structured_outputs, missing_information,
    safety_flags, route_decision, route_confidence, route_evidence,
    quality_summary, memory_version
  ) values (
    v_run_id, caller_id, v_project_id,
    jsonb_build_object('command', coalesce(p_result->>'command', 'START')),
    coalesce(p_result#>'{blueprint,starting_position}', '{}'::jsonb),
    coalesce(p_result#>'{route_decision,allowed_next_routes}', '[]'::jsonb),
    case when coalesce((p_result->>'requires_human')::boolean, false) then jsonb_build_array(jsonb_build_object('type', 'HUMAN_REVIEW', 'message', p_result->>'message')) else '[]'::jsonb end,
    jsonb_build_object('blueprint', coalesce(p_result->'blueprint', '{}'::jsonb)),
    case when jsonb_typeof(p_result->'missing_information') = 'array' then p_result->'missing_information' else '[]'::jsonb end,
    case when v_status = 'SAFE_FAILED' then jsonb_build_array(coalesce(p_result->>'message', 'Safe failure')) else '[]'::jsonb end,
    coalesce(p_result->'route_decision', jsonb_build_object('route', v_route, 'reason_code', v_status)),
    coalesce((p_result#>>'{route_decision,confidence}')::numeric, 1),
    coalesce(p_result#>'{route_decision,route_evidence}', jsonb_build_array(v_route)),
    v_quality,
    case when coalesce((p_result->>'memory_write_authorized')::boolean, false) then 1 else 0 end
  )
  on conflict (run_id) do update set
    structured_outputs = excluded.structured_outputs,
    missing_information = excluded.missing_information,
    safety_flags = excluded.safety_flags,
    route_decision = excluded.route_decision,
    route_confidence = excluded.route_confidence,
    route_evidence = excluded.route_evidence,
    quality_summary = excluded.quality_summary,
    memory_version = public.run_contexts.memory_version + case when excluded.memory_version > 0 then 1 else 0 end,
    updated_at = now();

  insert into public.state_transitions (
    owner_id, project_id, run_id, from_status, to_status, route, actor,
    reason_code, detail, state_version, correlation_id
  ) values (
    caller_id, v_project_id, v_run_id, v_run.status, v_status, v_route,
    'SUPERVISOR', coalesce(p_result#>>'{route_decision,reason_code}', v_route),
    jsonb_build_object('requires_human', coalesce((p_result->>'requires_human')::boolean, false), 'terminal', coalesce((p_result->>'terminal')::boolean, false)),
    v_version, p_result->>'correlation_id'
  );

  for v_item in select value from jsonb_array_elements(coalesce(p_result#>'{blueprint,sections}', '[]'::jsonb)) loop
    v_section_key := v_item->>'section_key';
    if v_section_key in ('foundation', 'customer_demand', 'competitor_intelligence', 'market_economics', 'operating_model', 'financial_readiness', 'validation', 'launch_distribution', 'growth_optimization', 'final_blueprint') then
      v_section_status := upper(coalesce(v_item->>'status', 'PARTIAL'));
      if v_section_status not in ('NOT_REQUESTED', 'BLOCKED', 'NEEDS_INPUT', 'IN_PROGRESS', 'AGENT_DONE', 'HUMAN_REVIEW', 'COMPLETED', 'PARTIAL', 'SAFE_FAILED') then
        v_section_status := 'PARTIAL';
      end if;
      insert into public.blueprint_sections (
        owner_id, project_id, run_id, section_key, status, completion_percent,
        summary, open_questions, evidence_ids, source_count, version
      ) values (
        caller_id, v_project_id, v_run_id, v_section_key, v_section_status,
        least(100, greatest(0, coalesce((v_item->>'completion_percent')::integer, 0))),
        case when jsonb_typeof(v_item->'summary') = 'object' then v_item->'summary' else jsonb_build_object('text', coalesce(v_item->>'summary', '')) end,
        case when jsonb_typeof(v_item->'open_questions') = 'array' then v_item->'open_questions' else '[]'::jsonb end,
        '{}'::uuid[],
        case when jsonb_typeof(v_item->'evidence_ids') = 'array' then jsonb_array_length(v_item->'evidence_ids') else 0 end,
        1
      )
      on conflict (run_id, section_key) do update set
        status = excluded.status,
        completion_percent = excluded.completion_percent,
        summary = excluded.summary,
        open_questions = excluded.open_questions,
        source_count = excluded.source_count,
        version = public.blueprint_sections.version + 1,
        updated_at = now();
    end if;
  end loop;

  for v_item in select value from jsonb_array_elements(coalesce(p_result#>'{blueprint,citations}', '[]'::jsonb)) loop
    if upper(coalesce(v_item->>'auditor_verdict', '')) in ('ACCEPT', 'ACCEPT_WITH_LIMITATION') then
      v_url := v_item->>'source_url';
      v_claim := btrim(coalesce(v_item->>'claim', v_item->>'excerpt', v_item->>'source_title', ''));
      if v_url ~* '^https://' and char_length(v_claim) >= 5 then
        v_source_type := upper(coalesce(v_item->>'source_type', 'OTHER'));
        if v_source_type not in ('FIRST_PARTY', 'GOVERNMENT', 'ACADEMIC', 'INDUSTRY', 'NEWS', 'REVIEW', 'COMMUNITY', 'MARKETPLACE', 'OTHER') then v_source_type := 'OTHER'; end if;
        v_provider := upper(coalesce(v_item->>'provider', 'OTHER'));
        if v_provider not in ('YOU', 'TAVILY', 'FIRECRAWL', 'DIRECT', 'FOUNDER', 'OTHER') then v_provider := 'OTHER'; end if;
        insert into public.evidence (
          owner_id, project_id, run_id, claim, stance, source_url, source_title,
          source_domain, source_type, retrieved_at, excerpt, query, provider,
          content_hash, limitations, auditor_verdict
        ) values (
          caller_id, v_project_id, v_run_id, left(v_claim, 8000), 'NEUTRAL', v_url,
          left(v_item->>'source_title', 1000), lower(coalesce(substring(v_url from '^https://([^/]+)'), 'unknown.invalid')),
          v_source_type, coalesce(nullif(v_item->>'retrieved_at', '')::timestamptz, now()),
          left(v_item->>'excerpt', 12000), v_item->>'query', v_provider,
          md5(v_url || '|' || v_claim),
          case when jsonb_typeof(v_item->'limitations') = 'array' then v_item->'limitations' else '[]'::jsonb end,
          upper(v_item->>'auditor_verdict')
        ) on conflict do nothing;
      end if;
    end if;
  end loop;

  if jsonb_typeof(v_quality) = 'object' and v_quality ? 'verdict' then
    insert into public.quality_checks (
      owner_id, project_id, run_id, check_type, rubric_scores, failed_rules,
      repair_instructions, before_score, after_score, verdict
    ) values (
      caller_id, v_project_id, v_run_id, 'FINAL_BLUEPRINT_QUALITY',
      coalesce(v_quality->'rubric_scores', '{}'::jsonb),
      coalesce(v_quality->'failed_rules', '[]'::jsonb),
      coalesce(v_quality->'repair_instructions', '[]'::jsonb),
      case when p_result#>>'{before_quality,overall_score}' is null then null else (p_result#>>'{before_quality,overall_score}')::numeric end,
      case when v_quality->>'overall_score' is null then null else (v_quality->>'overall_score')::numeric end,
      case when upper(v_quality->>'verdict') in ('PASS', 'REPAIR', 'FAIL', 'HUMAN_REVIEW') then upper(v_quality->>'verdict') else 'FAIL' end
    );
  end if;

  return jsonb_build_object('persisted', true, 'project_id', v_project_id, 'run_id', v_run_id, 'state_version', v_version, 'status', v_status, 'route', v_route);
end;
$$;

create or replace function public.append_chat_exchange(p_payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  caller_id uuid := auth.uid();
  v_project_id uuid := nullif(p_payload->>'project_id', '')::uuid;
  v_run_id uuid := nullif(p_payload->>'run_id', '')::uuid;
  v_thread_id uuid := nullif(p_payload->>'thread_id', '')::uuid;
  v_intent text := upper(coalesce(p_payload->>'intent', 'QUESTION'));
  v_response jsonb := coalesce(p_payload->'response', '{}'::jsonb);
  v_citations text[] := array(select jsonb_array_elements_text(coalesce(v_response->'citations', '[]'::jsonb)));
begin
  if caller_id is null then raise exception 'AUTH_REQUIRED' using errcode = '42501'; end if;
  if jsonb_typeof(p_payload) <> 'object' then raise exception 'CHAT_PAYLOAD_OBJECT_REQUIRED' using errcode = '22023'; end if;
  if not exists (select 1 from public.projects where id=v_project_id and owner_id=caller_id) then raise exception 'PROJECT_NOT_FOUND_OR_FORBIDDEN' using errcode='P0002'; end if;
  if v_run_id is null or not exists (select 1 from public.runs where id=v_run_id and project_id=v_project_id and owner_id=caller_id) then raise exception 'RUN_NOT_FOUND_OR_FORBIDDEN' using errcode='P0002'; end if;
  if v_intent not in ('QUESTION', 'EXPLAIN_PHASE', 'NEXT_STEP', 'RUN_MODULE', 'CORRECTION', 'CANCEL', 'OUT_OF_SCOPE', 'AMBIGUOUS') then v_intent := 'AMBIGUOUS'; end if;

  if v_thread_id is null then
    insert into public.chat_threads(owner_id, project_id, run_id)
    values (caller_id, v_project_id, v_run_id) returning id into v_thread_id;
  elsif not exists (select 1 from public.chat_threads where id=v_thread_id and project_id=v_project_id and owner_id=caller_id) then
    raise exception 'THREAD_NOT_FOUND_OR_FORBIDDEN' using errcode='P0002';
  end if;

  insert into public.chat_messages(owner_id, project_id, run_id, thread_id, role, intent, content, correlation_id)
  values (caller_id, v_project_id, v_run_id, v_thread_id, 'USER', v_intent, left(p_payload->>'message', 12000), p_payload->>'correlation_id');
  insert into public.chat_messages(owner_id, project_id, run_id, thread_id, role, intent, content, citation_ids, suggested_actions, correlation_id)
  values (caller_id, v_project_id, v_run_id, v_thread_id, 'ASSISTANT', v_intent, left(coalesce(v_response->>'answer', 'UNKNOWN'), 12000), v_citations, coalesce(v_response->'suggested_actions', '[]'::jsonb), p_payload->>'correlation_id');

  if v_intent = 'RUN_MODULE' and coalesce(v_response->>'status', '') not in ('NEEDS_CONFIRMATION', 'OUT_OF_SCOPE') then
    insert into public.agent_commands(owner_id, project_id, run_id, thread_id, idempotency_key, command_type, target_module, payload, approval_required, status)
    values (caller_id, v_project_id, v_run_id, v_thread_id, left(coalesce(p_payload->>'correlation_id', gen_random_uuid()::text) || ':run', 200), 'RUN_MODULE', nullif(p_payload->>'target_module', ''), p_payload, false, 'SUCCEEDED')
    on conflict (owner_id, idempotency_key) do nothing;
  end if;

  return jsonb_build_object('persisted', true, 'thread_id', v_thread_id, 'run_id', v_run_id);
end;
$$;

revoke all on function public.persist_supervisor_result(jsonb), public.append_chat_exchange(jsonb) from public, anon;
grant execute on function public.persist_supervisor_result(jsonb), public.append_chat_exchange(jsonb) to authenticated;

commit;
