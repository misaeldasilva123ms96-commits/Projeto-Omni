'use strict';

const fs = require('fs');
const path = require('path');

const workspaceRoot = process.env.NODE_RUNNER_BASE_DIR
  ? path.resolve(process.env.NODE_RUNNER_BASE_DIR)
  : path.resolve(__dirname, '..');

const payload = {
  status: 'ok',
  node_version: process.version,
  cwd: process.cwd(),
  workspace_root: workspaceRoot,
  runner_exists: fs.existsSync(path.join(workspaceRoot, 'js-runner', 'queryEngineRunner.js')),
  adapter_exists: fs.existsSync(path.join(workspaceRoot, 'src', 'queryEngineRunnerAdapter.js')),
  fusion_brain_exists: fs.existsSync(path.join(workspaceRoot, 'core', 'brain', 'fusionBrain.js')),
};

process.stdout.write(JSON.stringify(payload));
