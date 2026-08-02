'use strict';

const fs = require('fs');
const path = require('path');

function requireValidatedPathPolicy() {
  const samePath = (left, right) => {
    const a = path.resolve(left);
    const b = path.resolve(right);
    return process.platform === 'win32' ? a.toLowerCase() === b.toLowerCase() : a === b;
  };
  const contained = (root, candidate) => {
    const relative = path.relative(root, candidate);
    return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative));
  };
  const assertNoLinks = (candidate) => {
    const absolute = path.resolve(candidate);
    const parsed = path.parse(absolute);
    const parts = absolute.slice(parsed.root.length).split(path.sep).filter(Boolean);
    let current = parsed.root;
    for (const part of parts) {
      current = path.join(current, part);
      const entry = fs.lstatSync(current);
      if (entry.isSymbolicLink()) throw new Error('node_path_policy_bootstrap_failed');
    }
  };

  try {
    const lexicalRoot = path.resolve(__dirname, '..');
    const lexicalPolicy = path.join(lexicalRoot, 'js-runner', 'pathPolicy.js');
    assertNoLinks(lexicalRoot);
    assertNoLinks(lexicalPolicy);
    const canonicalRoot = fs.realpathSync(lexicalRoot);
    const canonicalPolicy = fs.realpathSync(lexicalPolicy);
    const policyInfo = fs.lstatSync(lexicalPolicy);
    if (
      !policyInfo.isFile()
      || !samePath(lexicalRoot, canonicalRoot)
      || !samePath(lexicalPolicy, canonicalPolicy)
      || !contained(canonicalRoot, canonicalPolicy)
    ) {
      throw new Error('node_path_policy_bootstrap_failed');
    }
    for (const key of ['BASE_DIR', 'NODE_RUNNER_BASE_DIR']) {
      const configured = String(process.env[key] || '').trim();
      if (!configured) continue;
      const lexicalConfigured = path.resolve(configured);
      assertNoLinks(lexicalConfigured);
      const canonicalConfigured = fs.realpathSync(lexicalConfigured);
      if (!samePath(lexicalConfigured, canonicalConfigured) || !samePath(canonicalConfigured, canonicalRoot)) {
        throw new Error('node_path_policy_bootstrap_failed');
      }
    }
    if (require.main === module && process.argv[1]) {
      const lexicalEntrypoint = path.resolve(process.argv[1]);
      assertNoLinks(lexicalEntrypoint);
      if (!samePath(lexicalEntrypoint, __filename) || !samePath(fs.realpathSync(lexicalEntrypoint), __filename)) {
        throw new Error('node_path_policy_bootstrap_failed');
      }
    }
    return require(lexicalPolicy);
  } catch {
    const error = new Error('node_path_policy_bootstrap_failed');
    error.stack = `${error.name}: ${error.message}`;
    throw error;
  }
}

let validatedPathPolicy;
try {
  validatedPathPolicy = requireValidatedPathPolicy();
} catch {
  process.stderr.write('node_path_policy_bootstrap_failed\n');
  process.exit(1);
}

const { getAuthoritativeRoot, validateAllowedFile } = validatedPathPolicy;

validateAllowedFile('path_policy');

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
