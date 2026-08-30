const fs = require('fs');

const file = process.argv[2];
if (!file) throw new Error('Usage: node validate_n8n_workflow.js <workflow.json>');
const workflow = JSON.parse(fs.readFileSync(file, 'utf8'));
const names = new Set(workflow.nodes.map((node) => node.name));
const missingTargets = [];
for (const [source, connection] of Object.entries(workflow.connections || {})) {
  for (const output of connection.main || []) {
    for (const edge of output) {
      if (!names.has(edge.node)) missingTargets.push(`${source}->${edge.node}`);
    }
  }
}
const syntaxErrors = [];
for (const node of workflow.nodes.filter((item) => item.type === 'n8n-nodes-base.code')) {
  try {
    new Function(node.parameters.jsCode);
  } catch (error) {
    syntaxErrors.push({ node: node.name, error: error.message });
  }
}
const urls = workflow.nodes
  .filter((node) => node.type === 'n8n-nodes-base.httpRequest')
  .map((node) => node.parameters.url);
const requiredRoles = [
  'Idea Framer', 'Customer Evidence', 'Competitor Intelligence',
  'Market Economics', 'Financial Scenario', 'Independent Evidence Audit',
  'Validation and Distribution', 'Blueprint Synthesis',
];
const result = {
  json_valid: true,
  node_count: workflow.nodes.length,
  unique_node_names: names.size === workflow.nodes.length,
  missing_connection_targets: missingTargets,
  code_syntax_errors: syntaxErrors,
  http_call_count: urls.length,
  unexpected_external_write_urls: urls.filter((url) => /supabase\.co|pinecone\.io/.test(url)),
  missing_required_roles: requiredRoles.filter((role) => !workflow.nodes.some((node) => node.name.includes(role))),
  adaptive_repair_branch: names.has('One Bounded Research Repair?'),
  safe_partial_branch: names.has('Build Safe Partial Blueprint'),
  published: workflow.active,
};
console.log(JSON.stringify(result, null, 2));
if (missingTargets.length || syntaxErrors.length || result.missing_required_roles.length) process.exit(1);
