function reviewDependencyImpact({ repositoryImpactAnalysis, repositoryAnalysis }) {
  const moduleCandidates = Array.isArray(repositoryImpactAnalysis?.module_change_candidates)
    ? repositoryImpactAnalysis.module_change_candidates
    : [];
  const frameworks = Array.isArray(repositoryAnalysis?.repository_map?.frameworks)
    ? repositoryAnalysis.repository_map.frameworks
    : [];
  return {
    invoked: true,
    specialist_id: 'dependency_impact_specialist',
    focus_modules: moduleCandidates.slice(0, 6).map(item => item.path),
    architectural_hotspots: repositoryImpactAnalysis?.impact_map?.hotspot_files || [],
    recommended_scope: moduleCandidates.length >= 5 ? 'milestone-first' : 'targeted-change',
    dependency_notes: frameworks.length > 1
      ? [`Repository spans multiple frameworks: ${frameworks.join(', ')}.`]
      : ['Repository impact is localized enough for bounded engineering work.'],
  };
}

module.exports = {
  reviewDependencyImpact,
};
