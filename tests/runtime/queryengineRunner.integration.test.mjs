import assert from 'node:assert/strict';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
process.env.BASE_DIR = projectRoot;
process.env.NODE_RUNNER_BASE_DIR = projectRoot;

const runnerModule = await import(pathToFileURL(path.join(projectRoot, 'js-runner', 'queryEngineRunner.js')).href);

const valid = runnerModule.safeParsePayload(JSON.stringify({
  message: 'ola',
  memory: {},
  history: [],
  summary: '',
  capabilities: [],
  session: { session_id: 'fase2-runner' },
}));
assert.equal(valid.message, 'ola');
const validResponse = await runnerModule.tryRunExistingQueryEngine({
  message: valid.message,
  memoryContext: { user: valid.memory, agentMemory: '' },
  history: valid.history,
  summary: valid.summary,
  capabilities: valid.capabilities,
  session: valid.session,
  cwd: projectRoot,
});
assert.ok(validResponse.trim().length > 0);

const legacy = runnerModule.safeParsePayload(JSON.stringify({
  message: 'leia package.json',
  memory: {},
  history: [],
  summary: '',
  capabilities: [],
  session: { session_id: 'fase2-legacy', executor_bridge: 'python-rust' },
  plan_kind: 'linear',
  milestone_plan: { ignored: true },
}));
const legacyResponse = await runnerModule.tryRunExistingQueryEngine({
  message: legacy.message,
  memoryContext: { user: legacy.memory, agentMemory: '' },
  history: legacy.history,
  summary: legacy.summary,
  capabilities: legacy.capabilities,
  session: legacy.session,
  cwd: projectRoot,
});
const legacyPayload = JSON.parse(legacyResponse);
assert.equal(typeof legacyPayload.execution_request, 'object');
assert.ok(Array.isArray(legacyPayload.execution_request.actions));

const malformed = runnerModule.safeParsePayload('{not-json');
assert.equal(malformed.message, '');
assert.deepEqual(malformed.history, []);

const phase10Safe = runnerModule.safeParsePayload(JSON.stringify({
  message: 'analise o repositorio e corrija os testes com seguranca',
  memory: {},
  history: [],
  summary: '',
  capabilities: [],
  session: {
    session_id: 'fase2-phase10',
    runtime_mode: 'python-rust-cargo',
    milestone_plan: { preexisting: true },
    repository_analysis: { preexisting: true },
  },
}));
const phase10Response = await runnerModule.tryRunExistingQueryEngine({
  message: phase10Safe.message,
  memoryContext: { user: phase10Safe.memory, agentMemory: '' },
  history: phase10Safe.history,
  summary: phase10Safe.summary,
  capabilities: phase10Safe.capabilities,
  session: phase10Safe.session,
  cwd: projectRoot,
});
const phase10Payload = JSON.parse(phase10Response);
assert.equal(typeof phase10Payload.execution_request.repository_analysis, 'object');
assert.equal(typeof phase10Payload.execution_request.milestone_plan, 'object');

console.log('queryengine runner integration tests: ok');
