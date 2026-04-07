function selectVerificationTargets({ repositoryImpactAnalysis, repositoryAnalysis }) {
  const testCandidates = Array.isArray(repositoryImpactAnalysis?.test_selection_candidates)
    ? repositoryImpactAnalysis.test_selection_candidates
    : [];
  const frameworks = Array.isArray(repositoryAnalysis?.repository_map?.frameworks)
    ? repositoryAnalysis.repository_map.frameworks
    : [];
  const verificationModes = ['targeted-tests'];
  if (frameworks.includes('javascript-testing') || frameworks.includes('react-vite')) {
    verificationModes.push('full-tests');
  }
  verificationModes.push('dependency-health');
  return {
    invoked: true,
    specialist_id: 'test_selection_specialist',
    targeted_tests: testCandidates.map(item => item.path),
    verification_modes: verificationModes,
    rationale: testCandidates.length > 0
      ? 'Selected tests that match likely affected modules.'
      : 'Falling back to broader verification because no direct test match was found.',
  };
}

module.exports = {
  selectVerificationTargets,
};
