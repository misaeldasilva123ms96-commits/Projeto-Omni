const fs = require('fs');
const path = require('path');

const EXECUTION_MODES = Object.freeze({
  NODE_RUST_DIRECT: 'node-rust-direct',
  PYTHON_RUST_PACKAGED: 'python-rust-packaged',
  PYTHON_RUST_CARGO: 'python-rust-cargo',
});

function findCompiledBridge(cwd) {
  const root = cwd || process.cwd();
  const candidates = [
    path.join(root, 'backend', 'rust', 'target', 'x86_64-pc-windows-gnullvm', 'debug', 'executor_bridge.exe'),
    path.join(root, 'backend', 'rust', 'target', 'debug', 'executor_bridge.exe'),
  ];

  return candidates.find(candidate => fs.existsSync(candidate)) || '';
}

function envFlag(name) {
  const value = String(process.env[name] || '').trim().toLowerCase();
  return value === '1' || value === 'true' || value === 'yes';
}

function normalizeRequestedMode(requestedMode) {
  const normalized = String(requestedMode || '').trim().toLowerCase();
  return Object.values(EXECUTION_MODES).includes(normalized) ? normalized : '';
}

function resolveExecutionMode({ cwd, requestedMode = '', allowNodeRustDirect = envFlag('OMINI_ENABLE_NODE_RUST_DIRECT') } = {}) {
  const compiledBridgePath = findCompiledBridge(cwd);
  const normalizedRequestedMode = normalizeRequestedMode(requestedMode || process.env.OMINI_EXECUTION_MODE);

  const packagedMode = compiledBridgePath
    ? {
        mode: EXECUTION_MODES.PYTHON_RUST_PACKAGED,
        owner: 'python',
        bridge_kind: 'packaged-binary',
        compiled_bridge_path: compiledBridgePath,
      }
    : null;

  const cargoMode = {
    mode: EXECUTION_MODES.PYTHON_RUST_CARGO,
    owner: 'python',
    bridge_kind: 'cargo-run',
    compiled_bridge_path: compiledBridgePath,
  };

  const directMode = compiledBridgePath && allowNodeRustDirect
    ? {
        mode: EXECUTION_MODES.NODE_RUST_DIRECT,
        owner: 'node',
        bridge_kind: 'packaged-binary',
        compiled_bridge_path: compiledBridgePath,
      }
    : null;

  const primary = (() => {
    if (normalizedRequestedMode === EXECUTION_MODES.NODE_RUST_DIRECT && directMode) return directMode;
    if (normalizedRequestedMode === EXECUTION_MODES.PYTHON_RUST_PACKAGED && packagedMode) return packagedMode;
    if (normalizedRequestedMode === EXECUTION_MODES.PYTHON_RUST_CARGO) return cargoMode;
    if (directMode) return directMode;
    if (packagedMode) return packagedMode;
    return cargoMode;
  })();

  const fallback = primary.mode === EXECUTION_MODES.PYTHON_RUST_CARGO
    ? null
    : cargoMode;

  return {
    primary,
    fallback,
    requested_mode: normalizedRequestedMode || 'auto',
    node_direct_enabled: Boolean(directMode),
    compiled_bridge_available: Boolean(compiledBridgePath),
  };
}

module.exports = {
  EXECUTION_MODES,
  findCompiledBridge,
  resolveExecutionMode,
};
