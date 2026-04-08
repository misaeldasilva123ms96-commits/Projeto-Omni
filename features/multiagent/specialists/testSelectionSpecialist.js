function specialistTimeoutMs() {
  const parsed = Number.parseInt(process.env.SPECIALIST_TIMEOUT_MS || '500', 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 500;
}

function fallbackVerificationSelection(reason) {
  return {
    invoked: true,
    degraded: true,
    specialist_id: 'test_selection_specialist',
    targeted_tests: [],
    verification_modes: ['targeted-tests', 'dependency-health'],
    rationale: `Verification specialist fallback: ${reason}.`,
  };
}

function selectVerificationTargets({ repositoryImpactAnalysis, repositoryAnalysis } = {}) {
  const startedAt = Date.now();
  try {
    if (process.env.OMINI_FORCE_SPECIALIST_FAILURE === 'test_selection_specialist') {
      throw new Error('forced specialist failure');
    }

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
    const result = {
      invoked: true,
      specialist_id: 'test_selection_specialist',
      targeted_tests: testCandidates.map(item => item.path),
      verification_modes: verificationModes,
      rationale: testCandidates.length > 0
        ? 'Selected tests that match likely affected modules.'
        : 'Falling back to broader verification because no direct test match was found.',
    };

    if (Date.now() - startedAt > specialistTimeoutMs()) {
      console.error('[specialist] test_selection_specialist timed out; returning degraded fallback');
      return fallbackVerificationSelection('timeout');
    }
    return result;
  } catch (error) {
    console.error('[specialist] test_selection_specialist failed:', error);
    return fallbackVerificationSelection(error instanceof Error ? error.message : 'unknown failure');
  }
}

module.exports = {
  selectVerificationTargets,
};
