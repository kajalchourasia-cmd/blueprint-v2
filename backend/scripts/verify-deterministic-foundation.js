const fs = require('fs');

const workflowPath = process.argv[2] || 'backend/n8n/BP-STAGE1-01-research-specialist.json';
const workflow = JSON.parse(fs.readFileSync(workflowPath, 'utf8'));
const node = workflow.nodes.find((item) => item.name === 'Build Deterministic Foundation');
if (!node) throw new Error('Build Deterministic Foundation node is missing.');

const fixture = {
  task: { id: 'task-1', task_key: 's1_foundation' },
  idea_text: 'A fitness accountability app for busy professionals.',
  founder_inputs: {
    target_customer: ['Professionals'],
    hours_per_week: 5,
    available_budget: 5000,
    launch_timeline: 'Within 3 months',
    constraints: ['Full-time job'],
    onboarding_answers: {
      customer_detail: 'people training at home',
      location: 'India',
      success_type: 'First paying customers',
      success_definition: '10 paying customers',
      prior_work: ['Compared competitors'],
    },
  },
  correlation_id: 'foundation-contract-test',
};

const execute = new Function('$input', node.parameters.jsCode);
const result = execute({ first: () => ({ json: fixture }) })[0].json;
const output = result.observation?.output || {};
const assertions = {
  completed: result.status === 'COMPLETED',
  foundation_module: result.module_key === 'foundation',
  deterministic_provider: result.provider_trace?.[0]?.provider === 'DETERMINISTIC_FOUNDATION',
  external_search_skipped: result.provider_trace?.some((item) => item.provider === 'YOU' && item.status === 'NOT_REQUIRED'),
  model_skipped: result.provider_trace?.some((item) => item.provider === 'NEBIUS' && item.status === 'NOT_REQUIRED'),
  founder_specific_output: output.target_user_boundary?.includes('Professionals') && output.success_definition === '10 paying customers',
  decision_fields_present: Array.isArray(output.assumptions) && Array.isArray(output.risks) && Array.isArray(output.unknowns),
};

console.log(JSON.stringify({ assertions, output }, null, 2));
if (Object.values(assertions).some((value) => !value)) process.exit(1);
