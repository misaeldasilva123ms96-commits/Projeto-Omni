const { getSpecialistAgent, listSpecialistAgents, resolveSpecialistsForIntent } = require('../../core/agents/specialistRegistry');

function buildDelegationPlan({ intent, complexity }) {
  const delegates = resolveSpecialistsForIntent(intent);
  const catalog = listSpecialistAgents();

  return {
    master: 'master_orchestrator',
    delegates,
    complexity,
    specialists: delegates.map(id => catalog.find(agent => agent.id === id)).filter(Boolean),
    delegation_contract: delegates.map(id => {
      const agent = getSpecialistAgent(id);
      return agent
        ? {
            specialist_id: agent.id,
            role: agent.role,
            allowed_tools: agent.allowedTools,
            capabilities: agent.capabilities,
            failure_policy: agent.failurePolicy,
            status: id === 'master_orchestrator' ? 'active' : 'delegated',
          }
        : null;
    }).filter(Boolean),
    policy: complexity === 'complex'
      ? 'delegate-specialists-before-execution'
      : 'keep-execution-tight',
  };
}

module.exports = {
  buildDelegationPlan,
};
