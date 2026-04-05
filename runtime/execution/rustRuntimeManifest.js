const path = require('path');
const { resolveExecutionMode } = require('./runtimeMode');

function buildRustRuntimeManifest(cwd) {
  const root = cwd || process.cwd();
  const runtimeMode = resolveExecutionMode({ cwd: root });
  return {
    authority: 'rust-execution-engine',
    source_repo: 'claw-code-main.zip',
    execution_mode: runtimeMode.primary.mode,
    fallback_mode: runtimeMode.fallback?.mode || null,
    compiled_bridge_available: runtimeMode.compiled_bridge_available,
    upstream_paths: {
      conversation_runtime: path.resolve(root, 'vendor', 'claw-runtime-upstream', 'conversation.rs'),
      permission_policy: path.resolve(root, 'vendor', 'claw-runtime-upstream', 'permissions.rs'),
      session_model: path.resolve(root, 'vendor', 'claw-runtime-upstream', 'session.rs'),
      usage_tracker: path.resolve(root, 'vendor', 'claw-runtime-upstream', 'usage.rs'),
    },
    responsibilities: [
      'tool execution loop',
      'permission enforcement',
      'usage tracking',
      'session compaction',
      'auditable tool execution',
    ],
  };
}

module.exports = {
  buildRustRuntimeManifest,
};
