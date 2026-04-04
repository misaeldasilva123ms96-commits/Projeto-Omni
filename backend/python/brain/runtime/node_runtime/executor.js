const { normalizeText } = require('./registry');
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
    /^oque e\s+(.+)$/,
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

  return normalized.replace(/[?!.]+$/g, '').trim();
}

function buildExplanation(topic, depthPreference) {
  const deep = depthPreference === 'deep';

  if (topic.includes('machine learning')) {
    const parts = [
      'Machine learning é uma forma de treinar sistemas para reconhecer padrões em dados e melhorar previsões com a experiência.',
      'Na prática, o modelo recebe exemplos, ajusta parâmetros internos e aprende a responder melhor para casos parecidos no futuro.',
      'Isso é usado em recomendação, detecção de fraude, visão computacional e assistentes inteligentes.',
    ];
    if (deep) {
      parts.push('Os principais estilos incluem aprendizado supervisionado, não supervisionado e por reforço, cada um adequado para problemas diferentes.');
    }
    return parts;
  }

  if (topic.includes('blockchain')) {
    return [
      'Blockchain é um registro digital distribuído que organiza informações em blocos conectados em sequência.',
      'Ela funciona mantendo cópias sincronizadas do mesmo histórico em vários participantes da rede, o que dificulta alterações indevidas.',
      deep
        ? 'Por isso ela é útil quando várias partes precisam confiar no mesmo registro sem depender de um único servidor central.'
        : 'Na prática, isso permite rastrear transações com transparência, como acontece no funcionamento das criptomoedas.',
    ];
  }

  if (topic.includes('bitcoin')) {
    return [
      'Bitcoin é uma criptomoeda criada para permitir transferências de valor pela internet sem depender de uma autoridade central.',
      'Ele funciona em uma rede descentralizada, onde as transações são validadas e registradas em blockchain.',
      'Na prática, ele pode ser usado para transferir valor digitalmente e também como referência no mercado de criptoativos.',
    ];
  }

  const title = capitalize(topic || 'esse tema');
  const parts = [
    `${title} é um conceito que vale entender pelo que ele é, por como funciona e por onde ele é aplicado.`,
    'O ponto principal é identificar sua função central e por que isso importa na prática.',
    'Se você quiser, eu também posso aprofundar com exemplos, vantagens, riscos ou comparação com alternativas.',
  ];
  if (!deep) {
    return parts.slice(0, 3);
  }
  parts.push('Se fizer sentido, eu posso transformar isso em um resumo técnico, um guia prático ou uma comparação com outra tecnologia.');
  return parts;
}

function buildComparativeAnalysis(message) {
  const msg = normalizeText(message);

  if (msg.includes('python') && msg.includes('rust')) {
    return {
      intro: 'Python e Rust podem funcionar muito bem em produção para sistemas de IA, mas brilham em pontos diferentes.',
      pros: [
        'Python acelera pesquisa, prototipagem e integração com bibliotecas de dados e machine learning.',
        'Rust oferece desempenho previsível, baixo consumo de memória e mais segurança para componentes críticos.',
      ],
      cons: [
        'Python tende a sofrer mais com concorrência pesada e gargalos de performance em partes sensíveis.',
        'Rust exige mais tempo de desenvolvimento e uma curva maior para equipes que ainda não dominam ownership e lifetimes.',
      ],
      recommendation: 'Se o foco é iterar rápido no cérebro e nos experimentos, Python costuma ser a melhor base. Se o foco é runtime crítico, throughput e confiabilidade de baixo nível, vale usar Rust em partes estratégicas ou numa arquitetura híbrida.',
    };
  }

  return {
    intro: 'A melhor comparação começa pelos critérios que realmente importam para o seu caso de uso.',
    pros: [
      'Uma opção pode entregar mais velocidade de desenvolvimento ou ecossistema.',
      'A outra pode ganhar em desempenho, previsibilidade ou custo operacional.',
    ],
    cons: [
      'Toda escolha técnica cria trade-offs em curva de aprendizado, manutenção e flexibilidade futura.',
      'Sem definir critérios claros, a comparação tende a virar preferência em vez de decisão técnica.',
    ],
    recommendation: 'Escolha pelos requisitos de performance, equipe, prazo e risco operacional. Se quiser, eu posso comparar duas tecnologias específicas com mais profundidade.',
  };
}

function buildSpecificPlan(message, thought) {
  const msg = normalizeText(message);

  if (msg.includes('delivery')) {
    return {
      title: 'Plano inicial para um app de delivery',
      steps: [
        'Escolha um nicho com dor clara, como entregas de restaurantes locais ou mercados de bairro, e valide onde o tempo de entrega e a previsibilidade são o maior problema.',
        'Monte uma operação enxuta com painel simples para lojistas, aplicativo para pedidos e um fluxo de despacho bem definido antes de expandir funcionalidades.',
        'Teste a aquisição em uma região pequena, acompanhe taxa de recompra, tempo médio de entrega e margem por pedido para ajustar o modelo.',
      ],
      closing: thought.goals.length > 0
        ? `Como você já busca ${thought.goals[0]}, eu começaria validando esse objetivo com uma operação pequena e métricas claras.`
        : 'O ponto mais importante no começo não é escalar a tecnologia, e sim provar recorrência, logística viável e unidade econômica saudável.',
    };
  }

  return {
    title: 'Plano prático de execução',
    steps: [
      'Defina o problema, o público e a proposta de valor de forma específica.',
      'Crie uma versão inicial com o mínimo necessário para validar uso real.',
      'Acompanhe métricas simples de adoção, retenção e receita antes de ampliar o escopo.',
    ],
    closing: 'Com essa base validada, fica muito mais seguro decidir o próximo investimento.',
  };
}

function buildIdeas(thought) {
  const likesTech = hasPreference(thought.preferences, 'tecnologia') || hasPreference(thought.preferences, 'ia');
  const worksWithAi = normalizeText(thought.work || '').includes('ia');

  if (likesTech || worksWithAi) {
    return [
      'Um copiloto de atendimento para pequenos negócios que transforma WhatsApp em funil de vendas com respostas, qualificação e agendamento.',
      'Uma plataforma de auditoria de processos com IA para empresas de serviço, capaz de detectar gargalos operacionais e sugerir melhorias semanais.',
      'Um agente de prospecção para nichos locais que encontra leads, monta abordagem personalizada e mede conversão por campanha.',
    ];
  }

  return [
    'Um serviço de automação com IA para tarefas repetitivas de pequenas empresas, cobrado por assinatura simples.',
    'Uma ferramenta que resume reuniões, extrai decisões e cria próximos passos automáticos para equipes enxutas.',
    'Uma solução de análise de mensagens de clientes para identificar dúvidas recorrentes e melhorar vendas e suporte.',
  ];
}

function buildBusinessPayload(message, thought) {
  const msg = normalizeText(message);
  if (msg.includes('ideia de negocio') || msg.includes('ideia de negócio')) {
    return buildIdeas(thought);
  }

  return [
    'Escolha um problema frequente e caro para um público específico.',
    'Crie uma oferta simples, com implementação rápida e benefício fácil de explicar.',
    'Valide com clientes reais antes de ampliar equipe, produto ou canais.',
  ];
}

function fallbackTextForStrategy(thought, decision) {
  const msg = normalizeText(thought.message);
  const topic = extractExplanationTopic(thought.message);

  switch (decision.strategy) {
    case 'greeting_reply':
      return 'Olá! Como posso te ajudar hoje?';
    case 'direct_answer':
      return msg.includes('funcionando')
        ? 'Olá! Sim, estou funcionando e pronto para te ajudar com explicações, planejamento, análise e ideias práticas.'
        : 'Sim, estou pronto para te ajudar. Pode me dizer qual objetivo ou dúvida você quer resolver agora?';
    case 'comparative_analysis': {
      const comparison = buildComparativeAnalysis(thought.message);
      return `${comparison.intro} Prós: ${comparison.pros.join(' ')} Contras: ${comparison.cons.join(' ')} ${comparison.recommendation}`;
    }
    case 'specific_plan': {
      const plan = buildSpecificPlan(thought.message, thought);
      return `${plan.title}:\n1. ${plan.steps[0]}\n2. ${plan.steps[1]}\n3. ${plan.steps[2]}\n${plan.closing}`;
    }
    case 'idea_generation': {
      const ideas = buildIdeas(thought);
      return `Aqui vão 3 ideias fortes:\n1. ${ideas[0]}\n2. ${ideas[1]}\n3. ${ideas[2]}`;
    }
    case 'business_plan': {
      const payload = buildBusinessPayload(thought.message, thought);
      return `Eu seguiria um caminho realista:\n1. ${payload[0]}\n2. ${payload[1]}\n3. ${payload[2]}`;
    }
    case 'learning_path':
      return [
        'O melhor caminho agora é este:',
        '1. Comece pelos fundamentos antes de buscar velocidade.',
        '2. Pratique no mesmo dia com exercícios curtos e feedback rápido.',
        '3. Transforme o estudo em um projeto pequeno e concluído para consolidar o aprendizado.',
      ].join('\n');
    case 'decision_help':
    case 'practical_advice':
      return 'A melhor escolha depende do seu estado atual, do custo de energia e do impacto imediato de cada opção. Em geral, vale priorizar a opção que cria progresso real sem gerar desgaste desnecessário ou atrasar o próximo passo importante. Compare as opções pelo ganho prático no curto prazo e pela energia que você ainda tem disponível agora.';
    case 'structured_explanation':
      return buildExplanation(topic, thought.depthPreference).join(' ');
    case 'identity_reply':
      return thought.userName
        ? 'Sou uma IA orientada a contexto, memória, decisão prática e aprendizado progressivo. Também levo em conta o que você já me contou.'
        : 'Sou uma IA orientada a contexto, memória, decisão prática e aprendizado progressivo. Meu trabalho é entender o que você quer e devolver algo útil.';
    case 'general_answer':
    case 'contextual_conversation':
    default:
      return thought.recentHistory.length > 0
        ? 'Entendi o contexto recente e posso continuar a conversa com foco no próximo passo útil.'
        : 'Posso te ajudar com explicações, planos, comparações e ideias práticas.';
  }
}

function mapStrategyForAdapter(strategy) {
  if (!strategy || strategy === 'contextual_conversation') {
    return 'general_answer';
  }
  return strategy;
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
  ].includes(strategy);
}

async function act(thought, decision, planResult) {
  const executionPlan = Array.isArray(planResult?.executionPlan) ? planResult.executionPlan : [];
  const fallbackText = fallbackTextForStrategy(thought, decision);

  if (!shouldUseLlm(decision.strategy)) {
    return {
      response: fallbackText,
      confidence: decision.confidence || 0.82,
      memory: {},
      provider: 'local',
      latencyMs: 0,
      fallbackUsed: true,
      executionPlan,
    };
  }

  const generated = await generateResponse({
    message: thought.message,
    strategy: mapStrategyForAdapter(decision.strategy),
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
      fallbackText,
      localDraft: fallbackText,
    },
  });

  return {
    response: generated.text || fallbackText,
    confidence: decision.confidence || 0.82,
    memory: {},
    provider: generated.provider || 'fallback',
    latencyMs: typeof generated.latencyMs === 'number' ? generated.latencyMs : 0,
    fallbackUsed: Boolean(generated.fallbackUsed) || !generated.text,
    executionPlan,
  };
}

module.exports = {
  act,
};
