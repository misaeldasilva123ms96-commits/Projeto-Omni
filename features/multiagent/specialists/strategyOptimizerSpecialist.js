function optimizeStrategySelection({ message = '', rankedStrategies = [], plannerResult = {} }) {
  const top = Array.isArray(rankedStrategies) ? rankedStrategies[0] : null;
  const text = String(message || '').toLowerCase();
  const stepBiases = [];
  let preferredPlanMode = plannerResult.plan_kind || 'linear';

  if (top) {
    if (String(top.strategy_type || '').includes('branch')) {
      preferredPlanMode = 'tree';
      stepBiases.push('prefer_branch_analysis');
    }
    if (String(top.lesson || '').toLowerCase().includes('read-only')) {
      stepBiases.push('prefer_read_only_first');
    }
  }

  if (text.includes('compare') || text.includes('comparar')) {
    preferredPlanMode = 'tree';
    stepBiases.push('prefer_comparative_execution');
  }

  return {
    invoked: true,
    preferred_plan_mode: preferredPlanMode,
    step_biases: stepBiases,
    selected_strategy: top || null,
    summary: top
      ? `Strategy optimizer selected ${top.strategy_type}.`
      : 'Strategy optimizer found no ranked strategy and kept the baseline plan.',
  };
}

module.exports = {
  optimizeStrategySelection,
};
