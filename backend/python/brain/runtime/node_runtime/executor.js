const { normalizeText, normalizeStrategyState, getStrategyEntry } = require('./registry');
const { hasPreference } = require('./memory');
const { generateResponse } = require('./llm_adapter');

function capitalize(value) {
  if (!value) {
    return '';
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function extractExplanationTopic(message) {
  const normalized = normalizeText(message);
  const patterns = [
    /^o que e\s+(.+)$/,
    /^o que\s+(.+)$/,
    /^oque e\s+(.+)$/,
    /^oque\s+(.+)$/,
    /^oq e\s+(.+)$/,
    /^oq\s+(.+)$/,
    /^explique\s+(.+)$/,
    /^como funciona\s+(.+)$/,
    /^me diga o que e\s+(.+)$/,
  ];

  for (const pattern of patterns) {
    const match = normalized.match(pattern);
    if (match && match[1]) {
      return match[1].trim();
    }
  }

  const compact = normalized.replace(/[?!.]+$/g, '').trim();
  if (compact === 'btc') {
    return 'bitcoin';
  }
  if (compact === 'cripto') {
    return 'criptomoeda';
  }
  return compact;
}

function limitSentences(text, count) {
  if (!count || count <= 0) {
    return text;
  }
  return text.split(/(?<=[.!?])\s+/).filter(Boolean).slice(0, count).join(' ');
}

function buildExplanation(topic, depthPreference, constraints = {}) {
  const deep = depthPreference === 'deep';
  const normalizedTopic = normalizeText(topic).replace(/\bbtc\b/g, 'bitcoin').replace(/\bcripto\b/g, 'criptomoeda');
  let text = '';

  if (normalizedTopic.includes('machine learning')) {
    text = [
      'Machine learning e uma forma de treinar sistemas para reconhecer padroes em dados e melhorar previsoes com a experiencia.',
      'Na pratica, o modelo recebe exemplos, ajusta parametros internos e aprende a responder melhor para casos parecidos no futuro.',
      'Isso e usado em recomendacao, deteccao de fraude, visao computacional e assistentes inteligentes.',
      deep ? 'Os principais estilos incluem aprendizado supervisionado, nao supervisionado e por reforco, cada um adequado para problemas diferentes.' : '',
    ].filter(Boolean).join(' ');
  } else if (normalizedTopic.includes('blockchain')) {
    text = [
      'Blockchain e um registro digital distribuido que organiza informacoes em blocos conectados em sequencia.',
      'Ela funciona mantendo copias sincronizadas do mesmo historico em varios participantes da rede, o que dificulta alteracoes indevidas.',
      deep
        ? 'Por isso ela e util quando varias partes precisam confiar no mesmo registro sem depender de um unico servidor central.'
        : 'Na pratica, isso permite rastrear transacoes com transparencia, como acontece no funcionamento das criptomoedas.',
    ].join(' ');
  } else if (normalizedTopic.includes('bitcoin') || normalizedTopic === 'btc' || normalizedTopic.endsWith(' btc')) {
    text = [
      'Bitcoin e uma criptomoeda criada para permitir transferencias de valor pela internet sem depender de uma autoridade central.',
      'Ele funciona em uma rede descentralizada, onde as transacoes sao validadas e registradas em blockchain.',
      'Na pratica, ele pode ser usado para transferir valor digitalmente e tambem como referencia no mercado de criptoativos.',
    ].join(' ');
  } else if (normalizedTopic.includes('criptomoeda') || normalizedTopic === 'cripto') {
    text = [
      'Criptomoeda e um ativo digital que usa criptografia para registrar transferencias e proteger a rede contra fraude.',
      'Em vez de depender de um banco central, ela costuma operar em uma rede distribuida, muitas vezes apoiada por blockchain.',
      deep
        ? 'Na pratica, criptomoedas podem servir para transferencia de valor, reserva especulativa ou infraestrutura financeira programavel, mas variam bastante em risco e utilidade.'
        : 'Na pratica, isso permite mover valor digitalmente entre pessoas e sistemas sem depender do modelo bancario tradicional.',
    ].join(' ');
  } else {
    const title = capitalize(normalizedTopic || 'esse tema');
    text = `${title} e um conceito importante que pode ser entendido pelo que ele faz, por como funciona e por onde costuma ser aplicado. O ponto principal e identificar sua funcao central e por que isso importa na pratica.`;
  }

  if (constraints.maxSentences) {
    return limitSentences(text, constraints.maxSentences);
  }
  if (constraints.singleSentence) {
    return limitSentences(text, 1);
  }
  return text;
}

function buildComparativeAnalysis(message) {
  const msg = normalizeText(message);

  if (msg.includes('python') && msg.includes('rust')) {
    return 'Python e Rust podem funcionar muito bem em producao para sistemas de IA, mas brilham em pontos diferentes. Python acelera pesquisa, prototipagem e integracao com bibliotecas de dados e machine learning, enquanto Rust entrega desempenho previsivel, baixo consumo de memoria e mais seguranca para componentes criticos. Em contrapartida, Python tende a sofrer mais com gargalos de performance em partes sensiveis, e Rust exige mais tempo de desenvolvimento e uma curva maior para a equipe. Se o foco e iterar rapido no cerebro e nos experimentos, Python costuma ser a melhor base; se o foco e runtime critico e throughput, vale usar Rust nas partes mais sensiveis ou em uma arquitetura hibrida.';
  }

  return 'A comparacao precisa olhar criterios concretos como custo, desempenho, risco, curva de aprendizado e impacto operacional, separando claramente vantagens, limitacoes e a recomendacao final conforme o contexto.';
}

function buildSpecificPlan(message, thought, constraints = {}) {
  const msg = normalizeText(message);
  const requestedSteps = constraints.stepCount || 5;

  if (msg.includes('delivery')) {
    const steps = [
      'Escolha um nicho com dor clara, como entregas de restaurantes locais ou mercados de bairro, e valide onde o tempo de entrega e a previsibilidade sao o maior problema.',
      'Monte uma operacao enxuta com painel simples para lojistas, aplicativo para pedidos e um fluxo de despacho bem definido antes de expandir funcionalidades.',
      'Teste a aquisicao em uma regiao pequena, acompanhe taxa de recompra, tempo medio de entrega e margem por pedido para ajustar o modelo.',
      'Refine a operacao com base nesses dados antes de ampliar cobertura geografica ou adicionar mais categorias.',
      thought.goals.length > 0
        ? `Como voce ja busca ${thought.goals[0]}, eu comecaria validando esse objetivo com uma operacao pequena e metricas claras.`
        : 'So depois de provar recorrencia, logistica viavel e unidade economica saudavel faz sentido escalar.'
    ];
    return [`Plano inicial para um app de delivery:`].concat(steps.slice(0, requestedSteps).map((step, index) => `${index + 1}. ${step}`)).join('\n');
  }

  const generic = [
    'Defina o problema, o publico e a proposta de valor de forma especifica.',
    'Crie uma versao inicial com o minimo necessario para validar uso real.',
    'Acompanhe metricas simples de adocao, retencao e receita antes de ampliar o escopo.',
    'Ajuste a oferta com base no uso real e no feedback dos primeiros clientes.',
    'So aumente investimento depois que houver sinais claros de tracao e repeticao do problema.',
  ];

  return [`Plano pratico de execucao:`].concat(generic.slice(0, requestedSteps).map((step, index) => `${index + 1}. ${step}`)).join('\n');
}

function buildIdeas(thought) {
  const likesTech = hasPreference(thought.preferences, 'tecnologia') || hasPreference(thought.preferences, 'ia');
  const worksWithAi = normalizeText(thought.work || '').includes('ia');

  if (likesTech || worksWithAi) {
    return [
      'Um copiloto de atendimento para pequenos negocios que transforma WhatsApp em funil de vendas com respostas, qualificacao e agendamento.',
      'Uma plataforma de auditoria de processos com IA para empresas de servico, capaz de detectar gargalos operacionais e sugerir melhorias semanais.',
      'Um agente de prospeccao para nichos locais que encontra leads, monta abordagem personalizada e mede conversao por campanha.',
    ];
  }

  return [
    'Um servico de automacao com IA para tarefas repetitivas de pequenas empresas, cobrado por assinatura simples.',
    'Uma ferramenta que resume reunioes, extrai decisoes e cria proximos passos automaticos para equipes enxutas.',
    'Uma solucao de analise de mensagens de clientes para identificar duvidas recorrentes e melhorar vendas e suporte.',
  ];
}

function buildBusinessPayload(thought) {
  return [
    'Escolha um problema frequente e caro para um publico especifico.',
    'Crie uma oferta simples, com implementacao rapida e beneficio facil de explicar.',
    'Valide com clientes reais antes de ampliar equipe, produto ou canais.',
  ];
}

function wordCount(message) {
  return normalizeText(message).split(/\s+/).filter(Boolean).length;
}

function isSimpleFastPath(thought, decision) {
  const normalizedMessage = normalizeText(thought.message).replace(/[?!.]+$/g, '').trim();
  const simpleConcepts = new Set(['btc', 'bitcoin', 'cripto', 'criptomoeda', 'blockchain']);

  if (decision.strategy === 'greeting_reply' || decision.strategy === 'memory_recall') {
    return true;
  }

  if (decision.strategy === 'structured_explanation' && simpleConcepts.has(normalizedMessage)) {
    return true;
  }

  return false;
}

function shouldUseLlm(strategy) {
  return [
    'structured_explanation',
    'comparative_analysis',
    'decision_help',
    'practical_advice',
    'specific_plan',
    'idea_generation',
    'business_plan',
    'learning_path',
    'direct_answer',
    'general_answer',
    'contextual_conversation',
    'creative_reasoning',
    'logic_solver',
    'memory_recall',
  ].includes(strategy);
}

function getModeStats(strategyState, strategyName, mode) {
  const entry = getStrategyEntry(strategyState, strategyName);
  const executionModes = entry.execution_modes && typeof entry.execution_modes === 'object' ? entry.execution_modes : {};
  return executionModes[mode] || {};
}

function chooseExecutionMode(thought, decision) {
  const strategyState = normalizeStrategyState(thought.strategyState);
  const strategyEntry = getStrategyEntry(strategyState, decision.strategy);
  const heuristicStats = getModeStats(strategyState, decision.strategy, 'heuristic');
  const llmStats = getModeStats(strategyState, decision.strategy, 'llm');
  const params = strategyState.params || {};
  const margin = Number(params.prefer_llm_margin || 0.05);
  const simplePrompt = isSimpleFastPath(thought, decision);
  const heuristicAvg = Number(heuristicStats.average_score || 0);
  const llmAvg = Number(llmStats.average_score || 0);
  const heuristicUses = Number(heuristicStats.uses || 0);
  const llmUses = Number(llmStats.uses || 0);
  const strategyAverage = Number(strategyEntry.average_score || 0.65);

  if (thought.highComplexity || thought.requiresLlm) {
    if (heuristicUses >= 8 && heuristicAvg >= llmAvg + margin && heuristicAvg >= Number(params.heuristic_success_floor || 0.72)) {
      return { mode: 'heuristic', reason: 'strong_complex_heuristic_history' };
    }
    return { mode: 'llm', reason: 'complex_prompt_forced_llm' };
  }

  if (simplePrompt) {
    if (llmUses >= 6 && llmAvg > heuristicAvg + margin) {
      return { mode: 'llm', reason: 'historical_llm_win' };
    }
    return { mode: 'heuristic', reason: 'simple_fast_path' };
  }

  if (llmUses >= 5 && llmAvg >= strategyAverage + margin) {
    return { mode: 'llm', reason: 'llm_outperforming' };
  }

  if (heuristicUses >= 5 && heuristicAvg >= Number(params.heuristic_success_floor || 0.72)) {
    return { mode: 'heuristic', reason: 'strong_heuristic_history' };
  }

  return { mode: shouldUseLlm(decision.strategy) ? 'llm' : 'heuristic', reason: 'default_hybrid' };
}

function buildDirectHeuristicAnswer(thought, decision, planResult) {
  const constraints = planResult?.constraints || {};

  switch (decision.strategy) {
    case 'greeting_reply':
      return 'Ola! Como posso te ajudar hoje?';
    case 'direct_answer':
      return thought.message && normalizeText(thought.message).includes('funcionando')
        ? 'Ola! Sim, estou funcionando e pronto para te ajudar com explicacoes, planejamento, analise e ideias praticas.'
        : 'Sim, estou pronto para te ajudar. Pode me dizer qual objetivo ou duvida voce quer resolver agora?';
    case 'structured_explanation':
      return buildExplanation(extractExplanationTopic(thought.message), thought.depthPreference, constraints);
    case 'comparative_analysis':
      return buildComparativeAnalysis(thought.message);
    case 'specific_plan':
      return buildSpecificPlan(thought.message, thought, constraints);
    case 'idea_generation': {
      const ideas = buildIdeas(thought);
      return `Aqui vao 3 ideias fortes:\n1. ${ideas[0]}\n2. ${ideas[1]}\n3. ${ideas[2]}`;
    }
    case 'business_plan': {
      const payload = buildBusinessPayload(thought);
      return `Eu seguiria um caminho realista:\n1. ${payload[0]}\n2. ${payload[1]}\n3. ${payload[2]}`;
    }
    case 'learning_path':
      return 'O melhor caminho agora e este:\n1. Comece pelos fundamentos antes de buscar velocidade.\n2. Pratique no mesmo dia com exercicios curtos e feedback rapido.\n3. Transforme o estudo em um projeto pequeno e concluido para consolidar o aprendizado.';
    case 'decision_help':
    case 'practical_advice':
      return 'A melhor escolha depende do contexto, do custo de energia e do impacto imediato de cada opcao. Em geral, vale priorizar a opcao que cria progresso real sem gerar desgaste desnecessario ou atrasar o proximo passo importante.';
    case 'memory_recall':
      if (thought.userName && normalizeText(thought.message).includes('nome')) {
        return `Seu nome e ${thought.userName}.`;
      }
      if (thought.work && normalizeText(thought.message).includes('trabalho')) {
        return `Voce trabalha com ${thought.work}.`;
      }
      return thought.userName || thought.work ? `${thought.userName ? `Seu nome e ${thought.userName}. ` : ''}${thought.work ? `Voce trabalha com ${thought.work}.` : ''}`.trim() : 'Ainda nao tenho esse dado salvo na memoria.';
    default:
      return 'Posso te ajudar com explicacoes, planos, comparacoes e ideias praticas.';
  }
}

function containsMetaResponse(text) {
  const normalized = normalizeText(text);
  return [
    'o mais util e',
    'eu responderia assim',
    'tratar este ponto',
    'vale mostrar por que isso importa',
    'sobre ',
  ].some(marker => normalized.includes(marker));
}

async function act(thought, decision, planResult) {
  const executionPlan = Array.isArray(planResult?.steps)
    ? planResult.steps
    : Array.isArray(planResult?.executionPlan)
      ? planResult.executionPlan
      : [];
  const constraints = planResult?.constraints && typeof planResult.constraints === 'object' ? planResult.constraints : {};
  const adaptiveMode = chooseExecutionMode(thought, decision);
  const trivialHeuristic = adaptiveMode.mode === 'heuristic' && !thought.highComplexity && !thought.requiresLlm;

  if (trivialHeuristic) {
    return {
      response: buildDirectHeuristicAnswer(thought, decision, planResult),
      confidence: decision.confidence || 0.82,
      memory: {},
      provider: 'local',
      latencyMs: 0,
      fallbackUsed: false,
      selectedMode: 'heuristic',
      adaptiveReason: adaptiveMode.reason,
      taskCategory: thought.taskCategory,
      executionPlan,
    };
  }

  const generated = await generateResponse({
    message: thought.message,
    strategy: decision.strategy,
    plan: executionPlan,
    context: {
      userId: thought.userId,
      userName: thought.userName,
      work: thought.work,
      preferences: thought.preferences,
      responseStyle: thought.responseStyle,
      depthPreference: thought.depthPreference,
      recurringTopics: thought.recurringTopics,
      goals: thought.goals,
      contextSummary: thought.contextSummary,
      constraints,
      targetOutput: planResult?.target_output || 'deliver the final answer only',
      taskCategory: thought.taskCategory,
      highComplexity: thought.highComplexity,
      requiresLlm: thought.requiresLlm,
    },
  });

  const response = typeof generated.text === 'string' && generated.text.trim()
    ? generated.text.trim()
    : buildDirectHeuristicAnswer(thought, decision, planResult);

  const safeResponse = containsMetaResponse(response) && (thought.highComplexity || thought.requiresLlm)
    ? buildDirectHeuristicAnswer(thought, decision, planResult)
    : response;

  return {
    response: safeResponse,
    confidence: decision.confidence || 0.82,
    memory: {},
    provider: generated.provider || (adaptiveMode.mode === 'llm' ? 'fallback' : 'local'),
    latencyMs: typeof generated.latencyMs === 'number' ? generated.latencyMs : 0,
    fallbackUsed: Boolean(generated.fallbackUsed) || generated.provider === 'fallback',
    selectedMode: adaptiveMode.mode === 'llm' ? 'llm' : 'heuristic',
    adaptiveReason: adaptiveMode.reason,
    taskCategory: thought.taskCategory,
    executionPlan,
  };
}

module.exports = {
  act,
};

