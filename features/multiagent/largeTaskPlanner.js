function buildMilestone(id, title, description, stepIds, extra = {}) {
  return {
    milestone_id: id,
    title,
    description,
    state: 'pending',
    step_ids: Array.isArray(stepIds) ? stepIds : [],
    blockers: [],
    progress: 0,
    ...extra,
  };
}

function buildLargeTaskPlan({ sessionId, message, repositoryAnalysis, repositoryImpactAnalysis, verificationPlan }) {
  const moduleCandidates = Array.isArray(repositoryImpactAnalysis?.module_change_candidates)
    ? repositoryImpactAnalysis.module_change_candidates
    : [];
  const topModules = moduleCandidates.slice(0, 5).map(item => item.path);
  const verificationModes = Array.isArray(verificationPlan?.verification_modes)
    ? verificationPlan.verification_modes
    : [];
  const milestones = [
    buildMilestone(
      `milestone:${sessionId}:analysis`,
      'Analyze repository entry points',
      'Inspect structure, dependency files, and likely module boundaries before changing code.',
      [`${sessionId}:step:repo-tree`, `${sessionId}:step:repo-deps`, `${sessionId}:step:repo-impact`],
      { epic_id: `epic:${sessionId}:analysis`, category: 'analysis', affected_files: topModules },
    ),
    buildMilestone(
      `milestone:${sessionId}:implementation`,
      'Prepare multi-module implementation plan',
      'Identify module candidates, patch-set boundaries, and patch safety before mutation.',
      [`${sessionId}:step:code-search`, `${sessionId}:step:patch-plan`],
      { epic_id: `epic:${sessionId}:implementation`, category: 'implementation', affected_files: topModules },
    ),
    buildMilestone(
      `milestone:${sessionId}:verification`,
      'Verify targeted and integration behavior',
      'Run targeted verification, broader test coverage, and integration review before merge-ready output.',
      [`${sessionId}:step:verification`, `${sessionId}:step:pr-summary`],
      { epic_id: `epic:${sessionId}:verification`, category: 'verification', verification_modes: verificationModes },
    ),
  ];

  return {
    version: 1,
    mode: 'large-project-engineering',
    root_goal_id: 'goal:large-engineering',
    milestone_tree: {
      root_milestone_id: milestones[0].milestone_id,
      milestones,
    },
    epics: [
      { epic_id: `epic:${sessionId}:analysis`, title: 'Repository understanding', milestone_ids: [milestones[0].milestone_id] },
      { epic_id: `epic:${sessionId}:implementation`, title: 'Patch-set planning', milestone_ids: [milestones[1].milestone_id] },
      { epic_id: `epic:${sessionId}:verification`, title: 'Verification and merge readiness', milestone_ids: [milestones[2].milestone_id] },
    ],
    module_candidates: topModules,
    integration_risk_summary: repositoryImpactAnalysis?.integration_risk_summary || {},
    checkpointable: true,
    requested_change: String(message || ''),
    generated_at: new Date().toISOString(),
    repository_root: repositoryAnalysis?.root || '.',
  };
}

module.exports = {
  buildLargeTaskPlan,
};
