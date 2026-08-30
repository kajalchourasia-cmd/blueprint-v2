const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const files = [
  'n8n/BP-AUDIT-01-independent-evidence-auditor.json',
  'n8n/BP-SYNTH-01-research-blueprint.json',
  'n8n/BP-STAGE1-ROUTER-01.json',
  'n8n/BP-SUPERVISOR-REEVAL-01.json',
  'n8n/BP-HITL-01-checkpoint-resume.json',
  'n8n/BP-SCHED-01-eligible-task-scheduler.json',
  'n8n/BP-PLAN-01-dynamic-task-planner.json',
  'n8n/BP-PINE-01-accepted-evidence-memory.json',
  'n8n/BP-MEM0-01-founder-journey-memory.json',
  'n8n/BP-RERUN-01-profile-impact-rerun.json',
  'n8n/BP-RESILIENCE-01-failure-route-observability.json',
];

let failed = false;
for (const rel of files) {
  const workflow = JSON.parse(fs.readFileSync(path.join(root, rel), 'utf8'));
  const names = new Set(workflow.nodes.map((n) => n.name));
  const ids = new Set();
  for (const node of workflow.nodes) {
    if (ids.has(node.id)) throw new Error(`${rel}: duplicate node id ${node.id}`);
    ids.add(node.id);
    const code = node.parameters?.jsCode;
    if (code) new AsyncFunction('$input', '$json', '$', code);
  }
  for (const [source, groups] of Object.entries(workflow.connections || {})) {
    if (!names.has(source)) throw new Error(`${rel}: missing connection source ${source}`);
    for (const group of groups.main || []) {
      for (const edge of group || []) {
        if (!names.has(edge.node)) throw new Error(`${rel}: missing connection target ${edge.node}`);
      }
    }
  }
  console.log(`PASS ${rel}: ${workflow.nodes.length} nodes, valid code and connections`);
}

const planner = JSON.parse(fs.readFileSync(path.join(root, 'n8n/BP-PLAN-01-dynamic-task-planner.json'), 'utf8'));
if (!planner.nodes.some((n) => n.name === 'Finalize Stage 1 Data Dependencies')) {
  failed = true;
  console.error('FAIL planner does not bind all audited research dependencies to synthesis');
}

const schedulerText = fs.readFileSync(path.join(root, 'n8n/BP-SCHED-01-eligible-task-scheduler.json'), 'utf8');
for (const module of ['evidence_audit', 'research_verdict', 'final_blueprint']) {
  if (!schedulerText.includes(`'${module}'`)) {
    failed = true;
    console.error(`FAIL scheduler missing ${module}`);
  }
}
if (!schedulerText.includes('bpStage1Router01')) {
  failed = true;
  console.error('FAIL scheduler is not bound to the typed worker router');
}

const supervisorText = fs.readFileSync(path.join(root, 'n8n/BP-SUPERVISOR-REEVAL-01.json'), 'utf8');
if (!supervisorText.includes('n>=20') || supervisorText.includes('n>=25')) {
  failed = true;
  console.error('FAIL Supervisor transition cap is not aligned to the database limit of 20');
}

if (failed) process.exit(1);
console.log('PASS Phase 6B structural contract');
