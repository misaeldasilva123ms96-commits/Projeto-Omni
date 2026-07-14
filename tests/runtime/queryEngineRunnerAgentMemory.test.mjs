import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { isAgentMemoryEnabled, loadAgentMemoryContext } = require('../../js-runner/queryEngineRunner.js');

const ENV_KEYS = [
  'NODE_RUNNER_BASE_DIR',
  'OMNI_PUBLIC_DEMO_MODE',
  'OMINI_PUBLIC_DEMO_MODE',
  'OMNI_ENABLE_AGENT_MEMORY',
];

function withEnv(updates, fn) {
  const saved = new Map(ENV_KEYS.map(key => [key, process.env[key]]));
  for (const key of ENV_KEYS) {
    delete process.env[key];
  }
  for (const [key, value] of Object.entries(updates)) {
    process.env[key] = value;
  }
  try {
    fn();
  } finally {
    for (const key of ENV_KEYS) {
      const value = saved.get(key);
      if (value === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = value;
      }
    }
  }
}

function withMemoryWorkspace(fn) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'omni-agent-memory-'));
  const memoryDir = path.join(root, '.claude', 'agent-memory', 'safe-notes');
  fs.mkdirSync(memoryDir, { recursive: true });
  fs.writeFileSync(path.join(memoryDir, 'MEMORY.MD'), 'safe local context only\n', 'utf8');
  try {
    fn(root);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

withMemoryWorkspace(root => {
  withEnv({
    NODE_RUNNER_BASE_DIR: root,
    OMNI_PUBLIC_DEMO_MODE: 'true',
    OMNI_ENABLE_AGENT_MEMORY: 'true',
  }, () => {
    assert.equal(isAgentMemoryEnabled(), false);
    assert.equal(loadAgentMemoryContext(), '');
  });
});

withMemoryWorkspace(root => {
  withEnv({
    NODE_RUNNER_BASE_DIR: root,
  }, () => {
    assert.equal(isAgentMemoryEnabled(), false);
    assert.equal(loadAgentMemoryContext(), '');
  });
});

withMemoryWorkspace(root => {
  withEnv({
    NODE_RUNNER_BASE_DIR: root,
    OMNI_ENABLE_AGENT_MEMORY: 'true',
  }, () => {
    assert.equal(isAgentMemoryEnabled(), true);
    assert.match(loadAgentMemoryContext(), /safe local context only/);
  });
});

console.log('queryEngineRunner agent memory hardening: ok');
