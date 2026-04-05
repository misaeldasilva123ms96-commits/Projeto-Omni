function simulatePlan({
  message = '',
  steps = [],
  criticReview = {},
  policySummary = [],
  strategySuggestions = [],
  runtimeConfig = {},
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
  let confidenceEstimate = 0.72;
  let estimatedCost = steps.length * 1.1;
  const policyFlags = blockedPolicies.map(item => item?.policy_decision?.reason_code).filter(Boolean);

  if (mutating.length > 0) {
    riskScore += 2;
    confidenceEstimate -= 0.12;
    estimatedCost += 1.5;
    blockers.push('write_requires_approval');
    alternatives.push('surface_operator_approval_before_mutation');
    recommendedDecision = 'revise';
  }

  if (blockedPolicies.length > 0) {
    riskScore += 2;
    confidenceEstimate -= 0.18;
    blockers.push('policy_blocker_detected');
    recommendedDecision = 'stop';
  }

  if (criticReview?.decision === 'revise') {
    riskScore += 1;
    confidenceEstimate -= 0.08;
    blockers.push('critic_requested_revision');
    recommendedDecision = 'revise';
  }

  if (branchCandidate && normalized.includes('compare')) {
    alternatives.push('explore_safe_read_only_branches');
    estimatedCost += 0.8;
  }

  if (Array.isArray(strategySuggestions) && strategySuggestions.length > 0) {
    alternatives.push(`strategy_hint:${strategySuggestions[0].strategy_type}`);
    confidenceEstimate += 0.05;
  }

  return {
    invoked: runtimeConfig.simulationEnabled !== false && (riskScore >= 2 || blockers.length > 0 || branchCandidate),
    risk_score: riskScore,
    confidence_estimate: Math.max(0.05, Math.min(0.99, confidenceEstimate)),
    estimated_cost: Number(estimatedCost.toFixed(2)),
    policy_flags: policyFlags,
    blockers,
    alternatives,
    branch_candidate: branchCandidate,
    recommended_decision: recommendedDecision,
    recommended_path: branchCandidate ? 'tree-branch-analysis' : recommendedDecision === 'revise' ? 'revised-safe-path' : 'default-path',
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
