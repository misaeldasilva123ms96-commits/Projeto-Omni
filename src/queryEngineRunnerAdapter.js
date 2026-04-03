function normalizeText(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function getUserMemory(memoryContext) {
  const user = memoryContext?.user;
  if (!user || typeof user !== 'object') {
    return { nome: '', preferencias: [] };
  }

  return {
    nome: typeof user.nome === 'string' ? user.nome.trim() : '',
    preferencias: Array.isArray(user.preferencias)
      ? user.preferencias.map(item => String(item).trim()).filter(Boolean)
      : [],
  };
}

function getRecentUserMessages(history) {
  if (!Array.isArray(history)) {
    return [];
  }

  return history
    .filter(item => item?.role === 'user' && typeof item?.content === 'string')
    .map(item => item.content.trim())
    .filter(Boolean)
    .slice(-6);
}

function buildContextSummary(history, summary, session) {
  if (summary && String(summary).trim()) {
    return String(summary).trim();
  }

  const sessionSummary = session?.summary;
  if (typeof sessionSummary === 'string' && sessionSummary.trim()) {
    return sessionSummary.trim();
  }

  const recent = getRecentUserMessages(history);
  if (recent.length === 0) {
    return 'Sem contexto anterior relevante.';
  }

  return recent.join(' | ');
}

function detectIntent(message, recentHistory) {
  const msg = normalizeText(message);
  const historyText = normalizeText(recentHistory.join(' '));

  if (
    msg.includes('devo') ||
    msg.includes(' ou ') ||
    msg.includes('qual e melhor') ||
    msg.includes('o que eu faco') ||
    msg.includes('o que fazer') ||
    msg.includes('vale a pena') ||
    msg.includes('melhor opcao')
  ) {
    return 'decision';
  }

  if (
    msg.includes('ganhar dinheiro') ||
    msg.includes('negocio') ||
    msg.includes('dinheiro') ||
    msg.includes('renda') ||
    msg.includes('vender online')
  ) {
    return 'dinheiro';
  }

  if (
    msg.includes('quero aprender') ||
    msg.includes('por onde comeco') ||
    msg.includes('programacao') ||
    msg.includes('estudar') ||
    historyText.includes('quero aprender')
  ) {
    return 'aprendizado';
  }

  if (
    msg.includes('como melhorar') ||
    msg.includes('conselho') ||
    msg.includes('dica')
  ) {
    return 'conselho';
  }

  if (
    msg.includes('o que e') ||
    msg.includes('explique') ||
    msg.includes('por que') ||
    msg.includes('porque') ||
    msg.includes('como funciona')
  ) {
    return 'explicacao';
  }

  if (
    msg.includes('quem e voce') ||
    msg.includes('como voce responde') ||
    msg.includes('como voce funciona')
  ) {
    return 'pessoal';
  }

  return 'conversa';
}

function buildCapabilityMap(capabilities) {
  if (!Array.isArray(capabilities)) {
    return {};
  }

  return Object.fromEntries(
    capabilities
      .filter(item => item && typeof item === 'object' && typeof item.name === 'string')
      .map(item => [item.name, item]),
  );
}

function getDefaultAgentRegistry() {
  return [
    {
      id: 'router_agent',
      name: 'RouterAgent',
      specialty: 'roteamento de intent',
      capabilities: ['give_advice', 'create_plan'],
      priority: 1,
      active: true,
    },
    {
      id: 'planner_agent',
      name: 'PlannerAgent',
      specialty: 'decomposicao de objetivos',
      capabilities: ['create_plan'],
      priority: 2,
      active: true,
    },
    {
      id: 'executor_agent',
      name: 'ExecutorAgent',
      specialty: 'execucao e consolidacao',
      capabilities: ['generate_idea', 'give_advice', 'create_plan'],
      priority: 3,
      active: true,
    },
    {
      id: 'critic_agent',
      name: 'CriticAgent',
      specialty: 'revisao final',
      capabilities: ['give_advice'],
      priority: 4,
      active: true,
    },
    {
      id: 'memory_agent',
      name: 'MemoryAgent',
      specialty: 'memoria e consolidacao',
      capabilities: ['create_plan'],
      priority: 5,
      active: true,
    },
  ];
}

function buildAgentRegistry(session) {
  const registry = Array.isArray(session?.agent_registry)
    ? session.agent_registry.filter(item => item && typeof item.id === 'string')
    : getDefaultAgentRegistry();

  return Object.fromEntries(registry.map(item => [item.id, item]));
}

function resolveDelegateAliases(intent) {
  switch (intent) {
    case 'dinheiro':
      return ['planner', 'executor', 'critic', 'memory'];
    case 'aprendizado':
      return ['planner', 'memory', 'executor', 'critic'];
    case 'decision':
    case 'conselho':
      return ['planner', 'executor', 'critic', 'memory'];
    case 'explicacao':
      return ['executor', 'critic', 'memory'];
    default:
      return ['executor', 'memory', 'critic'];
  }
}

function resolveDelegateIds(delegateAliases, registryMap) {
  const aliasMap = {
    planner: 'planner_agent',
    advisor: 'critic_agent',
    assistant: 'executor_agent',
    teacher: 'planner_agent',
    executor: 'executor_agent',
    critic: 'critic_agent',
    memory: 'memory_agent',
    router: 'router_agent',
  };

  return delegateAliases
    .map(alias => aliasMap[alias] || alias)
    .filter(agentId => registryMap[agentId]?.active !== false);
}

function think(message, memoryContext, history, summary, capabilities, session) {
  const userMemory = getUserMemory(memoryContext);
  const recentHistory = getRecentUserMessages(history);
  const capabilityMap = buildCapabilityMap(capabilities);
  const intent = detectIntent(message, recentHistory);
  const registryMap = buildAgentRegistry(session);
  const delegateAliases = resolveDelegateAliases(intent);

  return {
    intent,
    userName: userMemory.nome,
    preferences: userMemory.preferencias,
    contextSummary: buildContextSummary(history, summary, session),
    message,
    recentHistory,
    capabilityMap,
    availableCapabilities: Object.keys(capabilityMap),
    session,
    delegateAliases,
    delegates: resolveDelegateIds(delegateAliases, registryMap),
    registryMap,
    swarmRequest: session?.swarm_request || {},
  };
}

function decide(thought) {
  const canPlan = thought.availableCapabilities.includes('create_plan');
  const canAdvise = thought.availableCapabilities.includes('give_advice');
  const canIdeate = thought.availableCapabilities.includes('generate_idea');

  switch (thought.intent) {
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
      return { strategy: 'structured_explanation', confidence: 0.83 };
    default:
      return { strategy: 'contextual_conversation', confidence: 0.74 };
  }
}

function hasPreference(preferences, keyword) {
  return preferences.some(item => normalizeText(item).includes(keyword));
}

function buildExecutionPlan(decision) {
  switch (decision.strategy) {
    case 'business_plan':
      return ['avaliar contexto', 'selecionar oportunidade', 'montar proposta inicial'];
    case 'learning_path':
      return ['diagnosticar nivel atual', 'ordenar fundamentos', 'propor pratica real'];
    case 'decision_help':
    case 'practical_advice':
      return ['entender tradeoff', 'avaliar energia e risco', 'recomendar proximo passo'];
    case 'structured_explanation':
      return ['definir conceito', 'explicar impacto', 'dar exemplo util'];
    default:
      return ['entender objetivo', 'responder com utilidade'];
  }
}

async function invokePlannerAgent(thought, decision) {
  return {
    agentId: 'planner_agent',
    kind: 'planning',
    result: buildExecutionPlan(decision),
    summary: `Planner estruturou ${decision.strategy} em ${buildExecutionPlan(decision).length} etapas.`,
  };
}

async function invokeExecutorAgent(thought, decision) {
  const msg = normalizeText(thought.message);
  const likesTech =
    hasPreference(thought.preferences, 'tecnologia') ||
    hasPreference(thought.preferences, 'programacao');

  if (decision.strategy === 'business_plan') {
    return {
      agentId: 'executor_agent',
      kind: 'execution',
      payload: msg.includes('ideia de negocio')
        ? (likesTech
          ? [
              'Validar um servico de automacao simples para negocios locais.',
              'Oferecer implantacao rapida com mensalidade leve.',
              'Fechar os primeiros clientes antes de ampliar o escopo.',
            ]
          : [
              'Escolher um problema simples e frequente de um publico especifico.',
              'Montar uma oferta pequena e facil de vender.',
              'Testar rapido com clientes reais antes de investir mais.',
            ])
        : [
            'Combine habilidade vendavel com execucao constante.',
            'Crie uma oferta simples e resolva um problema real.',
            'Busque validacao rapida antes de pensar em escalar.',
          ],
    };
  }

  if (decision.strategy === 'learning_path') {
    return {
      agentId: 'executor_agent',
      kind: 'execution',
      steps: [
        'Comece pelos fundamentos antes de buscar velocidade.',
        'Pratique no mesmo dia com exercicios curtos.',
        'Transforme o estudo em um projeto pequeno e concluido.',
      ],
    };
  }

  if (decision.strategy === 'decision_help' || decision.strategy === 'practical_advice') {
    return {
      agentId: 'executor_agent',
      kind: 'execution',
      analysis: [
        'A melhor escolha depende do seu estado atual e do impacto imediato de cada opcao.',
        'Em geral, vale priorizar a opcao que cria progresso sem gerar desgaste desnecessario.',
      ],
      recommendation: 'Compare as opcoes pelo custo de energia e pelo ganho pratico no curto prazo.',
    };
  }

  if (decision.strategy === 'structured_explanation') {
    return {
      agentId: 'executor_agent',
      kind: 'execution',
      explanation: [
        'Definir com clareza o conceito central.',
        'Mostrar por que isso importa na pratica.',
        'Traduzir a ideia em exemplo simples e acionavel.',
      ],
    };
  }

  return {
    agentId: 'executor_agent',
    kind: 'execution',
    conversation:
      thought.recentHistory.length > 0
        ? 'Vou continuar a partir do contexto recente e focar no proximo passo mais util.'
        : 'Vou responder de forma direta e util com base no que voce perguntou.',
  };
}

async function invokeCriticAgent(thought, decision, current) {
  const issues = [];
  if (!current || typeof current !== 'object') {
    issues.push('sem payload');
  }
  if (thought.contextSummary === 'Sem contexto anterior relevante.' && thought.recentHistory.length === 0) {
    issues.push('baixo contexto historico');
  }
  return {
    agentId: 'critic_agent',
    kind: 'critique',
    issues,
    approved: true,
    qualityScore: issues.length === 0 ? 0.9 : 0.72,
  };
}

async function invokeMemoryAgent(thought) {
  return {
    agentId: 'memory_agent',
    kind: 'memory',
    memoryHint: {
      userName: thought.userName,
      preferences: thought.preferences,
      contextSummary: thought.contextSummary,
    },
  };
}

async function invokeRouterAgent(thought, decision) {
  return {
    agentId: 'router_agent',
    kind: 'route',
    route: {
      intent: thought.intent,
      strategy: decision.strategy,
      delegates: thought.delegates,
    },
  };
}

async function dispatchToAgent(agentId, thought, decision, currentState) {
  switch (agentId) {
    case 'planner_agent':
      return invokePlannerAgent(thought, decision, currentState);
    case 'executor_agent':
      return invokeExecutorAgent(thought, decision, currentState);
    case 'critic_agent':
      return invokeCriticAgent(thought, decision, currentState);
    case 'memory_agent':
      return invokeMemoryAgent(thought, decision, currentState);
    case 'router_agent':
      return invokeRouterAgent(thought, decision, currentState);
    default:
      return { agentId, kind: 'noop', result: null };
  }
}

async function resolveDelegates(thought, decision) {
  const ipcEnvelope = thought.delegates.map(agentId => ({
    to: agentId,
    type: 'task',
    payload: {
      message: thought.message,
      intent: thought.intent,
      strategy: decision.strategy,
    },
  }));

  const results = await Promise.all(
    ipcEnvelope.map(async envelope => dispatchToAgent(envelope.to, thought, decision, envelope.payload)),
  );

  return {
    route: results.find(item => item.agentId === 'router_agent') || null,
    planner: results.find(item => item.agentId === 'planner_agent') || null,
    executor: results.find(item => item.agentId === 'executor_agent') || null,
    critic: results.find(item => item.agentId === 'critic_agent') || null,
    memory: results.find(item => item.agentId === 'memory_agent') || null,
    all: results,
  };
}

function act(decision, thought, delegateResults) {
  const executionPlan = delegateResults.planner?.result || buildExecutionPlan(decision);
  const executorPayload = delegateResults.executor || { kind: 'execution' };

  return {
    executionPlan,
    delegateResults,
    executorPayload,
  };
}

function updateMemory(actionResult, thought) {
  return {
    intent: thought.intent,
    usedName: Boolean(thought.userName),
    usedPreferences: thought.preferences.length > 0,
    executionPlan: actionResult.executionPlan || [],
    delegates: thought.delegates,
    memoryHint: actionResult.delegateResults.memory?.memoryHint || {},
  };
}

function maybeUseName(thought) {
  return thought.userName ? `${thought.userName}, ` : '';
}

function respond(actionResult, thought, memorySignal, decision) {
  const opener = maybeUseName(thought);
  const executorPayload = actionResult.executorPayload;

  switch (thought.intent) {
    case 'decision':
    case 'conselho':
      return {
        response: `${opener}${executorPayload.analysis[0]} ${executorPayload.analysis[1]} ${executorPayload.recommendation}`,
        confidence: decision.confidence,
        memory: memorySignal,
      };
    case 'dinheiro':
      return {
        response: `${opener}eu seguiria um caminho realista:\n1. ${executorPayload.payload[0]}\n2. ${executorPayload.payload[1]}\n3. ${executorPayload.payload[2]}`,
        confidence: decision.confidence,
        memory: memorySignal,
      };
    case 'aprendizado':
      return {
        response: `${opener}o melhor caminho agora e este:\n1. ${executorPayload.steps[0]}\n2. ${executorPayload.steps[1]}\n3. ${executorPayload.steps[2]}`,
        confidence: decision.confidence,
        memory: memorySignal,
      };
    case 'pessoal':
      return {
        response: thought.userName
          ? 'Sou uma IA orientada a contexto, memoria, decisao pratica e aprendizado progressivo. Tambem levo em conta o que voce ja me contou, ' + thought.userName + '.'
          : 'Sou uma IA orientada a contexto, memoria, decisao pratica e aprendizado progressivo. Meu trabalho e entender o que voce quer e devolver algo util.',
        confidence: decision.confidence,
        memory: memorySignal,
      };
    case 'explicacao':
      return {
        response: `${opener}eu pensaria assim: ${executorPayload.explanation[0]}, depois ${executorPayload.explanation[1]} e por fim ${executorPayload.explanation[2]}.`,
        confidence: decision.confidence,
        memory: memorySignal,
      };
    default:
      return {
        response: `${opener}${executorPayload.conversation} Se quiser, me diga o objetivo principal e eu organizo a resposta com mais precisao.`,
        confidence: decision.confidence,
        memory: memorySignal,
      };
  }
}

async function runQueryEngine({ message, memoryContext, history, summary, capabilities, session }) {
  const thought = think(message, memoryContext, history, summary, capabilities, session);
  const decision = decide(thought);
  const delegateResults = await resolveDelegates(thought, decision);
  const actionResult = act(decision, thought, delegateResults);
  const memorySignal = updateMemory(actionResult, thought);
  return respond(actionResult, thought, memorySignal, decision);
}

module.exports = {
  runQueryEngine,
};
