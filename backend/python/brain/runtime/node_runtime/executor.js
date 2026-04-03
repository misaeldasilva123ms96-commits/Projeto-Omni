const { normalizeText } = require('./registry');
const { hasPreference } = require('./memory');

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

  return normalized;
}

function buildExplanation(topic) {
  if (topic.includes('criptomoeda')) {
    return [
      'Criptomoeda é um tipo de dinheiro digital que funciona pela internet e usa criptografia para registrar e proteger transações.',
      'Ela é importante porque permite transferências diretas entre pessoas ou empresas sem depender de um banco tradicional em cada operação.',
      'Um exemplo comum é o bitcoin, que pode ser enviado entre carteiras digitais e tem suas movimentações registradas em uma rede distribuída.',
    ];
  }

  if (topic.includes('blockchain')) {
    return [
      'Blockchain é um registro digital distribuído que organiza informações em blocos conectados em sequência.',
      'Ela funciona mantendo cópias sincronizadas do mesmo histórico em vários participantes da rede, o que dificulta alterações indevidas.',
      'Na prática, isso permite rastrear transações com transparência, como acontece no funcionamento das criptomoedas.',
    ];
  }

  if (topic.includes('bitcoin')) {
    return [
      'Bitcoin é uma criptomoeda criada para permitir transferências de valor pela internet sem depender de uma autoridade central.',
      'Ele funciona em uma rede descentralizada, onde as transações são validadas e registradas em blockchain.',
      'Na prática, ele pode ser usado para transferir valor digitalmente e também como referência no mercado de criptoativos.',
    ];
  }

  const capitalizedTopic = topic ? `${topic.charAt(0).toUpperCase()}${topic.slice(1)}` : 'Esse tema';
  return [
    `${capitalizedTopic} é um conceito que vale entender pelo que ele é, por como funciona e por onde ele é aplicado.`,
    'O ponto principal é identificar sua função central e por que isso importa na prática.',
    'Se você quiser, eu também posso aprofundar com exemplos, vantagens, riscos ou comparação com alternativas.',
  ];
}

function act(thought, decision, planResult) {
  const msg = normalizeText(thought.message);
  const likesTech =
    hasPreference(thought.preferences, 'tecnologia') ||
    hasPreference(thought.preferences, 'programacao');

  if (thought.intent === 'saudacao') {
    return {
      greeting: 'Olá! Como posso te ajudar hoje?',
      executionPlan: planResult.executionPlan,
    };
  }

  if (decision.strategy === 'business_plan') {
    return {
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
      executionPlan: planResult.executionPlan,
    };
  }

  if (decision.strategy === 'learning_path') {
    return {
      steps: [
        'Comece pelos fundamentos antes de buscar velocidade.',
        'Pratique no mesmo dia com exercicios curtos.',
        'Transforme o estudo em um projeto pequeno e concluido.',
      ],
      executionPlan: planResult.executionPlan,
    };
  }

  if (decision.strategy === 'decision_help' || decision.strategy === 'practical_advice') {
    return {
      analysis: [
        'A melhor escolha depende do seu estado atual e do impacto imediato de cada opcao.',
        'Em geral, vale priorizar a opcao que cria progresso sem gerar desgaste desnecessario.',
      ],
      recommendation: 'Compare as opcoes pelo custo de energia e pelo ganho pratico no curto prazo.',
      executionPlan: planResult.executionPlan,
    };
  }

  if (decision.strategy === 'structured_explanation') {
    const topic = extractExplanationTopic(thought.message);
    return {
      explanation: buildExplanation(topic),
      topic,
      executionPlan: planResult.executionPlan,
    };
  }

  if (decision.strategy === 'identity_reply') {
    return {
      identity: thought.userName
        ? 'Sou uma IA orientada a contexto, memoria, decisao pratica e aprendizado progressivo.'
        : 'Sou uma IA orientada a contexto, memoria, decisao pratica e aprendizado progressivo. Meu trabalho e entender o que voce quer e devolver algo util.',
      executionPlan: planResult.executionPlan,
    };
  }

  return {
    conversation:
      thought.recentHistory.length > 0
        ? 'Vou continuar a partir do contexto recente e focar no proximo passo mais util.'
        : 'Vou responder de forma direta e util com base no que voce perguntou.',
    executionPlan: planResult.executionPlan,
  };
}

module.exports = {
  act,
};
