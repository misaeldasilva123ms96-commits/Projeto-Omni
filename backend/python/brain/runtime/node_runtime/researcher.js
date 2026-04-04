const { normalizeText, buildCapabilityMap, resolveDelegatesByIntent } = require('./registry');
const { getUserMemory, getRecentUserMessages, buildContextSummary } = require('./memory');

const GREETING_PATTERN = /^(ola|oi|bom dia|boa tarde|boa noite)(\b|[!,?.\s])/;

function detectIntent(message, recentHistory) {
  const msg = normalizeText(message);
  const historyText = normalizeText(recentHistory.join(' '));

  if (GREETING_PATTERN.test(msg) && /funcionando|esta funcionando|ta funcionando|tudo bem|pode me ajudar/.test(msg)) {
    return 'pergunta_direta';
  }

  if (GREETING_PATTERN.test(msg)) {
    return 'saudacao';
  }

  if (
    msg.includes('pros e contras') ||
    msg.includes('vantagens e desvantagens') ||
    msg.includes('compare') ||
    msg.includes('comparar') ||
    msg.includes(' vs ') ||
    msg.includes(' versus ') ||
    msg.includes('analise ') ||
    msg.includes('analisa ')
  ) {
    return 'comparativo';
  }

  if (
    msg.includes('plano de negocios') ||
    msg.includes('plano de negocio') ||
    msg.includes('modelo de negocio') ||
    msg.includes('crie um plano') ||
    msg.includes('monte um plano') ||
    msg.includes('estrategia para')
  ) {
    return 'planejamento';
  }

  if (
    msg.includes('ideias de startup') ||
    msg.includes('ideias inovadoras') ||
    msg.includes('ideia de startup') ||
    msg.includes('me de 3 ideias') ||
    msg.includes('gere ideias')
  ) {
    return 'ideacao';
  }

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

  if (msg.includes('como melhorar') || msg.includes('conselho') || msg.includes('dica')) {
    return 'conselho';
  }

  if (
    msg.includes('o que e') ||
    msg.includes('oque e') ||
    msg.includes('explique') ||
    msg.includes('por que') ||
    msg.includes('porque') ||
    msg.includes('como funciona') ||
    msg.includes('me diga o que e')
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

  if (msg.includes('?') || msg.includes('voce esta funcionando')) {
    return 'pergunta_direta';
  }

  return 'conversa';
}

function think({ message, memoryContext, history, summary, capabilities, session }) {
  const userMemory = getUserMemory(memoryContext);
  const recentHistory = getRecentUserMessages(history);
  const capabilityMap = buildCapabilityMap(capabilities);
  const intent = detectIntent(message, recentHistory);

  return {
    intent,
    userId: userMemory.id,
    userName: userMemory.nome,
    work: userMemory.trabalho,
    preferences: userMemory.preferencias,
    responseStyle: userMemory.responseStyle,
    depthPreference: userMemory.depthPreference,
    recurringTopics: userMemory.recurringTopics,
    goals: userMemory.goals,
    contextSummary: buildContextSummary(history, summary, session),
    message,
    recentHistory,
    capabilityMap,
    availableCapabilities: Object.keys(capabilityMap),
    session: session && typeof session === 'object' ? session : {},
    delegates: resolveDelegatesByIntent(intent),
  };
}

module.exports = {
  think,
  detectIntent,
};
