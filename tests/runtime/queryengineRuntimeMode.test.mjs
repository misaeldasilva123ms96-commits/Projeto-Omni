import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';
import os from 'node:os';
import { createRequire } from 'node:module';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const runnerModule = await import(pathToFileURL(path.join(projectRoot, 'js-runner', 'queryEngineRunner.js')).href);
const require = createRequire(import.meta.url);
const runtimeModeModule = require(path.join(projectRoot, 'runtime', 'execution', 'runtimeMode.js'));

function makeTempWorkspace() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'omni-runtime-mode-'));
}

function createBridge(workspaceRoot, relativePath) {
  const absolutePath = path.join(workspaceRoot, relativePath);
  fs.mkdirSync(path.dirname(absolutePath), { recursive: true });
  fs.writeFileSync(absolutePath, '#!/bin/sh\nexit 0\n', 'utf8');
  return absolutePath;
}

const bunMetadata = runnerModule.resolveRuntimeMetadata(
  { OMINI_JS_RUNTIME: 'bun', OMINI_JS_RUNTIME_SOURCE: 'bun_detected' },
  { bun: '1.2.0', node: process.versions.node },
);
assert.equal(bunMetadata.runtime_mode, 'bun');
assert.equal(bunMetadata.runtime_reason, 'bun_native');

const nodeFallbackMetadata = runnerModule.resolveRuntimeMetadata(
  { OMINI_JS_RUNTIME: 'node', OMINI_JS_RUNTIME_SOURCE: 'node_fallback' },
  { node: process.versions.node },
);
assert.equal(nodeFallbackMetadata.runtime_mode, 'node');
assert.equal(nodeFallbackMetadata.runtime_reason, 'node_fallback_no_bun');

const apiMissingMetadata = runnerModule.resolveRuntimeMetadata(
  { OMINI_JS_RUNTIME: 'node', OMINI_JS_RUNTIME_SOURCE: 'bun_api_missing' },
  { node: process.versions.node },
);
assert.equal(apiMissingMetadata.runtime_mode, 'node');
assert.equal(apiMissingMetadata.runtime_reason, 'node_fallback_api_missing');

const runtimeErrorMetadata = runnerModule.resolveRuntimeMetadata(
  { OMINI_JS_RUNTIME: 'node', OMINI_JS_RUNTIME_SOURCE: 'bun_error' },
  { node: process.versions.node },
);
assert.equal(runtimeErrorMetadata.runtime_mode, 'node');
assert.equal(runtimeErrorMetadata.runtime_reason, 'node_fallback_error');

const originalEnableNodeRustDirect = process.env.OMINI_ENABLE_NODE_RUST_DIRECT;
try {
  process.env.OMINI_ENABLE_NODE_RUST_DIRECT = 'true';

  const linuxWorkspace = makeTempWorkspace();
  createBridge(linuxWorkspace, 'backend/rust/target/debug/executor_bridge');
  const linuxMode = runtimeModeModule.resolveExecutionMode({ cwd: linuxWorkspace, allowNodeRustDirect: true });
  assert.equal(linuxMode.primary.mode, runtimeModeModule.EXECUTION_MODES.NODE_RUST_DIRECT);
  assert.equal(linuxMode.compiled_bridge_available, true);

  const windowsWorkspace = makeTempWorkspace();
  createBridge(windowsWorkspace, 'backend/rust/target/debug/executor_bridge.exe');
  const windowsMode = runtimeModeModule.resolveExecutionMode({ cwd: windowsWorkspace, allowNodeRustDirect: true });
  assert.equal(windowsMode.primary.mode, runtimeModeModule.EXECUTION_MODES.NODE_RUST_DIRECT);
  assert.equal(windowsMode.compiled_bridge_available, true);

  const fallbackWorkspace = makeTempWorkspace();
  const fallbackMode = runtimeModeModule.resolveExecutionMode({ cwd: fallbackWorkspace, allowNodeRustDirect: true });
  assert.equal(fallbackMode.primary.mode, runtimeModeModule.EXECUTION_MODES.PYTHON_RUST_CARGO);
  assert.equal(fallbackMode.fallback, null);
  assert.equal(fallbackMode.compiled_bridge_available, false);
} finally {
  if (typeof originalEnableNodeRustDirect === 'string') {
    process.env.OMINI_ENABLE_NODE_RUST_DIRECT = originalEnableNodeRustDirect;
  } else {
    delete process.env.OMINI_ENABLE_NODE_RUST_DIRECT;
  }
}

const preservedStructured = runnerModule.sanitizeForUser({
  response: '[execução_python_requerida] plano pronto',
  execution_request: {
    actions: [{ selected_tool: 'read_file', tool_arguments: { path: 'package.json' } }],
  },
  metadata: {
    engine_mode: 'fusion_authority',
    engine_reason: 'adapter_path_selected',
  },
});
assert.equal(typeof preservedStructured.execution_request, 'object');
assert.ok(Array.isArray(preservedStructured.execution_request.actions));
assert.equal(preservedStructured.metadata.engine_mode, 'fusion_authority');

const emptySanitized = runnerModule.sanitizeForUser('');
assert.equal(emptySanitized.error.failure_class, 'NODE_EMPTY_RESPONSE');
assert.equal(typeof emptySanitized.response, 'string');

console.log('queryengine runtime mode tests: ok');
