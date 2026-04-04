const { strategyForIntent } = require('./registry');

function buildExecutionPlan(strategy) {
  switch (strategy) {
    case 'greeting_reply':
      return ['reconhecer a saudacao', 'confirmar disponibilidade', 'convidar para o proximo passo'];
    case 'direct_answer':
      return ['identificar a pergunta principal', 'responder de forma objetiva', 'oferecer continuidade'];
    case 'comparative_analysis':
      return ['definir criterio de comparacao', 'avaliar pontos fortes e fracos', 'fechar com recomendacao contextual'];
    case 'specific_plan':
      return ['definir objetivo e publico', 'estruturar operacao inicial', 'montar validacao e crescimento'];
    case 'idea_generation':
      return ['mapear oportunidade', 'propor ideias viaveis', 'apontar primeiro teste'];
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
  const decision = strategyForIntent(thought.intent, thought.availableCapabilities, thought.strategyState);
  return {
    ...decision,
    intent: thought.intent,
    taskCategory: thought.taskCategory,
    promptComplexity: thought.promptComplexity,
  };
}

function plan(thought, decision) {
  return {
    strategy: decision.strategy,
    executionPlan: buildExecutionPlan(decision.strategy),
    complexity: thought.promptComplexity.isComplex ? 'high' : thought.recentHistory.length > 2 ? 'medium' : 'normal',
    taskCategory: thought.taskCategory,
    adaptive: decision.adaptive || {},
  };
}

module.exports = {
  decide,
  plan,
};
