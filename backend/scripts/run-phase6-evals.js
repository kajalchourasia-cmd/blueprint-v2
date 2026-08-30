const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const suitePath = path.join(root, 'evals', 'phase6-regression-cases.json');
const latestPath = path.join(root, 'evals', 'latest-phase6-results.json');
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

const suite = JSON.parse(fs.readFileSync(suitePath, 'utf8'));

function getPath(value, dotted) {
  if (!dotted) return value;
  return dotted.split('.').reduce((current, key) => current == null ? undefined : current[key], value);
}

function assertOne(actual, assertion) {
  const value = getPath(actual, assertion.path);
  switch (assertion.op) {
    case 'eq': return Object.is(value, assertion.value);
    case 'gt': return Number(value) > Number(assertion.value);
    case 'includes': return Array.isArray(value) && value.includes(assertion.value);
    case 'includesText': return String(value ?? '').includes(String(assertion.value));
    case 'notIncludesText': return !String(value ?? '').includes(String(assertion.value));
    case 'lengthEq': return Array.isArray(value) && value.length === assertion.value;
    case 'anyFieldEq': return Array.isArray(value) && value.some(x => getPath(x, assertion.field) === assertion.value);
    case 'noFieldEq': return Array.isArray(value) && !value.some(x => getPath(x, assertion.field) === assertion.value);
    case 'fieldEq': {
      if (!Array.isArray(value)) return false;
      const item = value.find(x => getPath(x, assertion.field) === assertion.match);
      return item != null && getPath(item, assertion.resultField) === assertion.value;
    }
    case 'fieldArrayIncludes': {
      if (!Array.isArray(value)) return false;
      const item = value.find(x => getPath(x, assertion.field) === assertion.match);
      return item != null && Array.isArray(getPath(item, assertion.resultField))
        && getPath(item, assertion.resultField).includes(assertion.value);
    }
    default: throw new Error(`Unknown assertion operator: ${assertion.op}`);
  }
}

async function runCodeNode(testCase) {
  const workflowPath = path.join(root, 'n8n', testCase.workflow);
  const workflow = JSON.parse(fs.readFileSync(workflowPath, 'utf8'));
  const node = workflow.nodes.find(n => n.name === testCase.node);
  if (!node) throw new Error(`Node not found: ${testCase.workflow} :: ${testCase.node}`);
  if (!node.parameters?.jsCode) throw new Error(`Node is not Code: ${testCase.node}`);
  const inputItems = (testCase.inputs ?? [testCase.input]).map(json => ({ json }));
  const firstJson = inputItems[0]?.json ?? {};
  const $input = { first: () => inputItems[0], all: () => inputItems };
  const $ = name => {
    const mocked = testCase.node_outputs?.[name];
    if (mocked === undefined) throw new Error(`Missing node mock: ${name}`);
    const items = (Array.isArray(mocked) ? mocked : [mocked]).map(json => ({ json }));
    return { first: () => items[0], all: () => items, isExecuted: true };
  };
  const fn = new AsyncFunction('$input', '$json', '$', '$execution', node.parameters.jsCode);
  const started = performance.now();
  const raw = await fn($input, firstJson, $, { id: `eval-${testCase.id}` });
  const durationMs = Math.round((performance.now() - started) * 1000) / 1000;
  const items = Array.isArray(raw) ? raw : [raw];
  return { actual: items[0]?.json ?? items[0], duration_ms: durationMs, item_count: items.length };
}

function structuralChecks() {
  const dir = path.join(root, 'n8n');
  const files = fs.readdirSync(dir).filter(x => x.endsWith('.json'));
  const results = [];
  for (const file of files) {
    const workflow = JSON.parse(fs.readFileSync(path.join(dir, file), 'utf8'));
    const names = new Set(workflow.nodes.map(n => n.name));
    const ids = new Set();
    let okay = true;
    const failures = [];
    for (const node of workflow.nodes) {
      if (ids.has(node.id)) { okay = false; failures.push(`duplicate node id ${node.id}`); }
      ids.add(node.id);
      if (node.parameters?.jsCode) {
        try { new AsyncFunction('$input', '$json', '$', '$execution', node.parameters.jsCode); }
        catch (error) { okay = false; failures.push(`${node.name}: ${error.message}`); }
      }
    }
    for (const [source, groups] of Object.entries(workflow.connections ?? {})) {
      if (!names.has(source)) { okay = false; failures.push(`missing source ${source}`); }
      for (const group of groups.main ?? []) for (const edge of group ?? []) {
        if (!names.has(edge.node)) { okay = false; failures.push(`missing target ${edge.node}`); }
      }
    }
    const production = !/^BP-(SETUP|TEST)/.test(workflow.name)
      && workflow.id !== 'bp90ErrorAudit01';
    if (production && workflow.settings?.errorWorkflow !== 'bp90ErrorAudit01') {
      okay = false; failures.push('missing BP-90 error workflow');
    }
    const serialized = JSON.stringify(workflow);
    if (/sb_secret_[A-Za-z0-9_-]+|Bearer eyJ[A-Za-z0-9_-]+\./.test(serialized)) {
      okay = false; failures.push('possible embedded credential');
    }
    if (/use (?:your|the model.?s) (?:training )?knowledge (?:as|for) (?:a )?fallback/i.test(serialized)) {
      okay = false; failures.push('unsafe evidence fallback');
    }
    results.push({
      id: `structure_${workflow.id}`,
      category: 'STATE',
      status: okay ? 'PASS' : 'FAIL',
      expected: { valid_connections: true, valid_code: true, bounded_error_route: production },
      actual: { workflow: workflow.name, nodes: workflow.nodes.length, failures },
      assertions: failures,
      duration_ms: 0
    });
  }

  const resilienceSql = fs.readFileSync(
    path.join(root, 'supabase', 'migrations', '018_resilience_observability_evals.sql'),
    'utf8'
  );
  const isolationFailures = [];
  if (!/enable row level security/gi.test(resilienceSql)) isolationFailures.push('evaluation tables do not enable RLS');
  if (!/auth\.uid\(\)\)\s*=\s*owner_id/gi.test(resilienceSql)) isolationFailures.push('owner-scoped policy predicate missing');
  if (!/revoke all on public\.eval_suite_runs,public\.eval_case_results from anon/gi.test(resilienceSql)) isolationFailures.push('anonymous table access is not revoked');
  results.push({
    id: 'security_owner_isolation_contract',
    category: 'SECURITY',
    status: isolationFailures.length ? 'FAIL' : 'PASS',
    expected: { rls: true, owner_scope: true, anonymous_access: false },
    actual: { migration: '018_resilience_observability_evals.sql', failures: isolationFailures },
    assertions: isolationFailures,
    duration_ms: 0
  });

  const evalPersistenceFailures = [];
  for (const required of ['eval_suite_runs', 'eval_case_results', 'record_resilience_decision', 'get_run_observability']) {
    if (!resilienceSql.includes(required)) evalPersistenceFailures.push(`missing ${required}`);
  }
  results.push({
    id: 'state_eval_and_observability_contract',
    category: 'STATE',
    status: evalPersistenceFailures.length ? 'FAIL' : 'PASS',
    expected: { durable_eval_summary: true, caught_failure_recording: true, run_observability: true },
    actual: { migration: '018_resilience_observability_evals.sql', failures: evalPersistenceFailures },
    assertions: evalPersistenceFailures,
    duration_ms: 0
  });
  return results;
}

(async () => {
  const startedAt = new Date().toISOString();
  const results = [];
  for (const testCase of suite.cases) {
    try {
      const execution = await runCodeNode(testCase);
      const assertions = testCase.assertions.map(a => ({
        ...a,
        passed: assertOne(execution.actual, a),
        actual_value: getPath(execution.actual, a.path)
      }));
      results.push({
        id: testCase.id,
        category: testCase.category,
        status: assertions.every(x => x.passed) ? 'PASS' : 'FAIL',
        expected: testCase.assertions,
        actual: execution.actual,
        assertions,
        duration_ms: execution.duration_ms
      });
    } catch (error) {
      results.push({
        id: testCase.id,
        category: testCase.category,
        status: 'FAIL',
        expected: testCase.assertions,
        actual: { error: error.message },
        assertions: [],
        duration_ms: 0
      });
    }
  }
  results.push(...structuralChecks());
  const total = results.length;
  const passed = results.filter(x => x.status === 'PASS').length;
  const failed = total - passed;
  const categoryMetrics = {};
  for (const result of results) {
    const metric = categoryMetrics[result.category] ?? { total: 0, passed: 0, failed: 0 };
    metric.total += 1;
    metric[result.status === 'PASS' ? 'passed' : 'failed'] += 1;
    categoryMetrics[result.category] = metric;
  }
  const report = {
    schema_version: 'bp-phase6-eval-report-v1',
    suite_name: suite.suite_name,
    suite_version: suite.suite_version,
    started_at: startedAt,
    completed_at: new Date().toISOString(),
    status: failed === 0 ? 'PASSED' : 'FAILED',
    total_cases: total,
    passed_cases: passed,
    failed_cases: failed,
    completion_rate: total ? passed / total : 0,
    category_metrics: categoryMetrics,
    results
  };
  fs.writeFileSync(latestPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  console.log(`${report.status}: ${passed}/${total} cases passed`);
  for (const result of results.filter(x => x.status === 'FAIL')) {
    console.error(`FAIL ${result.id}: ${JSON.stringify(result.actual)}`);
  }
  process.exitCode = failed === 0 ? 0 : 1;
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
