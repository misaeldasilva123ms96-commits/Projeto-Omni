function specialistTimeoutMs() {
  const parsed = Number.parseInt(process.env.SPECIALIST_TIMEOUT_MS || '500', 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 500;
}

function fallbackDependencyImpact(reason) {
  return {
    invoked: true,
    degraded: true,
    specialist_id: 'dependency_impact_specialist',
    focus_modules: [],
    architectural_hotspots: [],
    recommended_scope: 'targeted-change',
    dependency_notes: [`Dependency impact specialist fallback: ${reason}.`],
  };
}

function reviewDependencyImpact({ repositoryImpactAnalysis, repositoryAnalysis } = {}) {
  const startedAt = Date.now();
  try {
    if (process.env.OMINI_FORCE_SPECIALIST_FAILURE === 'dependency_impact_specialist') {
      throw new Error('forced specialist failure');
    }

    const moduleCandidates = Array.isArray(repositoryImpactAnalysis?.module_change_candidates)
      ? repositoryImpactAnalysis.module_change_candidates
      : [];
    const frameworks = Array.isArray(repositoryAnalysis?.repository_map?.frameworks)
      ? repositoryAnalysis.repository_map.frameworks
      : [];
    const result = {
      invoked: true,
      specialist_id: 'dependency_impact_specialist',
      focus_modules: moduleCandidates.slice(0, 6).map(item => item.path),
      architectural_hotspots: repositoryImpactAnalysis?.impact_map?.hotspot_files || [],
      recommended_scope: moduleCandidates.length >= 5 ? 'milestone-first' : 'targeted-change',
      dependency_notes: frameworks.length > 1
        ? [`Repository spans multiple frameworks: ${frameworks.join(', ')}.`]
        : ['Repository impact is localized enough for bounded engineering work.'],
    };

    if (Date.now() - startedAt > specialistTimeoutMs()) {
      console.error('[specialist] dependency_impact_specialist timed out; returning degraded fallback');
      return fallbackDependencyImpact('timeout');
    }
    return result;
  } catch (error) {
    console.error('[specialist] dependency_impact_specialist failed:', error);
    return fallbackDependencyImpact(error instanceof Error ? error.message : 'unknown failure');
  }
}

module.exports = {
  reviewDependencyImpact,
};
