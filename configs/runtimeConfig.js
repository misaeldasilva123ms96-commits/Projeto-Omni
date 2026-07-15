function envValue(name, fallback = '') {
  return String(process.env[name] || fallback).trim();
}

function intEnv(name, fallback) {
  const raw = Number.parseInt(envValue(name), 10);
  return Number.isFinite(raw) && raw > 0 ? raw : fallback;
}

function loadRuntimeConfig() {
  return {
    requestedExecutionMode: envValue('OMNI_EXECUTION_MODE', 'auto') || 'auto',
    maxSteps: intEnv('OMNI_MAX_STEPS', 6),
    maxRetries: intEnv('OMNI_MAX_RETRIES', 1),
    stepTimeoutMs: intEnv('OMNI_STEP_TIMEOUT_MS', 30000),
    maxCorrectionDepth: intEnv('OMNI_MAX_CORRECTION_DEPTH', 1),
    maxParallelReadSteps: intEnv('OMNI_MAX_PARALLEL_READ_STEPS', 2),
    staleCheckpointMinutes: intEnv('OMNI_STALE_CHECKPOINT_MINUTES', 120),
    criticEnabled: envValue('OMNI_ENABLE_CRITIC', 'true').toLowerCase() !== 'false',
    criticRiskThreshold: intEnv('OMNI_CRITIC_RISK_THRESHOLD', 2),
    semanticRetrievalMode: envValue('OMNI_SEMANTIC_MODE', 'vector') || 'vector',
    reflectionEnabled: envValue('OMNI_ENABLE_REFLECTION', 'true').toLowerCase() !== 'false',
    reflectionMaxDepth: intEnv('OMNI_MAX_REFLECTION_DEPTH', 1),
    hierarchyThreshold: intEnv('OMNI_HIERARCHY_THRESHOLD', 3),
    negotiationMaxDepth: intEnv('OMNI_NEGOTIATION_MAX_DEPTH', 1),
    supervisionMaxTreeNodes: intEnv('OMNI_SUPERVISION_MAX_TREE_NODES', 24),
    supervisionMaxBranches: intEnv('OMNI_SUPERVISION_MAX_BRANCHES', 2),
    simulationEnabled: envValue('OMNI_ENABLE_SIMULATION', 'true').toLowerCase() !== 'false',
    maxEngineeringIterations: intEnv('OMNI_MAX_ENGINEERING_ITERATIONS', 3),
    maxMilestones: intEnv('OMNI_MAX_MILESTONES', 6),
  };
}

module.exports = {
  loadRuntimeConfig,
};
