import assert from 'node:assert/strict';
import path from 'path';
import { fileURLToPath } from 'url';
import { pathToFileURL } from 'node:url';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
process.env.BASE_DIR = projectRoot;
process.env.NODE_RUNNER_BASE_DIR = projectRoot;
process.env.OMINI_QUERY_ENGINE_ORDER = 'adapter_first';

const runnerModule = await import(pathToFileURL(path.join(projectRoot, 'js-runner', 'queryEngineRunner.js')).href);

const payload = runnerModule.safeParsePayload(
  JSON.stringify({
    message:
      'analise esse repositorio e aponte riscos obvios de arquitetura sem usar atalho conversacional',
    memory: { nome: 'Tester', preferencias: ['SaaS B2B'] },
    history: [],
    summary: '',
    capabilities: [],
    session: { session_id: 'adapter-first-smoke' },
  }),
);

const execution = await runnerModule.tryRunExistingQueryEngineDetailed({
  message: payload.message,
  memoryContext: { user: payload.memory, agentMemory: '' },
  history: payload.history,
  summary: payload.summary,
  capabilities: payload.capabilities,
  session: payload.session,
  cwd: projectRoot,
});

assert.ok(execution.result, 'expected engine result');
assert.match(
  String(execution.selectedCandidate || ''),
  /queryEngineRunnerAdapter\.(js|mjs)$/,
  `expected fusion adapter, got ${execution.selectedCandidate}`,
);
assert.equal(execution.result.metadata?.engine_mode, 'fusion_authority');
assert.equal(execution.result.metadata?.engine_reason, 'adapter_path_selected');
const text = String(execution.result.response || '');
assert.ok(
  !text.startsWith('[degraded:node_runner]'),
  'node runner should not emit technical fallback for normal adapter path',
);
assert.ok(text.length > 40, 'expected substantive local response');

console.log('adapter-first-runner: ok');
