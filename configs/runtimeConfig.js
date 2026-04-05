function intEnv(name, fallback) {
  const raw = Number.parseInt(String(process.env[name] || ''), 10);
  return Number.isFinite(raw) && raw > 0 ? raw : fallback;
}

function loadRuntimeConfig() {
  return {
    requestedExecutionMode: String(process.env.OMINI_EXECUTION_MODE || 'auto').trim() || 'auto',
    maxSteps: intEnv('OMINI_MAX_STEPS', 6),
    maxRetries: intEnv('OMINI_MAX_RETRIES', 1),
    stepTimeoutMs: intEnv('OMINI_STEP_TIMEOUT_MS', 30000),
    maxCorrectionDepth: intEnv('OMINI_MAX_CORRECTION_DEPTH', 1),
  };
}

module.exports = {
  loadRuntimeConfig,
};
