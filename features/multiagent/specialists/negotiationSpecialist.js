function buildNegotiationTurn(agentId, stance, reason, depth = 1) {
  return {
    agent_id: agentId,
    stance,
    reason,
    depth,
  };
}

function negotiatePlan({
  message = '',
  plannerResult = {},
  criticReview = {},
  simulationSummary = {},
  strategySuggestions = [],
  maxDepth = 1,
}) {
  const steps = Array.isArray(plannerResult.steps) ? plannerResult.steps : [];
  const risky = steps.some(step => step.selected_tool === 'write_file');
  const analysis = String(message || '').toLowerCase().includes('analise');
  const turns = [];

  turns.push(buildNegotiationTurn(
    'task_planner',
    'proposal',
    plannerResult.plan_kind === 'hierarchical'
      ? 'Use hierarchical decomposition with bounded execution tree.'
      : 'Use direct bounded execution path.',
  ));
  turns.push(buildNegotiationTurn(
    'researcher_agent',
    'counterproposal',
    analysis
      ? 'Gather read-only evidence first to reduce uncertainty.'
      : 'Keep evidence gathering minimal before acting.',
  ));
  if (strategySuggestions.length > 0) {
    turns.push(buildNegotiationTurn(
      'reviewer_agent',
      'evaluation',
      `Top strategy suggests: ${strategySuggestions[0].lesson || strategySuggestions[0].strategy_type}.`,
    ));
  }
  turns.push(buildNegotiationTurn(
    'critic_agent',
    criticReview?.decision === 'revise' ? 'critic-review' : 'critic-approve',
    criticReview?.decision === 'revise'
      ? `Critic requests revision: ${criticReview.reason_code || 'unknown'}.`
      : 'Critic allows bounded execution.',
  ));
  if (simulationSummary?.invoked) {
    turns.push(buildNegotiationTurn(
      'simulator_agent',
      'simulation-evaluation',
      simulationSummary.summary || 'Simulation completed.',
    ));
  }

  const disagreements = turns.filter(turn => /counterproposal|revise|block/i.test(turn.stance) || /revision|reduce uncertainty/i.test(turn.reason));
  const finalDecision = simulationSummary?.recommended_decision === 'stop'
    ? 'stop'
    : criticReview?.decision === 'revise'
      ? 'revise'
      : risky
        ? 'revise'
        : 'proceed';

  return {
    invoked: true,
    max_depth: maxDepth,
    final_decision: finalDecision,
    disagreement_count: disagreements.length,
    turns,
    summary: disagreements.length > 0
      ? 'Negotiation recorded bounded disagreement before final orchestrator decision.'
      : 'Negotiation converged without material disagreement.',
  };
}

module.exports = {
  negotiatePlan,
};
