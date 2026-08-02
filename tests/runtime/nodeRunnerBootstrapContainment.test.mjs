import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const payload = JSON.stringify({
  message: 'bootstrap-test',
  memory: {},
  history: [],
  summary: '',
  capabilities: [],
  session: {},
});

function makeFixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'omni-node-bootstrap-'));
  for (const relative of ['backend/python', 'backend/rust', 'js-runner', 'contract', 'src', 'core/brain']) {
    fs.mkdirSync(path.join(root, relative), { recursive: true });
  }
  fs.writeFileSync(path.join(root, 'package.json'), '{}');
  fs.copyFileSync(path.join(projectRoot, 'contract/runner-schema.v1.json'), path.join(root, 'contract/runner-schema.v1.json'));
  for (const name of ['pathPolicy.js', 'queryEngineRunner.js', 'runtimeHealthcheck.js']) {
    fs.copyFileSync(path.join(projectRoot, 'js-runner', name), path.join(root, 'js-runner', name));
  }
  fs.writeFileSync(path.join(root, 'core/brain/fusionBrain.js'), 'module.exports = {};');
  fs.writeFileSync(
    path.join(root, 'src/queryEngineRunnerAdapter.js'),
    "require('../core/brain/fusionBrain.js'); module.exports.runQueryEngine = async () => ({response:'fixture-ok'});",
  );
  return root;
}

function runEntrypoint(root, entrypoint) {
  return spawnSync(process.execPath, [path.join(root, 'js-runner', entrypoint)], {
    cwd: root,
    env: {
      ...process.env,
      BASE_DIR: root,
      NODE_RUNNER_BASE_DIR: root,
      OMNI_BASE_DIR: root,
      NODE_OPTIONS: '',
      NODE_PATH: '',
    },
    encoding: 'utf8',
    input: entrypoint === 'queryEngineRunner.js' ? payload : undefined,
  });
}

function makeSentinelModule(modulePath, sentinelPath) {
  fs.writeFileSync(
    modulePath,
    `require('node:fs').writeFileSync(${JSON.stringify(sentinelPath)}, 'executed'); module.exports = {};`,
  );
}

function assertTargetPathRedacted(result, externalPath) {
  const combined = `${result.stdout}${result.stderr}`;
  assert.equal(combined.includes(externalPath), false);
  assert.equal(combined.includes(path.dirname(externalPath)), false);
}

for (const entrypoint of ['queryEngineRunner.js', 'runtimeHealthcheck.js']) {
  test(`${entrypoint} accepts the normal validated policy module`, () => {
    const root = makeFixture();
    const result = runEntrypoint(root, entrypoint);
    assert.equal(result.status, 0, result.stderr);
    const output = JSON.parse(result.stdout);
    if (entrypoint === 'queryEngineRunner.js') assert.equal(output.response, 'fixture-ok');
    else assert.equal(output.runner_exists, true);
    fs.rmSync(root, { recursive: true, force: true });
  });

  test(`${entrypoint} rejects an external policy symlink before its sentinel executes`, t => {
    const root = makeFixture();
    const external = fs.mkdtempSync(path.join(os.tmpdir(), 'omni-external-policy-'));
    const externalModule = path.join(external, 'externalPolicy.js');
    const sentinel = path.join(external, 'sentinel-created');
    makeSentinelModule(externalModule, sentinel);
    const policyPath = path.join(root, 'js-runner/pathPolicy.js');
    fs.rmSync(policyPath);
    try {
      fs.symlinkSync(externalModule, policyPath, 'file');
    } catch (error) {
      fs.rmSync(root, { recursive: true, force: true });
      fs.rmSync(external, { recursive: true, force: true });
      t.skip(`symlink unavailable: ${error.code}`);
      return;
    }
    const result = runEntrypoint(root, entrypoint);
    assert.notEqual(result.status, 0);
    assert.equal(fs.existsSync(sentinel), false);
    assertTargetPathRedacted(result, externalModule);
    fs.rmSync(root, { recursive: true, force: true });
    fs.rmSync(external, { recursive: true, force: true });
  });

  test(`${entrypoint} rejects an internal policy symlink`, t => {
    const root = makeFixture();
    const policyPath = path.join(root, 'js-runner/pathPolicy.js');
    const target = path.join(root, 'js-runner/pathPolicy.real.js');
    fs.copyFileSync(path.join(projectRoot, 'js-runner/pathPolicy.js'), target);
    fs.rmSync(policyPath);
    try {
      fs.symlinkSync(target, policyPath, 'file');
    } catch (error) {
      fs.rmSync(root, { recursive: true, force: true });
      t.skip(`symlink unavailable: ${error.code}`);
      return;
    }
    const result = runEntrypoint(root, entrypoint);
    assert.notEqual(result.status, 0);
    fs.rmSync(root, { recursive: true, force: true });
  });

  test(`${entrypoint} rejects a directory policy leaf`, () => {
    const root = makeFixture();
    const policyPath = path.join(root, 'js-runner/pathPolicy.js');
    fs.rmSync(policyPath);
    fs.mkdirSync(policyPath);
    const result = runEntrypoint(root, entrypoint);
    assert.notEqual(result.status, 0);
    fs.rmSync(root, { recursive: true, force: true });
  });

  test(`${entrypoint} rejects a symlinked js-runner parent before policy execution`, t => {
    const root = makeFixture();
    const external = fs.mkdtempSync(path.join(os.tmpdir(), 'omni-external-js-runner-'));
    const realRunner = path.join(external, 'js-runner-real');
    fs.renameSync(path.join(root, 'js-runner'), realRunner);
    const sentinel = path.join(external, 'sentinel-created');
    makeSentinelModule(path.join(realRunner, 'pathPolicy.js'), sentinel);
    try {
      fs.symlinkSync(realRunner, path.join(root, 'js-runner'), 'junction');
    } catch (error) {
      fs.rmSync(root, { recursive: true, force: true });
      fs.rmSync(external, { recursive: true, force: true });
      t.skip(`junction unavailable: ${error.code}`);
      return;
    }
    const result = runEntrypoint(root, entrypoint);
    assert.notEqual(result.status, 0);
    assert.equal(fs.existsSync(sentinel), false);
    assertTargetPathRedacted(result, realRunner);
    fs.rmSync(root, { recursive: true, force: true });
    fs.rmSync(external, { recursive: true, force: true });
  });
}

for (const replacement of ['external-symlink', 'internal-symlink', 'directory', 'parent-symlink']) {
  test(`query runner validates fusionBrain before adapter import for ${replacement}`, t => {
    const root = makeFixture();
    const external = fs.mkdtempSync(path.join(os.tmpdir(), 'omni-external-fusion-'));
    const sentinel = path.join(external, 'sentinel-created');
    const externalModule = path.join(external, 'fusionBrain.js');
    makeSentinelModule(externalModule, sentinel);
    const fusionPath = path.join(root, 'core/brain/fusionBrain.js');
    fs.rmSync(fusionPath);
    try {
      if (replacement === 'external-symlink') {
        fs.symlinkSync(externalModule, fusionPath, 'file');
      } else if (replacement === 'internal-symlink') {
        const internal = path.join(root, 'core/brain/fusionBrain.real.js');
        makeSentinelModule(internal, sentinel);
        fs.symlinkSync(internal, fusionPath, 'file');
      } else if (replacement === 'directory') {
        fs.mkdirSync(fusionPath);
        makeSentinelModule(path.join(fusionPath, 'index.js'), sentinel);
      } else {
        const brain = path.join(root, 'core/brain');
        const externalBrain = path.join(external, 'brain');
        fs.renameSync(brain, externalBrain);
        makeSentinelModule(path.join(externalBrain, 'fusionBrain.js'), sentinel);
        fs.symlinkSync(externalBrain, brain, 'junction');
      }
    } catch (error) {
      fs.rmSync(root, { recursive: true, force: true });
      fs.rmSync(external, { recursive: true, force: true });
      t.skip(`link fixture unavailable: ${error.code}`);
      return;
    }
    const result = runEntrypoint(root, 'queryEngineRunner.js');
    assert.equal(result.status, 0, result.stderr);
    const output = JSON.parse(result.stdout);
    assert.match(output.response, /^\[degraded:node_runner\]/);
    assert.equal(fs.existsSync(sentinel), false);
    assertTargetPathRedacted(result, externalModule);
    fs.rmSync(root, { recursive: true, force: true });
    fs.rmSync(external, { recursive: true, force: true });
  });
}
