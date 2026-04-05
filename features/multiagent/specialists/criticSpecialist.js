function estimatePlanRisk({ steps = [], complexity = 'simple', intent = '' }) {
  let risk = complexity === 'complex' ? 2 : 1;
  if (steps.some(step => step.selected_tool === 'write_file')) risk += 2;
  if (steps.length >= 3) risk += 1;
  if (intent === 'analysis') risk += 1;
  return risk;
}

function reviewPlan({ steps = [], planGraph = null, complexity = 'simple', intent = '', runtimeConfig = {} }) {
  const risk = estimatePlanRisk({ steps, complexity, intent });
  const criticEnabled = runtimeConfig.criticEnabled !== false;
  if (!criticEnabled || risk < Number(runtimeConfig.criticRiskThreshold || 2)) {
    return {
      invoked: false,
      decision: 'approve',
      reason_code: 'critic_not_required',
      risk_score: risk,
    };
  }

  if (!steps.length) {
    return {
      invoked: true,
      decision: 'revise',
      reason_code: 'empty_plan',
      risk_score: risk,
    };
  }

  if (planGraph && Array.isArray(planGraph.nodes) && planGraph.nodes.some(node => node.selected_tool === 'write_file' && node.parallel_safe)) {
    return {
      invoked: true,
      decision: 'revise',
      reason_code: 'unsafe_parallel_write',
      risk_score: risk,
    };
  }

  return {
    invoked: true,
    decision: 'approve',
    reason_code: 'plan_within_bounds',
    risk_score: risk,
  };
}

function reviewOutcome({ action, result, evaluation, attemptIndex = 1, maxAttempts = 1 }) {
  const weakSuccess = Boolean(result?.ok) && !String(result?.summary || '').trim();
  if (weakSuccess) {
    return {
      invoked: true,
      decision: 'revise',
      reason_code: 'weak_success_payload',
      attempt_index: attemptIndex,
      max_attempts: maxAttempts,
    };
  }

  if (!result?.ok && evaluation?.decision === 'stop_failed' && attemptIndex < maxAttempts) {
    return {
      invoked: true,
      decision: 'retry',
      reason_code: 'critic_retry_window',
      attempt_index: attemptIndex,
      max_attempts: maxAttempts,
    };
  }

  if (!result?.ok && action?.selected_tool === 'write_file') {
    return {
      invoked: true,
      decision: 'stop',
      reason_code: 'write_failure_needs_operator',
      attempt_index: attemptIndex,
      max_attempts: maxAttempts,
    };
  }

  return {
    invoked: true,
    decision: 'approve',
    reason_code: result?.ok ? 'outcome_grounded' : 'failure_already_classified',
    attempt_index: attemptIndex,
    max_attempts: maxAttempts,
  };
}

module.exports = {
  reviewOutcome,
  reviewPlan,
};
