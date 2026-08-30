const { DatabaseSync } = require('node:sqlite');

const executionId = Number(process.argv[2]);
if (!Number.isInteger(executionId)) throw new Error('Execution ID is required');
const db = new DatabaseSync('/home/node/.n8n/database.sqlite', { readOnly: true });
for (const table of ['execution_entity', 'execution_data']) {
  console.log(table, db.prepare(`pragma table_info(${table})`).all().map((row) => row.name));
}
console.log('entity', db.prepare(
  'select id, status, "startedAt", "stoppedAt", mode, "workflowId" from execution_entity where id=?',
).get(executionId));
const row = db.prepare('select * from execution_data where "executionId"=?').get(executionId);
if (!row) throw new Error('Execution data not found');
console.log('data_columns', Object.fromEntries(Object.entries(row).map(([key, value]) => [key, typeof value === 'string' ? value.length : value])));
for (const [key, value] of Object.entries(row)) {
  if (typeof value === 'string' && value.length < 2000) console.log(key, value);
}

const { parse } = require('/usr/local/lib/node_modules/n8n/node_modules/.pnpm/node_modules/flatted');
const parsed = parse(row.data);
console.log('parsed_keys', Object.keys(parsed));
const runData = parsed.resultData?.runData || parsed.runData || {};
console.log('run_nodes', Object.keys(runData));
const requestedNodes = process.argv.slice(3);
const selectedNodes = requestedNodes.length ? requestedNodes : [
  'You — Customer Demand Search', 'You — Competitor Search', 'You — Market Search',
  'Normalize Evidence Cards', 'You — One Repair Search', 'Build Safe Partial Blueprint',
];
for (const name of selectedNodes) {
  const runs = runData[name] || [];
  const last = runs[runs.length - 1];
  const items = last?.data?.main?.[0] || [];
  console.log(`\nNODE ${name}`, JSON.stringify({ status: last?.executionStatus, error: last?.error, items: items.length }, null, 2));
  if (items[0]?.json) {
    const text = JSON.stringify(items[0].json, null, 2);
    console.log(text.slice(0, 12000));
  }
}
