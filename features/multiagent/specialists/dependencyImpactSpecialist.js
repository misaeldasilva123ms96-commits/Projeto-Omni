const {
  buildSpecialistFallback,
  logSpecialistFallback,
} = require('./specialistErrorPolicy');

function specialistTimeoutMs() {
  const parsed = Number.parseInt(process.env.SPECIALIST_TIMEOUT_MS || '500', 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 500;
}

function fallbackDependencyImpact(error = null) {
  return buildSpecialistFallback({
    specialistId: 'dependency_impact_specialist',
    extra: {
      focus_modules: [],
      architectural_hotspots: [],
      recommended_scope: 'targeted-change',
      dependency_notes: ['Dependency impact specialist fallback: public-safe degraded result.'],
    },
    err: error,
  });
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
      logSpecialistFallback({ specialistId: 'dependency_impact_specialist' });
      return fallbackDependencyImpact();
    }
    return result;
  } catch (error) {
    logSpecialistFallback({ specialistId: 'dependency_impact_specialist', err: error });
    return fallbackDependencyImpact(error);
  }
}

module.exports = {
  reviewDependencyImpact,
};
