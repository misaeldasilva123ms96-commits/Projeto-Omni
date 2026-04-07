function buildVerificationPlan({ repositoryImpactAnalysis, runtimeConfig }) {
  const targetedTests = Array.isArray(repositoryImpactAnalysis?.test_selection_candidates)
    ? repositoryImpactAnalysis.test_selection_candidates.map(item => item.path)
    : [];
  const verificationModes = targetedTests.length > 0
    ? ['targeted-tests', 'full-tests', 'dependency-health']
    : ['full-tests', 'dependency-health'];
  return {
    version: 1,
    verification_modes: verificationModes,
    targeted_tests: targetedTests,
    max_verification_steps: Math.min(4, Math.max(2, runtimeConfig.maxEngineeringIterations || 3)),
    requires_full_regression: verificationModes.includes('full-tests'),
    summary: targetedTests.length > 0
      ? 'Targeted verification will run before broader regression checks.'
      : 'No direct test match found; falling back to broader verification.',
  };
}

module.exports = {
  buildVerificationPlan,
};
