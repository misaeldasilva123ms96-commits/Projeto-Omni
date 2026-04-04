function normalizeText(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

const AGENTS = [
  {
    id: 'orchestrator_agent',
    name: 'OrchestratorAgent',
    specialty: 'coordena o runtime cognitivo e consolida o resultado final',
    capabilities: ['route_work', 'compose_response'],
    priority: 1,
    active: true,
  },
  {
    id: 'planner_agent',
    name: 'PlannerAgent',
    specialty: 'decomposicao de objetivos e definicao de passos',
    capabilities: ['create_plan'],
    priority: 2,
    active: true,
  },
  {
    id: 'researcher_agent',
    name: 'ResearcherAgent',
    specialty: 'analise de contexto, historico e memoria do usuario',
    capabilities: ['analyze_context', 'summarize_context'],
    priority: 3,
    active: true,
  },
  {
    id: 'executor_agent',
    name: 'ExecutorAgent',
    specialty: 'execucao da estrategia e geracao da resposta de trabalho',
    capabilities: ['generate_idea', 'give_advice', 'create_plan', 'explain_topic', 'compare_options'],
    priority: 4,
    active: true,
  },
  {
    id: 'reviewer_agent',
    name: 'ReviewerAgent',
    specialty: 'revisao de qualidade e saneamento da resposta final',
    capabilities: ['review_response'],
    priority: 5,
    active: true,
  },
  {
    id: 'memory_agent',
    name: 'MemoryAgent',
    specialty: 'sinais de memoria, contexto util e consolidacao',
    capabilities: ['memory_lookup', 'memory_signal'],
    priority: 6,
    active: true,
  },
];

const CAPABILITIES = [
  { name: 'route_work', description: 'seleciona fluxo multiagente', category: 'orchestration' },
  { name: 'compose_response', description: 'organiza a resposta final', category: 'orchestration' },
  { name: 'analyze_context', description: 'analisa historico, memoria e objetivo atual', category: 'analysis' },
  { name: 'summarize_context', description: 'resume contexto relevante', category: 'analysis' },
  { name: 'create_plan', description: 'decompoe um objetivo em passos curtos', category: 'planning' },
  { name: 'generate_idea', description: 'gera ideias de negocio ou iniciativa', category: 'strategy' },
  { name: 'give_advice', description: 'gera orientacao pratica e contextual', category: 'guidance' },
  { name: 'explain_topic', description: 'explica conceitos de forma clara', category: 'knowledge' },
  { name: 'compare_options', description: 'compara opcoes com pros e contras', category: 'analysis' },
  { name: 'review_response', description: 'revisa clareza, utilidade e repeticao', category: 'quality' },
  { name: 'memory_lookup', description: 'consulta sinais de memoria atuais', category: 'memory' },
  { name: 'memory_signal', description: 'gera sugestoes de consolidacao', category: 'memory' },
];

function listAgents() {
  return AGENTS.filter(agent => agent.active !== false).slice();
}

function listCapabilities() {
  return CAPABILITIES.slice();
}

function buildCapabilityMap(capabilities) {
  const source = Array.isArray(capabilities) && capabilities.length > 0 ? capabilities : CAPABILITIES;
  return Object.fromEntries(source.filter(item => item && typeof item.name === 'string').map(item => [item.name, item]));
}

function resolveDelegatesByIntent(intent) {
  switch (intent) {
    case 'saudacao':
    case 'pergunta_direta':
      return ['researcher_agent', 'executor_agent', 'reviewer_agent', 'memory_agent'];
    case 'comparativo':
    case 'planejamento':
    case 'ideacao':
    case 'decision':
    case 'conselho':
    case 'dinheiro':
    case 'aprendizado':
      return ['researcher_agent', 'planner_agent', 'executor_agent', 'reviewer_agent', 'memory_agent'];
    case 'explicacao':
    case 'pessoal':
      return ['researcher_agent', 'executor_agent', 'reviewer_agent', 'memory_agent'];
    default:
      return ['researcher_agent', 'executor_agent', 'reviewer_agent', 'memory_agent'];
  }
}

function normalizeStrategyState(strategyState) {
  if (!strategyState || typeof strategyState !== 'object') {
    return {
      params: {
        complex_prompt_word_threshold: 20,
        heuristic_success_floor: 0.72,
        llm_success_floor: 0.68,
        prefer_llm_margin: 0.05,
      },
      strategies: {},
      intent_profiles: {},
      category_scores: {},
      registry_overrides: {},
    };
  }

  return {
    params: {
      complex_prompt_word_threshold: 20,
      heuristic_success_floor: 0.72,
      llm_success_floor: 0.68,
      prefer_llm_margin: 0.05,
      ...(strategyState.params && typeof strategyState.params === 'object' ? strategyState.params : {}),
    },
    strategies: strategyState.strategies && typeof strategyState.strategies === 'object' ? strategyState.strategies : {},
    intent_profiles: strategyState.intent_profiles && typeof strategyState.intent_profiles === 'object' ? strategyState.intent_profiles : {},
    category_scores: strategyState.category_scores && typeof strategyState.category_scores === 'object' ? strategyState.category_scores : {},
    registry_overrides: strategyState.registry_overrides && typeof strategyState.registry_overrides === 'object' ? strategyState.registry_overrides : {},
  };
}

function getStrategyEntry(strategyState, strategyName) {
  return normalizeStrategyState(strategyState).strategies[strategyName] || {};
}

function getIntentPriority(intent, strategyState) {
  const normalized = normalizeStrategyState(strategyState);
  const intentPriority = normalized.registry_overrides.intent_priority;
  if (!intentPriority || typeof intentPriority !== 'object') {
    return 1;
  }
  return Number(intentPriority[intent] || 1);
}

function strategyScore(strategyName, intent, strategyState) {
  const normalized = normalizeStrategyState(strategyState);
  const entry = normalized.strategies[strategyName] || {};
  const perIntent = entry.per_intent && typeof entry.per_intent === 'object' ? entry.per_intent[intent] || {} : {};
  const biasMap = normalized.registry_overrides.strategy_bias || {};
  const baseAverage = Number(entry.average_score || 0.65);
  const intentAverage = Number(perIntent.average_score || baseAverage);
  const feedbackScore = Number(entry.feedback_score || 0);
  const failures = Number(entry.failure_count || 0);
  const uses = Number(entry.total_uses || 0);
  const bias = Number((biasMap[strategyName] || {}).bias || 0);
  const sampleBonus = uses >= 3 ? 0.04 : 0;
  const failurePenalty = failures >= 3 ? 0.08 : 0;
  return intentAverage + feedbackScore * 0.08 + bias + sampleBonus - failurePenalty;
}

function chooseBestStrategy(candidates, intent, strategyState, fallbackStrategy) {
  if (!Array.isArray(candidates) || candidates.length === 0) {
    return fallbackStrategy;
  }

  let winner = fallbackStrategy;
  let bestScore = -Infinity;
  for (const candidate of candidates) {
    const score = strategyScore(candidate, intent, strategyState);
    if (score > bestScore) {
      bestScore = score;
      winner = candidate;
    }
  }
  return winner;
}

function strategyForIntent(intent, availableCapabilities, strategyState) {
  const canPlan = availableCapabilities.includes('create_plan');
  const canAdvise = availableCapabilities.includes('give_advice');
  const canIdeate = availableCapabilities.includes('generate_idea');
  const canCompare = availableCapabilities.includes('compare_options');
  const normalized = normalizeStrategyState(strategyState);

  let base = { strategy: 'contextual_conversation', confidence: 0.76, candidates: ['contextual_conversation'] };
  switch (intent) {
    case 'saudacao':
      base = { strategy: 'greeting_reply', confidence: 0.99, candidates: ['greeting_reply'] };
      break;
    case 'pergunta_direta':
      base = { strategy: 'direct_answer', confidence: 0.9, candidates: ['direct_answer', 'structured_explanation'] };
      break;
    case 'comparativo':
      base = { strategy: canCompare ? 'comparative_analysis' : 'structured_explanation', confidence: 0.92, candidates: ['comparative_analysis', 'structured_explanation'] };
      break;
    case 'planejamento':
      base = { strategy: canPlan ? 'specific_plan' : 'business_plan', confidence: 0.91, candidates: ['specific_plan', 'business_plan'] };
      break;
    case 'ideacao':
      base = { strategy: canIdeate ? 'idea_generation' : 'business_plan', confidence: 0.9, candidates: ['idea_generation', 'business_plan'] };
      break;
    case 'decision':
      base = { strategy: canAdvise ? 'decision_help' : 'contextual_conversation', confidence: 0.92, candidates: ['decision_help', 'practical_advice', 'contextual_conversation'] };
      break;
    case 'dinheiro':
      base = { strategy: canIdeate ? 'business_plan' : 'contextual_conversation', confidence: 0.9, candidates: ['business_plan', 'specific_plan', 'contextual_conversation'] };
      break;
    case 'conselho':
      base = { strategy: canAdvise ? 'practical_advice' : 'contextual_conversation', confidence: 0.86, candidates: ['practical_advice', 'decision_help', 'contextual_conversation'] };
      break;
    case 'aprendizado':
      base = { strategy: canPlan ? 'learning_path' : 'structured_explanation', confidence: 0.89, candidates: ['learning_path', 'structured_explanation'] };
      break;
    case 'pessoal':
      base = { strategy: 'identity_reply', confidence: 0.95, candidates: ['identity_reply'] };
      break;
    case 'explicacao':
      base = { strategy: 'structured_explanation', confidence: 0.88, candidates: ['structured_explanation', 'direct_answer'] };
      break;
    default:
      base = { strategy: 'contextual_conversation', confidence: 0.76, candidates: ['contextual_conversation', 'direct_answer'] };
      break;
  }

  const intentProfile = normalized.intent_profiles[intent];
  const adaptiveStrategy = chooseBestStrategy(base.candidates, intent, normalized, base.strategy);
  const preferredStrategy = intentProfile && typeof intentProfile === 'object' ? intentProfile.preferred_strategy : '';
  const finalStrategy = preferredStrategy && base.candidates.includes(preferredStrategy) ? preferredStrategy : adaptiveStrategy;

  return {
    strategy: finalStrategy,
    confidence: Math.min(0.99, base.confidence * getIntentPriority(intent, normalized)),
    adaptive: {
      candidates: base.candidates,
      preferredStrategy: preferredStrategy || finalStrategy,
      intentScore: intentProfile && typeof intentProfile === 'object' ? Number(intentProfile.average_score || 0) : 0,
    },
  };
}

module.exports = {
  normalizeText,
  AGENTS,
  CAPABILITIES,
  listAgents,
  listCapabilities,
  buildCapabilityMap,
  resolveDelegatesByIntent,
  normalizeStrategyState,
  getStrategyEntry,
  strategyForIntent,
};
