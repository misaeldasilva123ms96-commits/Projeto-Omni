import assert from 'node:assert/strict';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const projectRoot = process.cwd();
const launcherModule = await import(pathToFileURL(path.join(projectRoot, 'scripts', 'js-runtime-launcher.mjs')).href);

const defaultSelected = launcherModule.detectJsRuntime({
  BUN_BIN: process.execPath,
  NODE_BIN: process.execPath,
});
assert.equal(defaultSelected.runtimeName, 'node');
assert.equal(defaultSelected.source, 'node_default');
assert.equal(defaultSelected.fallbackUsed, false);

const explicitNodeSelected = launcherModule.detectJsRuntime({
  OMNI_JS_RUNTIME_BIN: process.execPath,
  NODE_BIN: process.execPath,
});
assert.equal(explicitNodeSelected.runtimeName, 'node');
assert.equal(explicitNodeSelected.source, 'explicit_env');

const obsoleteOnlySelected = launcherModule.detectJsRuntime({
  OMINI_JS_RUNTIME_BIN: 'bun',
  NODE_BIN: process.execPath,
});
assert.equal(obsoleteOnlySelected.runtimeName, 'node');
assert.equal(obsoleteOnlySelected.source, 'node_default');

const explicitBunSelected = launcherModule.detectJsRuntime({
  OMNI_JS_RUNTIME_BIN: 'bun',
  NODE_BIN: process.execPath,
});
assert.equal(explicitBunSelected.runtimeName, 'bun');
assert.match(explicitBunSelected.source, /^explicit_env/);
assert.equal(explicitBunSelected.fallbackUsed, false);

const explicitMissingBun = launcherModule.runWithSelectedRuntime(
  ['js-runner/healthcheck.js'],
  {
    OMNI_JS_RUNTIME_BIN: 'definitely-missing-bun',
    PATH: process.env.PATH,
  },
);
assert.equal(explicitMissingBun, 1);

console.log('js runtime launcher tests: ok');
