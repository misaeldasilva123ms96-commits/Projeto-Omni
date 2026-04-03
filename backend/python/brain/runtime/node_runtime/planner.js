const { strategyForIntent } = require('./registry');

function buildExecutionPlan(strategy) {
  switch (strategy) {
    case 'business_plan':
      return ['avaliar contexto', 'selecionar oportunidade', 'montar proposta inicial'];
    case 'learning_path':
      return ['diagnosticar nivel atual', 'ordenar fundamentos', 'propor pratica real'];
    case 'decision_help':
    case 'practical_advice':
      return ['entender tradeoff', 'avaliar energia e risco', 'recomendar proximo passo'];
    case 'structured_explanation':
      return ['definir conceito', 'explicar impacto', 'dar exemplo util'];
    case 'identity_reply':
      return ['avaliar memoria do usuario', 'explicar identidade do sistema', 'manter continuidade'];
    default:
      return ['entender objetivo', 'responder com utilidade'];
  }
}

function decide(thought) {
  return strategyForIntent(thought.intent, thought.availableCapabilities);
}

function plan(thought, decision) {
  return {
    strategy: decision.strategy,
    executionPlan: buildExecutionPlan(decision.strategy),
    delegates: thought.delegates,
  };
}

module.exports = {
  decide,
  plan,
  buildExecutionPlan,
};
