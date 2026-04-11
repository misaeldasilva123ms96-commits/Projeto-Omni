import assert from 'node:assert/strict';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const projectRoot = process.cwd();
const launcherModule = await import(pathToFileURL(path.join(projectRoot, 'scripts', 'js-runtime-launcher.mjs')).href);

const bunSelected = launcherModule.detectJsRuntime({
  BUN_BIN: process.execPath,
  NODE_BIN: 'definitely-missing-node',
});
assert.equal(bunSelected.runtimeName, 'bun');

const nodeSelected = launcherModule.detectJsRuntime({
  BUN_BIN: 'definitely-missing-bun',
  NODE_BIN: process.execPath,
});
assert.equal(nodeSelected.runtimeName, 'node');
assert.equal(nodeSelected.fallbackUsed, true);

console.log('js runtime launcher tests: ok');
