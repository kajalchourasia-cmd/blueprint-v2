const fs = require('fs');

const files = process.argv.slice(2);
if (!files.length) throw new Error('Provide one or more workflow JSON files');

let failed = false;
for (const file of files) {
  const workflow = JSON.parse(fs.readFileSync(file, 'utf8'));
  const names = new Set(workflow.nodes.map((node) => node.name));
  const missingTargets = [];
  const codeSyntaxErrors = [];
  for (const [source, connection] of Object.entries(workflow.connections || {})) {
    if (!names.has(source)) missingTargets.push(`missing source:${source}`);
    for (const output of connection.main || []) {
      for (const edge of output) if (!names.has(edge.node)) missingTargets.push(`${source}->${edge.node}`);
    }
  }
  for (const item of workflow.nodes.filter((node) => node.type === 'n8n-nodes-base.code')) {
    try { new Function(item.parameters.jsCode); }
    catch (error) { codeSyntaxErrors.push({ node: item.name, error: error.message }); }
  }
  const executeTargets = workflow.nodes
    .filter((item) => item.type === 'n8n-nodes-base.executeWorkflow')
    .map((item) => item.parameters.workflowId?.value ?? null);
  const externalWrites = workflow.nodes
    .filter((item) => item.type === 'n8n-nodes-base.httpRequest')
    .filter((item) => ['POST', 'PUT', 'PATCH', 'DELETE'].includes(item.parameters.method ?? 'GET'))
    .map((item) => item.parameters.url)
    .filter((url) => !/chat\/completions|rest\/v1\/rpc\/(get_supervisor_context|start_blueprint_run|persist_supervisor_result|append_chat_exchange)$/.test(url));
  const result = {
    file,
    workflow_id: workflow.id,
    node_count: workflow.nodes.length,
    unique_node_names: names.size === workflow.nodes.length,
    missing_connection_targets: missingTargets,
    code_syntax_errors: codeSyntaxErrors,
    subworkflow_targets: executeTargets,
    unexpected_external_write_urls: externalWrites,
    has_error_workflow: workflow.settings?.errorWorkflow === 'bp90ErrorAudit01',
    active: workflow.active,
  };
  console.log(JSON.stringify(result, null, 2));
  if (!result.unique_node_names || missingTargets.length || codeSyntaxErrors.length || externalWrites.length || !result.has_error_workflow || result.active) failed = true;
}
if (failed) process.exit(1);
