const { normalizeText } = require('./registry');
const { hasPreference } = require('./memory');

function act(thought, decision, planResult) {
  const msg = normalizeText(thought.message);
  const likesTech =
    hasPreference(thought.preferences, 'tecnologia') ||
    hasPreference(thought.preferences, 'programacao');

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
    return {
      explanation: [
        'Definir com clareza o conceito central.',
        'Mostrar por que isso importa na pratica.',
        'Traduzir a ideia em exemplo simples e acionavel.',
      ],
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
