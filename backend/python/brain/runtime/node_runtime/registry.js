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
  const source = Array.isArray(capabilities) && capabilities.length > 0
    ? capabilities
    : CAPABILITIES;

  return Object.fromEntries(
    source
      .filter(item => item && typeof item.name === 'string')
      .map(item => [item.name, item]),
  );
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

function strategyForIntent(intent, availableCapabilities) {
  const canPlan = availableCapabilities.includes('create_plan');
  const canAdvise = availableCapabilities.includes('give_advice');
  const canIdeate = availableCapabilities.includes('generate_idea');
  const canCompare = availableCapabilities.includes('compare_options');

  switch (intent) {
    case 'saudacao':
      return { strategy: 'greeting_reply', confidence: 0.99 };
    case 'pergunta_direta':
      return { strategy: 'direct_answer', confidence: 0.9 };
    case 'comparativo':
      return { strategy: canCompare ? 'comparative_analysis' : 'structured_explanation', confidence: 0.92 };
    case 'planejamento':
      return { strategy: canPlan ? 'specific_plan' : 'business_plan', confidence: 0.91 };
    case 'ideacao':
      return { strategy: canIdeate ? 'idea_generation' : 'business_plan', confidence: 0.9 };
    case 'decision':
      return { strategy: canAdvise ? 'decision_help' : 'contextual_conversation', confidence: 0.92 };
    case 'dinheiro':
      return { strategy: canIdeate ? 'business_plan' : 'contextual_conversation', confidence: 0.9 };
    case 'conselho':
      return { strategy: canAdvise ? 'practical_advice' : 'contextual_conversation', confidence: 0.86 };
    case 'aprendizado':
      return { strategy: canPlan ? 'learning_path' : 'structured_explanation', confidence: 0.89 };
    case 'pessoal':
      return { strategy: 'identity_reply', confidence: 0.95 };
    case 'explicacao':
      return { strategy: 'structured_explanation', confidence: 0.88 };
    default:
      return { strategy: 'contextual_conversation', confidence: 0.76 };
  }
}

module.exports = {
  normalizeText,
  AGENTS,
  CAPABILITIES,
  listAgents,
  listCapabilities,
  buildCapabilityMap,
  resolveDelegatesByIntent,
  strategyForIntent,
};