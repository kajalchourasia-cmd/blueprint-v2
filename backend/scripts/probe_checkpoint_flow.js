// Local integration probe: reuses an authenticated start execution without
// printing its token, resolves the latest pending founder gate, and reports
// only non-secret response fields.
const { DatabaseSync } = require('node:sqlite');
const { parse } = require('/usr/local/lib/node_modules/n8n/node_modules/.pnpm/node_modules/flatted');

const executionId = Number(process.argv[2]);
const requestedDecision = String(process.argv[3] || 'PROCEED').toUpperCase();
if (!Number.isInteger(executionId)) throw new Error('START_EXECUTION_ID_REQUIRED');

const db = new DatabaseSync('/home/node/.n8n/database.sqlite', { readOnly: true });
const row = db.prepare('select data from execution_data where "executionId"=?').get(executionId);
if (!row) throw new Error('START_EXECUTION_NOT_FOUND');
const data = parse(row.data);
const runData = data.resultData?.runData || {};
const dispatch = runData['Prepare Supervisor Start Dispatch']?.at(-1)?.data?.main?.[0]?.[0]?.json;
if (!dispatch?.authorization || !dispatch?.run_id) throw new Error('AUTHENTICATED_DISPATCH_NOT_FOUND');

const supabase = 'https://gudsbrmphrokpnzmrlqd.supabase.co';
const headers = { Authorization: dispatch.authorization, apikey: dispatch.authorization.replace(/^Bearer\s+/i, ''), 'Content-Type': 'application/json' };
// The apikey header above is replaced by the existing public credential at the
// n8n endpoint; Supabase RPC calls accept Authorization plus the project public
// credential. Read it from the workflow credential is intentionally avoided.
delete headers.apikey;

async function rpc(name, body) {
  const response = await fetch(`${supabase}/rest/v1/rpc/${name}`, { method: 'POST', headers: { Authorization: dispatch.authorization, apikey: process.env.SUPABASE_ANON_KEY || '', 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(`${name}:${response.status}:${payload.message || 'FAILED'}`);
  return payload;
}

(async () => {
  // The public key is not available in this standalone container process, so
  // retrieve the owner-scoped context through the locally published endpoint is
  // not possible without the public header. This script is designed to receive
  // SUPABASE_ANON_KEY as an ephemeral environment variable from the caller.
  if (!process.env.SUPABASE_ANON_KEY) throw new Error('SUPABASE_ANON_KEY_ENV_REQUIRED');
  const panel = await rpc('get_founder_control_panel', { p_run_id: dispatch.run_id });
  const context = await rpc('get_supervisor_context', { p_run_id: dispatch.run_id });
  const checkpoint = (panel.panel_items || []).find((item) => item.item_type === 'HUMAN_CHECKPOINT');
  if (!checkpoint) throw new Error('PENDING_CHECKPOINT_NOT_FOUND');
  const allowed = checkpoint.allowed_decisions || [];
  const decision = allowed.includes(requestedDecision) ? requestedDecision : allowed[0];
  const response = await fetch('http://127.0.0.1:5678/webhook/blueprint/checkpoint', {
    method: 'POST', headers: { Authorization: dispatch.authorization, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      checkpoint_id: checkpoint.checkpoint_id,
      expected_state_version: checkpoint.state_version,
      decision,
      decision_payload: { founder_note: 'Automated local closed-loop integration probe.' },
      project_id: dispatch.project_id,
      run_id: dispatch.run_id,
      profile_version: dispatch.profile_version,
      idea_text: dispatch.idea_text,
      profile: context.current_blueprint?.blueprint?.starting_position || dispatch.profile,
      requested_research: dispatch.requested_research,
      correlation_id: `checkpoint-probe-${Date.now()}`,
    }),
  });
  const result = await response.json().catch(() => ({}));
  console.log(JSON.stringify({ http_status: response.status, ok: result.ok, status: result.status, route: result.route, decision: result.decision, planning_mode: result.planning_mode, run_id: result.run_id, state_version: result.state_version }, null, 2));
  if (!response.ok || !result.ok) process.exitCode = 1;
})().catch((error) => { console.error(error.message); process.exitCode = 1; });
