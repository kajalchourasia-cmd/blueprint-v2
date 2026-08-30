const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..', 'n8n');
const load = (name) => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8'));
const code = (workflow, name) => {
  const found = workflow.nodes.find((item) => item.name === name);
  if (!found?.parameters?.jsCode) throw new Error(`NODE_NOT_FOUND:${name}`);
  return found.parameters.jsCode;
};
const runCode = (source, input, named = {}) => {
  const fn = new Function('$input', '$json', '$', source);
  return fn(
    { first: () => ({ json: input }) },
    input,
    (name) => ({ first: () => ({ json: named[name] ?? {} }) }),
  )[0].json;
};
const assert = (condition, message) => { if (!condition) throw new Error(message); };

const advisory = load('BP-STAGE23-01-advisory-action-blueprint.json');
const fixture = runCode(code(advisory, 'Create Safe Advisory Fixture'), {});
const normalized = runCode(code(advisory, 'Normalize Advisory Task'), fixture);
const safe = runCode(code(advisory, 'Return Safe Advisory Result'), normalized);
assert(normalized.supported === true, 'Safe advisory fixture is not allowlisted.');
assert(safe.status === 'COMPLETED' && safe.test_mode === true, 'Safe advisory fixture did not complete without writes.');
assert(safe.observation.output.limitations.includes('TEST_MODE'), 'Safe fixture is not visibly synthetic.');

const finance = runCode(code(advisory, 'Build Deterministic Finance Scenarios'), {
  ...normalized,
  test_mode: false,
  module_key: 'financial_readiness',
  profile: { constraints: { available_budget: 5000, hours_per_week: 8 } },
});
assert(finance.status === 'COMPLETED', 'Available budget should produce a bounded finance result.');
assert(finance.observation.output.scenarios[0].result_budget === 5000, 'Finance result did not preserve founder input.');
assert(finance.observation.output.limitations.some((x) => /not forecast/i.test(x)), 'Finance result lost its no-forecast boundary.');

const planner = load('BP-PLAN-01-dynamic-task-planner.json');
const plannerCode = code(planner, 'Normalize Profile and Build Candidate Graph');
const stage2 = runCode(plannerCode, {
  idea_text: 'A founder evidence workspace with cited research and decisions.',
  requested_research: ['customer_demand', 'competitor_intelligence', 'market_economics'],
  profile_version: 2,
  planning_mode: 'PROVE_AND_DESIGN',
  goal: { type: 'PAID_CUSTOMERS' },
  gate_context: { decision: 'PROCEED' },
  test_mode: true,
});
assert(stage2.candidate_tasks.some((x) => x.module_key === 'financial_readiness'), 'Paid-customer goal did not select finance.');
assert(!stage2.candidate_tasks.some((x) => x.task_key.startsWith('s3_')), 'Stage 2 leaked a Stage 3 task.');

const scheduler = load('BP-SCHED-01-eligible-task-scheduler.json');
const schedulerCode = code(scheduler, 'Normalize Scheduler Request');
const scheduled = runCode(schedulerCode, {
  authorization: 'Bearer safe-test', project_id: '00000000-0000-4000-8000-000000000001',
  run_id: '00000000-0000-4000-8000-000000000002', profile_version: 2,
  requested_research: ['customer_demand'], planning_mode: 'PROVE_AND_DESIGN', test_mode: true,
});
assert(scheduled.allowed_modules.length <= 8, 'Scheduler exceeded the database allowlist boundary.');
assert(scheduled.allowed_modules.includes('execution_readiness'), 'Stage 2 scheduler omitted Gate 2.');
const discoverScheduled = runCode(schedulerCode, {
  authorization: 'Bearer safe-test', project_id: '00000000-0000-4000-8000-000000000001',
  run_id: '00000000-0000-4000-8000-000000000002', profile_version: 2,
  requested_research: ['customer_demand'], planning_mode: 'DISCOVER', test_mode: true,
});
assert(discoverScheduled.allowed_modules.length === 7, 'Discover scheduler must send exactly seven allowlisted modules.');

const chat = load('BP-CHAT-01-research-copilot.json');
assert(code(chat, 'Validate Chat Request and Scope').includes('section_key'), 'Chat does not retain section scope.');
assert(code(chat, 'Prepare Grounded Copilot Answer').includes('requested_section'), 'Chat prompt does not prioritize the selected section.');

const checkpoint = load('BP-API-03-founder-checkpoint.json');
const invalid = runCode(code(checkpoint, 'Validate Checkpoint API Request'), { body: {}, headers: {} });
assert(invalid.valid === false && invalid.status_code === 401, 'Checkpoint API does not reject missing auth safely.');

const supervisor = load('BP-00-adaptive-supervisor.json');
assert(code(supervisor, 'Normalize Canonical Supervisor Command').includes("['START','RESUME']"), 'Supervisor cannot resume after a gate.');

const auditor = load('BP-AUDIT-01-independent-evidence-auditor.json');
assert(code(auditor, 'Audit Evidence Independently').includes('directDemandGap'), 'Auditor does not distinguish desk research from direct demand evidence.');
assert(code(auditor, 'Audit Evidence Independently').includes('DESK_RESEARCH_ONLY'), 'Auditor does not label the evidence basis.');
const deskOnlyAudit = runCode(code(auditor, 'Audit Evidence Independently'), {
  task: { id: 'audit-task', task_key: 's1_evidence_audit' },
  dependency_outputs: ['customer_demand', 'competitor_intelligence', 'market_economics'].map((module) => ({
    module_key: module, status: 'COMPLETED', observation_verdict: 'VALID',
    output: {
      coverage: 1,
      evidence_cards: Array.from({ length: 4 }, (_, index) => ({ evidence_id: `web-${module}-${index}`, provider: 'YOU' })),
      observed_signals: Array.from({ length: 4 }, (_, index) => ({ claim: `Directional signal ${index}`, evidence_ids: [`web-${module}-${index}`] })),
      unknowns: ['Direct willingness to pay is unknown.'], contradictions: [],
    },
  })),
  test_mode: false,
});
const deskVerdictInput = deskOnlyAudit.observation.output.verdict_input;
const deskWeighted = (deskVerdictInput.dimension_scores.user_demand.score * 0.4)
  + (deskVerdictInput.dimension_scores.competitive_opportunity.score * 0.3)
  + (deskVerdictInput.dimension_scores.market_accessibility.score * 0.3);
assert(deskVerdictInput.critical_blockers.some((x) => /no direct interview/i.test(x)), 'Desk-only evidence did not create a direct-demand blocker.');
assert(deskWeighted < 60, 'Desk-only research can still cross the commercial viability threshold.');

console.log(JSON.stringify({
  passed: 17,
  checks: [
    'safe_advisory_fixture', 'synthetic_fixture_label', 'founder_input_finance',
    'finance_no_forecast_boundary', 'goal_specific_stage2', 'no_stage3_leak',
    'scheduler_allowlist_limit', 'gate2_scheduled', 'discover_allowlist_exact', 'section_scoped_chat',
    'section_scoped_prompt', 'checkpoint_auth_rejection', 'supervisor_resume_command',
    'direct_demand_gate', 'desk_research_label', 'desk_only_blocker', 'desk_only_score_ceiling',
  ],
}, null, 2));
