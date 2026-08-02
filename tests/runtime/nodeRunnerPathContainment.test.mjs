import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const require = createRequire(import.meta.url);
const policy = require('../../js-runner/pathPolicy.js');

function makeFixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'omni-node-policy-'));
  for (const relative of ['backend/python', 'backend/rust', 'js-runner', 'contract', 'src']) {
    fs.mkdirSync(path.join(root, relative), { recursive: true });
  }
  fs.writeFileSync(path.join(root, 'package.json'), '{}');
  fs.writeFileSync(path.join(root, 'contract/runner-schema.v1.json'), '{}');
  fs.copyFileSync(path.join(projectRoot, 'js-runner/pathPolicy.js'), path.join(root, 'js-runner/pathPolicy.js'));
  fs.copyFileSync(path.join(projectRoot, 'js-runner/queryEngineRunner.js'), path.join(root, 'js-runner/queryEngineRunner.js'));
  fs.writeFileSync(path.join(root, 'src/queryEngineRunnerAdapter.js'), 'module.exports.runQueryEngine = async () => ({response:"ok"});');
  return root;
}

function fixturePolicy(root) {
  const fixtureRequire = createRequire(path.join(root, 'js-runner/queryEngineRunner.js'));
  return fixtureRequire('./pathPolicy.js');
}

test('code-derived root accepts matching controls and rejects both mismatches', () => {
  assert.equal(policy.getAuthoritativeRoot({ BASE_DIR: projectRoot, NODE_RUNNER_BASE_DIR: projectRoot }), projectRoot);
  assert.throws(() => policy.getAuthoritativeRoot({ BASE_DIR: path.dirname(projectRoot) }), /node_project_root_invalid/);
  assert.throws(() => policy.getAuthoritativeRoot({ NODE_RUNNER_BASE_DIR: path.dirname(projectRoot) }), /node_project_root_invalid/);
});

test('schema and adapter overrides must resolve to exact allow-listed files', () => {
  const external = path.join(os.tmpdir(), 'external-runner-artifact.json');
  fs.writeFileSync(external, '{}');
  assert.throws(() => policy.validateConfiguredArtifact('RUNNER_SCHEMA_PATH', ['schema'], { RUNNER_SCHEMA_PATH: external }), /node_path_policy_violation/);
  assert.throws(() => policy.validateConfiguredArtifact('RUNNER_ADAPTER_PATH', ['adapter_js'], { RUNNER_ADAPTER_PATH: external }), /node_path_policy_violation/);
  fs.rmSync(external, { force: true });
});

test('security artifacts reject symlinks even when the target remains inside the root', t => {
  const root = makeFixture();
  const localPolicy = fixturePolicy(root);
  const target = path.join(root, 'src/queryEngineRunnerAdapter.js');
  const link = path.join(root, 'src/queryEngineRunnerAdapter.mjs');
  try {
    fs.symlinkSync(target, link, 'file');
  } catch (error) {
    fs.rmSync(root, { recursive: true, force: true });
    t.skip(`symlink unavailable: ${error.code}`);
    return;
  }
  assert.throws(() => localPolicy.validateAllowedFile('adapter_mjs'), /node_adapter_mjs_unsafe|node_path_policy_violation/);
  assert.equal(localPolicy.validateAllowedFile('adapter_js'), target);
  fs.mkdirSync(path.join(root, 'dist'), { recursive: true });
  fs.symlinkSync(target, path.join(root, 'dist/QueryEngine.js'), 'file');
  assert.throws(() => localPolicy.validateAllowedFile('dist_query_engine', { required: false }), /node_dist_query_engine_unsafe|node_path_policy_violation/);
  fs.rmSync(root, { recursive: true, force: true });
});

test('runner process fails closed on external schema and adapter overrides without disclosing paths', () => {
  for (const key of ['RUNNER_SCHEMA_PATH', 'RUNNER_ADAPTER_PATH']) {
    const result = spawnSync(process.execPath, ['js-runner/queryEngineRunner.js'], {
      cwd: projectRoot,
      env: { ...process.env, BASE_DIR: projectRoot, NODE_RUNNER_BASE_DIR: projectRoot, [key]: os.tmpdir() },
      encoding: 'utf8',
      input: JSON.stringify({ message: 'test', memory: {}, history: [], summary: '', capabilities: [], session: {} }),
    });
    assert.equal(result.status, 0);
    assert.match(JSON.parse(result.stdout).response, /^\[degraded:node_runner\]/);
    assert.equal(`${result.stdout}${result.stderr}`.includes(os.tmpdir()), false);
  }
});

test('candidate diagnostics use safe labels and Node ignores arbitrary loader opt-in', async () => {
  assert.equal(policy.labelForPath(path.join(projectRoot, 'dist/QueryEngine.js')), 'dist_query_engine');
  const runner = require('../../js-runner/queryEngineRunner.js');
  assert.equal(runner.hasConfiguredTypescriptLoader({ OMNI_QUERY_ENGINE_TYPESCRIPT_LOADER_ENABLED: 'true', NODE_OPTIONS: '--loader=x' }, ['--loader=x']), false);
  const execution = await runner.tryRunExistingQueryEngineDetailed({ message: 'test', memoryContext: {}, history: [], summary: '', capabilities: [], session: {}, cwd: projectRoot });
  assert.ok(execution.attemptedCandidates.every(candidate => !path.isAbsolute(candidate)));
  assert.ok(execution.candidateErrors.every(item => !path.isAbsolute(item.candidate)));
  const forwardedCandidates = runner.getQueryEngineCandidates({ Forwarded: 'for=/external/evil.js' }, { node: process.versions.node }, []);
  assert.ok(forwardedCandidates.every(candidate => policy.labelForPath(candidate) !== 'unauthorized_candidate'));
});

test('memory traversal is deterministic and bounded by depth, entries, files, and symlinks', t => {
  const root = makeFixture();
  const memory = path.join(root, '.claude/agent-memory');
  fs.mkdirSync(memory, { recursive: true });
  for (let index = 0; index < 80; index += 1) {
    const dir = path.join(memory, `d-${String(index).padStart(3, '0')}`);
    fs.mkdirSync(dir);
    fs.writeFileSync(path.join(dir, 'MEMORY.md'), `memory-${index}`);
  }
  let deep = memory;
  for (let index = 0; index < 10; index += 1) {
    deep = path.join(deep, `deep-${index}`);
    fs.mkdirSync(deep);
  }
  fs.writeFileSync(path.join(deep, 'MEMORY.md'), 'too-deep');
  try {
    fs.symlinkSync(os.tmpdir(), path.join(memory, 'external'), 'junction');
    fs.symlinkSync(path.join(os.tmpdir(), 'external-memory.md'), path.join(memory, 'MEMORY.md'), 'file');
  } catch (error) {
    if (error.code !== 'EPERM') throw error;
    t.diagnostic('junction creation unavailable; remaining traversal bounds still verified');
  }
  const localRunner = createRequire(path.join(root, 'js-runner/queryEngineRunner.js'))('./queryEngineRunner.js');
  const first = localRunner.collectMemoryFiles(memory);
  const second = localRunner.collectMemoryFiles(memory);
  assert.deepEqual(first, second);
  assert.ok(first.length <= 64);
  assert.equal(first.some(file => file.includes('deep-8') || file.includes('external')), false);
  fs.rmSync(root, { recursive: true, force: true });
});

test('memory entry-count guard terminates a tree larger than 512 entries', () => {
  const root = makeFixture();
  const memory = path.join(root, '.claude/agent-memory');
  fs.mkdirSync(memory, { recursive: true });
  for (let index = 0; index < 520; index += 1) {
    fs.writeFileSync(path.join(memory, `entry-${String(index).padStart(3, '0')}.txt`), 'bounded');
  }
  const localRunner = createRequire(path.join(root, 'js-runner/queryEngineRunner.js'))('./queryEngineRunner.js');
  assert.deepEqual(localRunner.collectMemoryFiles(memory), []);
  fs.rmSync(root, { recursive: true, force: true });
});

test('symlinked memory root is rejected without reading its external target', t => {
  const root = makeFixture();
  const external = fs.mkdtempSync(path.join(os.tmpdir(), 'omni-external-memory-'));
  fs.mkdirSync(path.join(root, '.claude'), { recursive: true });
  fs.writeFileSync(path.join(external, 'MEMORY.md'), 'must-not-read');
  try {
    fs.symlinkSync(external, path.join(root, '.claude/agent-memory'), 'junction');
  } catch (error) {
    fs.rmSync(root, { recursive: true, force: true });
    fs.rmSync(external, { recursive: true, force: true });
    t.skip(`junction unavailable: ${error.code}`);
    return;
  }
  const localPolicy = fixturePolicy(root);
  assert.throws(() => localPolicy.validateMemoryRoot('.claude/agent-memory', { BASE_DIR: root, NODE_RUNNER_BASE_DIR: root }), /node_memory_root_invalid|node_path_policy_violation/);
  fs.rmSync(root, { recursive: true, force: true });
  fs.rmSync(external, { recursive: true, force: true });
});

test('agent memory honors the 16 KiB aggregate bound and public demo disables reads', () => {
  const root = makeFixture();
  const memory = path.join(root, '.claude/agent-memory');
  fs.mkdirSync(memory, { recursive: true });
  for (let index = 0; index < 40; index += 1) {
    const dir = path.join(memory, `memory-${String(index).padStart(2, '0')}`);
    fs.mkdirSync(dir);
    fs.writeFileSync(path.join(dir, 'MEMORY.md'), 'x'.repeat(1024));
  }
  const previous = Object.fromEntries(['BASE_DIR', 'NODE_RUNNER_BASE_DIR', 'OMNI_ENABLE_AGENT_MEMORY', 'OMNI_PUBLIC_DEMO_MODE'].map(key => [key, process.env[key]]));
  Object.assign(process.env, { BASE_DIR: root, NODE_RUNNER_BASE_DIR: root, OMNI_ENABLE_AGENT_MEMORY: 'true', OMNI_PUBLIC_DEMO_MODE: 'false' });
  const localRunner = createRequire(path.join(root, 'js-runner/queryEngineRunner.js'))('./queryEngineRunner.js');
  const context = localRunner.loadAgentMemoryContext();
  assert.ok(Buffer.byteLength(context, 'utf8') <= 16 * 1024);
  assert.match(context, /x{32}/);
  process.env.OMNI_PUBLIC_DEMO_MODE = 'true';
  assert.equal(localRunner.loadAgentMemoryContext(), '');
  for (const [key, value] of Object.entries(previous)) {
    if (value === undefined) delete process.env[key]; else process.env[key] = value;
  }
  fs.rmSync(root, { recursive: true, force: true });
});
