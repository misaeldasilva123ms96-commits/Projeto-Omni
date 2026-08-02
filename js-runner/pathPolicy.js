'use strict';

const fs = require('fs');
const path = require('path');

const SECURITY_FILES = Object.freeze({
  runner: 'js-runner/queryEngineRunner.js',
  schema: 'contract/runner-schema.v1.json',
  adapter_js: 'src/queryEngineRunnerAdapter.js',
  adapter_mjs: 'src/queryEngineRunnerAdapter.mjs',
  fusion_brain: 'core/brain/fusionBrain.js',
  runtime_healthcheck: 'js-runner/runtimeHealthcheck.js',
  dist_query_engine: 'dist/QueryEngine.js',
  build_query_engine: 'build/QueryEngine.js',
  src_query_engine_js: 'src/QueryEngine.js',
  runtime_query_engine_js: 'runtime/node/QueryEngine.js',
  src_query_engine_ts: 'src/QueryEngine.ts',
  runtime_query_engine_ts: 'runtime/node/QueryEngine.ts',
});

const MEMORY_ROOTS = Object.freeze([
  '.claude/agent-memory',
  '.claude/agent-memory-local',
]);

class NodePathPolicyError extends Error {
  constructor(code) {
    super(code);
    this.name = 'NodePathPolicyError';
    this.code = code;
  }
}

function samePath(left, right) {
  const a = path.resolve(left);
  const b = path.resolve(right);
  return process.platform === 'win32' ? a.toLowerCase() === b.toLowerCase() : a === b;
}

function isContained(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative));
}

function assertNoLinkComponents(candidate, includeLeaf = true) {
  const absolute = path.resolve(candidate);
  const parsed = path.parse(absolute);
  const parts = absolute.slice(parsed.root.length).split(path.sep).filter(Boolean);
  let current = parsed.root;
  const end = includeLeaf ? parts.length : Math.max(0, parts.length - 1);
  for (let index = 0; index < end; index += 1) {
    current = path.join(current, parts[index]);
    let entry;
    try {
      entry = fs.lstatSync(current);
    } catch (error) {
      if (error && error.code === 'ENOENT') return false;
      throw new NodePathPolicyError('node_path_policy_violation');
    }
    if (entry.isSymbolicLink()) {
      throw new NodePathPolicyError('node_path_policy_violation');
    }
  }
  return true;
}

function canonicalCodeRoot() {
  const lexicalRoot = path.resolve(__dirname, '..');
  if (!assertNoLinkComponents(lexicalRoot)) {
    throw new NodePathPolicyError('node_project_root_invalid');
  }
  const root = fs.realpathSync(lexicalRoot);
  const markers = ['package.json', 'backend/python', 'backend/rust', SECURITY_FILES.runner, SECURITY_FILES.schema];
  for (const relative of markers) {
    const candidate = path.join(root, relative);
    if (!assertNoLinkComponents(candidate)) {
      throw new NodePathPolicyError('node_project_root_invalid');
    }
    const info = fs.statSync(candidate);
    const expectedDirectory = relative === 'backend/python' || relative === 'backend/rust';
    if (expectedDirectory ? !info.isDirectory() : !info.isFile()) {
      throw new NodePathPolicyError('node_project_root_invalid');
    }
  }
  return root;
}

function requireMatchingEnvironmentRoot(root, env = process.env) {
  for (const key of ['BASE_DIR', 'NODE_RUNNER_BASE_DIR']) {
    const configured = String(env[key] || '').trim();
    if (!configured) continue;
    let canonical;
    try {
      canonical = fs.realpathSync(path.resolve(configured));
    } catch {
      throw new NodePathPolicyError('node_project_root_invalid');
    }
    if (!samePath(canonical, root)) {
      throw new NodePathPolicyError('node_project_root_invalid');
    }
  }
  return root;
}

function getAuthoritativeRoot(env = process.env) {
  return requireMatchingEnvironmentRoot(canonicalCodeRoot(), env);
}

function labelForPath(candidate) {
  const root = canonicalCodeRoot();
  const normalized = path.relative(root, path.resolve(candidate)).split(path.sep).join('/');
  return Object.entries(SECURITY_FILES).find(([, relative]) => relative === normalized)?.[0] || 'unauthorized_candidate';
}

function validateAllowedFile(label, { required = true, env = process.env } = {}) {
  const relative = SECURITY_FILES[label];
  if (!relative) throw new NodePathPolicyError('node_path_policy_violation');
  const root = getAuthoritativeRoot(env);
  const candidate = path.join(root, relative);
  if (!isContained(root, candidate)) throw new NodePathPolicyError('node_path_policy_violation');
  const present = assertNoLinkComponents(candidate);
  if (!present) {
    if (required) throw new NodePathPolicyError(`node_${label}_missing`);
    return null;
  }
  let canonical;
  let info;
  try {
    canonical = fs.realpathSync(candidate);
    info = fs.statSync(candidate);
  } catch {
    throw new NodePathPolicyError(`node_${label}_unsafe`);
  }
  if (!isContained(root, canonical) || !samePath(canonical, candidate) || !info.isFile()) {
    throw new NodePathPolicyError(`node_${label}_unsafe`);
  }
  return candidate;
}

function validateConfiguredArtifact(key, allowedLabels, env = process.env) {
  const configured = String(env[key] || '').trim();
  if (!configured) return null;
  const configuredPath = path.resolve(configured);
  let canonical;
  try {
    if (!assertNoLinkComponents(configuredPath)) throw new NodePathPolicyError('node_path_policy_violation');
    canonical = fs.realpathSync(configuredPath);
  } catch {
    throw new NodePathPolicyError('node_path_policy_violation');
  }
  for (const label of allowedLabels) {
    const allowed = validateAllowedFile(label, { required: true, env });
    if (samePath(configuredPath, allowed) && samePath(canonical, allowed)) return allowed;
  }
  throw new NodePathPolicyError('node_path_policy_violation');
}

function validateMemoryRoot(relative, env = process.env) {
  if (!MEMORY_ROOTS.includes(relative)) throw new NodePathPolicyError('node_memory_root_invalid');
  const root = getAuthoritativeRoot(env);
  const candidate = path.join(root, relative);
  if (!isContained(root, candidate)) throw new NodePathPolicyError('node_memory_root_invalid');
  const present = assertNoLinkComponents(candidate);
  if (!present) return null;
  const canonical = fs.realpathSync(candidate);
  const info = fs.statSync(candidate);
  if (!samePath(canonical, candidate) || !isContained(root, canonical) || !info.isDirectory()) {
    throw new NodePathPolicyError('node_memory_root_invalid');
  }
  return candidate;
}

module.exports = {
  MEMORY_ROOTS,
  NodePathPolicyError,
  SECURITY_FILES,
  assertNoLinkComponents,
  getAuthoritativeRoot,
  isContained,
  labelForPath,
  validateAllowedFile,
  validateConfiguredArtifact,
  validateMemoryRoot,
};
