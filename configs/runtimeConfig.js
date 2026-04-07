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
    maxParallelReadSteps: intEnv('OMINI_MAX_PARALLEL_READ_STEPS', 2),
    staleCheckpointMinutes: intEnv('OMINI_STALE_CHECKPOINT_MINUTES', 120),
    criticEnabled: String(process.env.OMINI_ENABLE_CRITIC || 'true').trim().toLowerCase() !== 'false',
    criticRiskThreshold: intEnv('OMINI_CRITIC_RISK_THRESHOLD', 2),
    semanticRetrievalMode: String(process.env.OMINI_SEMANTIC_MODE || 'vector').trim() || 'vector',
    reflectionEnabled: String(process.env.OMINI_ENABLE_REFLECTION || 'true').trim().toLowerCase() !== 'false',
    reflectionMaxDepth: intEnv('OMINI_MAX_REFLECTION_DEPTH', 1),
    hierarchyThreshold: intEnv('OMINI_HIERARCHY_THRESHOLD', 3),
    negotiationMaxDepth: intEnv('OMINI_NEGOTIATION_MAX_DEPTH', 1),
    supervisionMaxTreeNodes: intEnv('OMINI_SUPERVISION_MAX_TREE_NODES', 24),
    supervisionMaxBranches: intEnv('OMINI_SUPERVISION_MAX_BRANCHES', 2),
    simulationEnabled: String(process.env.OMINI_ENABLE_SIMULATION || 'true').trim().toLowerCase() !== 'false',
    maxEngineeringIterations: intEnv('OMINI_MAX_ENGINEERING_ITERATIONS', 3),
    maxMilestones: intEnv('OMINI_MAX_MILESTONES', 6),
  };
}

module.exports = {
  loadRuntimeConfig,
};
