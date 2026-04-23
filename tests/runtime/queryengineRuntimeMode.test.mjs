import assert from 'node:assert/strict';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const runnerModule = await import(pathToFileURL(path.join(projectRoot, 'js-runner', 'queryEngineRunner.js')).href);

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

console.log('queryengine runtime mode tests: ok');
