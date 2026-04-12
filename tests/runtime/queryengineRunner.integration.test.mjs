import assert from 'node:assert/strict';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
process.env.BASE_DIR = projectRoot;
process.env.NODE_RUNNER_BASE_DIR = projectRoot;
const packageModule = await import(pathToFileURL(path.join(projectRoot, 'scripts', 'package-queryengine.mjs')).href);
packageModule.packageQueryEngine();
const packagedCandidatePath = path.join(projectRoot, 'dist', 'QueryEngine.js');

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
const validExecution = await runnerModule.tryRunExistingQueryEngineDetailed({
  message: valid.message,
  memoryContext: { user: valid.memory, agentMemory: '' },
  history: valid.history,
  summary: valid.summary,
  capabilities: valid.capabilities,
  session: valid.session,
  cwd: projectRoot,
});
assert.equal(validExecution.selectedCandidate, packagedCandidatePath);
assert.equal(typeof validExecution.result.response, 'string');
assert.ok(validExecution.result.response.trim().length > 0);
assert.equal(validExecution.result.metadata?.engine_mode, 'packaged_upstream');
assert.equal(validExecution.result.metadata?.engine_reason, 'dist_candidate_selected');

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
const legacyExecution = await runnerModule.tryRunExistingQueryEngineDetailed({
  message: legacy.message,
  memoryContext: { user: legacy.memory, agentMemory: '' },
  history: legacy.history,
  summary: legacy.summary,
  capabilities: legacy.capabilities,
  session: legacy.session,
  cwd: projectRoot,
});
assert.equal(legacyExecution.selectedCandidate, packagedCandidatePath);
const legacyPayload = legacyExecution.result;
assert.equal(typeof legacyPayload.execution_request, 'object');
assert.ok(Array.isArray(legacyPayload.execution_request.actions));
assert.equal(legacyPayload.metadata?.engine_mode, 'authority_fallback');
assert.equal(legacyPayload.metadata?.engine_reason, 'fallback_policy_triggered');

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
const phase10Execution = await runnerModule.tryRunExistingQueryEngineDetailed({
  message: phase10Safe.message,
  memoryContext: { user: phase10Safe.memory, agentMemory: '' },
  history: phase10Safe.history,
  summary: phase10Safe.summary,
  capabilities: phase10Safe.capabilities,
  session: phase10Safe.session,
  cwd: projectRoot,
});
assert.equal(phase10Execution.selectedCandidate, packagedCandidatePath);
const phase10Payload = phase10Execution.result;
assert.equal(typeof phase10Payload.execution_request.repository_analysis, 'object');
assert.equal(typeof phase10Payload.execution_request.milestone_plan, 'object');
assert.equal(phase10Payload.metadata?.engine_mode, 'authority_fallback');
assert.equal(phase10Payload.metadata?.engine_reason, 'fallback_policy_triggered');

console.log('queryengine runner integration tests: ok');
