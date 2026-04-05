function reviewEngineeringPlan({ repositoryAnalysis = {}, plannerResult = {}, message = '' }) {
  const files = Array.isArray(repositoryAnalysis.file_index) ? repositoryAnalysis.file_index : [];
  const steps = Array.isArray(plannerResult.steps) ? plannerResult.steps : [];
  const riskyWrite = steps.some(step => ['filesystem_write', 'write_file', 'git_commit', 'package_manager'].includes(step.selected_tool));
  const review = {
    invoked: true,
    risk_level: riskyWrite ? 'medium' : 'low',
    repository_size: files.length,
    recommended_scope: riskyWrite ? 'bounded_patch' : 'read_only_or_test_first',
    warnings: [],
    improvements: [],
  };

  if (files.length > 1200) {
    review.risk_level = 'high';
    review.warnings.push('repository_large');
    review.improvements.push('narrow file targeting before mutation');
  }
  if (/dependency|upgrade|atualize dependencia|atualizar dependencia/i.test(message)) {
    review.warnings.push('dependency_change_requires_review');
    review.improvements.push('inspect lockfiles and run focused verification');
  }
  if (riskyWrite) {
    review.improvements.push('run tests before accepting patch');
  }
  return review;
}

module.exports = {
  reviewEngineeringPlan,
};
