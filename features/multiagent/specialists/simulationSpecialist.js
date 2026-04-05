function simulatePlan({
  message = '',
  steps = [],
  criticReview = {},
  policySummary = [],
  strategySuggestions = [],
}) {
  const normalized = String(message || '').toLowerCase();
  const mutating = steps.filter(step => step.selected_tool === 'write_file');
  const branchCandidate = steps.filter(step => ['glob_search', 'grep_search', 'read_file'].includes(step.selected_tool)).length >= 2;
  const blockedPolicies = Array.isArray(policySummary)
    ? policySummary.filter(item => item?.policy_decision?.decision === 'stop')
    : [];
  const blockers = [];
  const alternatives = [];
  let recommendedDecision = 'proceed';
  let riskScore = steps.length >= 3 ? 2 : 1;

  if (mutating.length > 0) {
    riskScore += 2;
    blockers.push('write_requires_approval');
    alternatives.push('surface_operator_approval_before_mutation');
    recommendedDecision = 'revise';
  }

  if (blockedPolicies.length > 0) {
    riskScore += 2;
    blockers.push('policy_blocker_detected');
    recommendedDecision = 'stop';
  }

  if (criticReview?.decision === 'revise') {
    riskScore += 1;
    blockers.push('critic_requested_revision');
    recommendedDecision = 'revise';
  }

  if (branchCandidate && normalized.includes('compare')) {
    alternatives.push('explore_safe_read_only_branches');
  }

  if (Array.isArray(strategySuggestions) && strategySuggestions.length > 0) {
    alternatives.push(`strategy_hint:${strategySuggestions[0].strategy_type}`);
  }

  return {
    invoked: riskScore >= 2 || blockers.length > 0 || branchCandidate,
    risk_score: riskScore,
    blockers,
    alternatives,
    branch_candidate: branchCandidate,
    recommended_decision: recommendedDecision,
    summary: blockers.length > 0
      ? `Simulation found blockers: ${blockers.join(', ')}.`
      : branchCandidate
        ? 'Simulation approved bounded read-only branch exploration.'
        : 'Simulation found no blocking issues.',
  };
}

module.exports = {
  simulatePlan,
};
