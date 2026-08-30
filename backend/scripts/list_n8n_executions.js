const { DatabaseSync } = require('node:sqlite');

const limit = Math.max(1, Math.min(100, Number(process.argv[2] || 30)));
const db = new DatabaseSync('/home/node/.n8n/database.sqlite', { readOnly: true });
const rows = db.prepare(
  'select e.id,e.status,e."startedAt",e."stoppedAt",e.mode,e."workflowId",w.name ' +
  'from execution_entity e left join workflow_entity w on w.id=e."workflowId" ' +
  'order by e.id desc limit ?',
).all(limit);
console.log(JSON.stringify(rows, null, 2));
