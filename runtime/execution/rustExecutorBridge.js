const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { EXECUTION_MODES, findCompiledBridge, resolveExecutionMode } = require('./runtimeMode');

function ensureTmpDir(cwd) {
  const tmpDir = path.join(cwd, '.logs', 'fusion-runtime', 'tmp');
  fs.mkdirSync(tmpDir, { recursive: true });
  return tmpDir;
}

function buildPayloadFile(cwd, action) {
  const tmpDir = ensureTmpDir(cwd);
  const filePath = path.join(
    tmpDir,
    `executor-action-${Date.now()}-${Math.random().toString(16).slice(2)}.json`,
  );
  fs.writeFileSync(filePath, JSON.stringify(action, null, 2), 'utf8');
  return filePath;
}

function runRustExecutor({ cwd, action, requestedMode = '' }) {
  const payloadFile = buildPayloadFile(cwd, action);
  const runtimeMode = resolveExecutionMode({
    cwd,
    requestedMode,
    allowNodeRustDirect: true,
  });
  const primary = runtimeMode.primary.mode === EXECUTION_MODES.NODE_RUST_DIRECT
    ? runtimeMode.primary
    : {
        mode: EXECUTION_MODES.PYTHON_RUST_CARGO,
        bridge_kind: 'cargo-run',
        compiled_bridge_path: findCompiledBridge(cwd),
      };

  const compiledBridge = primary.compiled_bridge_path || '';
  const command = primary.mode === EXECUTION_MODES.NODE_RUST_DIRECT && compiledBridge
    ? compiledBridge
    : 'cargo';
  const commandArgs = primary.mode === EXECUTION_MODES.NODE_RUST_DIRECT && compiledBridge
    ? [payloadFile]
    : ['run', '--quiet', '--bin', 'executor_bridge', '--', payloadFile];

  const result = spawnSync(command, commandArgs, {
    cwd: primary.mode === EXECUTION_MODES.NODE_RUST_DIRECT && compiledBridge ? cwd : path.join(cwd, 'backend', 'rust'),
    encoding: 'utf8',
    timeout: action.timeout_ms || 30000,
    env: {
      ...process.env,
      CARGO_TERM_COLOR: 'never',
      RUST_BACKTRACE: '0',
    },
  });

  try {
    fs.unlinkSync(payloadFile);
  } catch {}

  if (result.error) {
    return {
      ok: false,
      error: {
        kind: 'spawn_error',
        message: result.error.message,
      },
    };
  }

  if (result.status !== 0) {
    return {
      ok: false,
      error: {
        kind: 'runtime_error',
        message: (result.stderr || result.stdout || 'Rust executor bridge failed').trim(),
        code: result.status,
      },
    };
  }

  try {
    const parsed = JSON.parse(result.stdout || '{}');
    parsed.runtime_mode = primary.mode;
    return parsed;
  } catch (error) {
    return {
      ok: false,
      error: {
        kind: 'parse_error',
        message: `Failed to parse Rust bridge output: ${error.message}`,
        raw: result.stdout,
      },
    };
  }
}

module.exports = {
  runRustExecutor,
};
