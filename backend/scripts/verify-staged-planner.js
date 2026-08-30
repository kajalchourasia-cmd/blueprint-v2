const fs = require('fs');

const workflowPath = process.argv[2] || '/tmp/BP-PLAN-01.json';
const workflow = JSON.parse(fs.readFileSync(workflowPath, 'utf8'));
const node = workflow.nodes.find((item) => item.name === 'Normalize Profile and Build Candidate Graph');
const precedenceNode = workflow.nodes.find((item) => item.name === 'Enforce Explicit Gate Decision Precedence');

if (!node?.parameters?.jsCode) {
  throw new Error('PLANNER_NORMALIZER_NOT_FOUND');
}

const run = (input) => {
  const fn = new Function('$input', node.parameters.jsCode);
  const result = fn({ first: () => ({ json: input }) });
  const normalized = result[0].json;
  if (!precedenceNode?.parameters?.jsCode) return normalized;
  const precedence = new Function('$input', precedenceNode.parameters.jsCode);
  return precedence({ first: () => ({ json: normalized }) })[0].json;
};

const base = {
  idea_text: 'A workspace that helps founders decide whether an idea deserves further validation.',
  requested_research: ['user_research', 'competitor_research', 'market_research'],
  profile_version: 1,
  founder_inputs: { current_stage: 'IDEA' },
  test_mode: true,
};

const assert = (condition, message) => {
  if (!condition) throw new Error(message);
};

const cases = [];

const discover = run({ ...base, planning_mode: 'DISCOVER', goal_status: 'MISSING' });
assert(discover.needs_input === false, 'Discover must accept a missing goal.');
assert(discover.candidate_tasks.length === 7, 'Discover with all streams must create exactly seven tasks.');
assert(discover.candidate_tasks.every((task) => task.task_key.startsWith('s1_')), 'Discover leaked a later-stage task.');
cases.push(['discover_idea_only', true, discover.candidate_tasks.map((task) => task.task_key)]);

const noGate = run({
  ...base,
  planning_mode: 'PROVE_AND_DESIGN',
  goal_status: 'CONFIRMED',
  goal: { type: 'PAID_CUSTOMERS' },
  gate_context: {},
});
assert(noGate.needs_input === true && noGate.guard_route === 'HUMAN_REVIEW', 'Stage 2 bypassed Gate 1.');
cases.push(['stage2_without_gate', true, noGate.guard_status]);

const missingResearch = run({
  ...base,
  planning_mode: 'PROVE_AND_DESIGN',
  goal_status: 'CONFIRMED',
  goal: { type: 'PAID_CUSTOMERS' },
  gate_context: { decision: 'RUN_MISSING_RESEARCH' },
});
assert(missingResearch.guard_status === 'REPLAN_DISCOVER', 'Missing research did not route back to Discover.');
cases.push(['missing_research_replan', true, missingResearch.guard_route]);

const paused = run({
  ...base,
  planning_mode: 'PROVE_AND_DESIGN',
  goal_status: 'CONFIRMED',
  goal: { type: 'PAID_CUSTOMERS' },
  gate_context: { decision: 'PAUSE_OR_REVISE' },
});
assert(paused.guard_status === 'PAUSED', 'Founder pause did not stop later planning.');
cases.push(['founder_pause', true, paused.guard_status]);

const stage2 = run({
  ...base,
  planning_mode: 'PROVE_AND_DESIGN',
  goal_status: 'CONFIRMED',
  goal: { type: 'PAID_CUSTOMERS' },
  gate_context: { decision: 'PROCEED' },
});
assert(stage2.needs_input === false, 'Valid Gate 1 decision failed.');
assert(stage2.candidate_tasks.some((task) => task.task_key === 's2_financial_readiness'), 'Goal-relevant finance was not selected.');
assert(!stage2.candidate_tasks.some((task) => task.task_key.startsWith('s3_')), 'Stage 2 leaked advisory Stage 3 work.');
cases.push(['stage2_goal_branch', true, stage2.candidate_tasks.filter((task) => task.task_key.startsWith('s2_')).map((task) => task.task_key)]);

const noGate2 = run({
  ...base,
  planning_mode: 'COMPLETE_ACTION_BLUEPRINT',
  goal_status: 'CONFIRMED',
  goal: { type: 'PAID_CUSTOMERS' },
  gate_context: {},
});
assert(noGate2.needs_input === true && noGate2.guard_route === 'HUMAN_REVIEW', 'Action Blueprint bypassed Gate 2.');
cases.push(['action_without_gate2', true, noGate2.guard_status]);

const preTractionGrowth = run({
  ...base,
  planning_mode: 'COMPLETE_ACTION_BLUEPRINT',
  goal_status: 'CONFIRMED',
  goal: { type: 'GROWTH' },
  founder_inputs: { current_stage: 'PRE_LAUNCH', traction_confirmed: false },
  gate_context: { decision: 'PROCEED' },
});
const growth = preTractionGrowth.candidate_tasks.find((task) => task.task_key === 's3_growth_guidance');
assert(growth?.plan_decision === 'NOT_APPLICABLE', 'Pre-traction growth task must not invent measured growth work.');
assert(preTractionGrowth.candidate_tasks.some((task) => task.task_key === 's3_action_blueprint'), 'Action Blueprint task missing after Gate 2.');
assert(!preTractionGrowth.candidate_tasks.some((task) => /weekly/i.test(task.goal) && !/do not[^.]*weekly/i.test(task.goal)), 'A weekly execution schedule leaked into Stage 3.');
cases.push(['pretraction_growth_advisory', true, growth.plan_decision]);

console.log(JSON.stringify({ passed: cases.length, total: cases.length, cases }, null, 2));
