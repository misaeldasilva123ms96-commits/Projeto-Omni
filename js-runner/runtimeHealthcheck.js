'use strict';

const path = require('path');
const { getAuthoritativeRoot, validateAllowedFile } = require('./pathPolicy');

const workspaceRoot = getAuthoritativeRoot();
const runnerPath = validateAllowedFile('runner');
const adapterPath = validateAllowedFile('adapter_js');
const fusionBrainPath = validateAllowedFile('fusion_brain');
validateAllowedFile('schema');
const rootLabel = path.basename(workspaceRoot).toLowerCase() === 'app' ? 'app' : 'repo';

const payload = {
  status: 'ok',
  runtime_name: process.versions.bun ? 'bun' : 'node',
  runtime_version: process.versions.bun || process.version,
  node_version: process.version,
  cwd: process.cwd() === workspaceRoot ? rootLabel : 'unknown',
  workspace_root: rootLabel,
  runner_exists: Boolean(runnerPath),
  adapter_exists: Boolean(adapterPath),
  fusion_brain_exists: Boolean(fusionBrainPath),
};

process.stdout.write(JSON.stringify(payload));
