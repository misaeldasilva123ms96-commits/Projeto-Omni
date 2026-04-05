const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const { runQueryEngine } = require('../../core/brain/fusionBrain');
const { resolveExecutionMode, EXECUTION_MODES } = require('../../runtime/execution/runtimeMode');
const { chooseProvider } = require('../../platform/providers/providerRouter');
const { createPermissionPolicy, PermissionMode, authorizeExecution } = require('../../runtime/permissions/permissionBridge');
const { recordRuntimeArtifacts, recordSemanticEntry } = require('../../storage/memory/runtimeMemoryStore');

async function main() {
  const result = await runQueryEngine({
    message: 'ola',
    memoryContext: { user: {} },
    history: [],
    summary: '',
    capabilities: [],
    session: { session_id: 'test-session' },
    cwd: process.cwd(),
  });

  assert.equal(typeof result.response, 'string');
  assert.equal(typeof result.confidence, 'number');
  assert.equal(typeof result.memory, 'object');
  assert.match(result.response.toLowerCase(), /olá|ola/);

  const provider = chooseProvider({ complexity: 'complex' });
  assert.equal(provider.name, 'local-heuristic');

  const policy = createPermissionPolicy({
    defaultMode: PermissionMode.PROMPT,
    toolModes: { file_delete: PermissionMode.DENY },
  });

  const permissionResult = authorizeExecution({
    policy,
    toolName: 'file_delete',
    input: '{}',
  });

  assert.equal(permissionResult.allowed, false);
  assert.match(permissionResult.reason, /denied/i);

  const delegated = await runQueryEngine({
    message: 'leia package.json',
    memoryContext: { user: {} },
    history: [],
    summary: '',
    capabilities: [],
    session: { session_id: 'delegation-test', executor_bridge: 'python-rust' },
    cwd: process.cwd(),
  });

  assert.equal(typeof delegated.execution_request, 'object');
  assert.equal(Array.isArray(delegated.execution_request.actions), true);
  assert.equal(delegated.execution_request.actions[0].selected_agent, 'researcher_agent');
  assert.equal(delegated.execution_request.actions[0].selected_tool, 'read_file');
  assert.equal(delegated.execution_request.mode.startsWith('python-rust'), true);

  const multiStep = await runQueryEngine({
    message: 'liste os arquivos e leia package.json',
    memoryContext: { user: {} },
    history: [],
    summary: '',
    capabilities: [],
    session: { session_id: 'multi-step-test', runtime_mode: EXECUTION_MODES.PYTHON_RUST_CARGO },
    cwd: process.cwd(),
  });

  assert.equal(typeof multiStep.execution_request, 'object');
  assert.equal(multiStep.execution_request.actions.length >= 2, true);
  assert.equal(multiStep.execution_request.actions[0].selected_tool, 'glob_search');
  assert.equal(multiStep.execution_request.actions[1].selected_tool, 'read_file');
  assert.equal(multiStep.execution_request.delegation.delegates.includes('task_planner'), true);
  assert.equal(multiStep.execution_request.delegation.delegates.includes('reviewer_agent'), true);

  recordRuntimeArtifacts(process.cwd(), 'memory-recall-test', [{ kind: 'file', path: 'package.json', preview: '' }]);
  const memoryGuided = await runQueryEngine({
    message: 'leia de novo',
    memoryContext: { user: {} },
    history: [],
    summary: '',
    capabilities: [],
    session: { session_id: 'memory-recall-test', runtime_mode: EXECUTION_MODES.PYTHON_RUST_CARGO },
    cwd: process.cwd(),
  });
  assert.equal(memoryGuided.execution_request.actions[0].tool_arguments.path, 'package.json');

  recordSemanticEntry(process.cwd(), 'semantic-test', {
    path: 'package.json',
    preview: 'Production package for the Omini Node runner and schema validation.',
    source: 'test',
  });
  const semanticGuided = await runQueryEngine({
    message: 'analise o arquivo sobre schema validation',
    memoryContext: { user: {} },
    history: [],
    summary: '',
    capabilities: [],
    session: { session_id: 'semantic-test', runtime_mode: EXECUTION_MODES.PYTHON_RUST_CARGO },
    cwd: process.cwd(),
  });
  assert.equal(semanticGuided.execution_request.actions[0].tool_arguments.path, 'package.json');
  assert.equal(Array.isArray(semanticGuided.execution_request.semantic_retrieval), true);
  assert.equal(semanticGuided.execution_request.semantic_retrieval[0].path, 'package.json');

  const runtimeMode = resolveExecutionMode({
    cwd: process.cwd(),
    requestedMode: EXECUTION_MODES.PYTHON_RUST_CARGO,
  });
  assert.equal(runtimeMode.primary.mode, EXECUTION_MODES.PYTHON_RUST_CARGO);
  assert.equal(runtimeMode.fallback, null);

  const cwd = process.cwd();
  const auditPath = path.join(cwd, '.logs', 'fusion-runtime', 'execution-audit.jsonl');
  const before = fs.existsSync(auditPath) ? fs.readFileSync(auditPath, 'utf8').split('\n').filter(Boolean).length : 0;

  await runQueryEngine({
    message: 'btc',
    memoryContext: { user: {} },
    history: [],
    summary: '',
    capabilities: [],
    session: { session_id: 'audit-session' },
    cwd,
  });

  const after = fs.readFileSync(auditPath, 'utf8').split('\n').filter(Boolean).length;
  assert.ok(after > before);
  console.log('fusion tests: ok');
}

main().catch(error => {
  console.error(error);
  process.exit(1);
});
