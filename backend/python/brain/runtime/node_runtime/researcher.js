const { normalizeText, buildCapabilityMap, resolveDelegatesByIntent } = require('./registry');
const { getUserMemory, getRecentUserMessages, buildContextSummary } = require('./memory');

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

function think({ message, memoryContext, history, summary, capabilities, session }) {
  const userMemory = getUserMemory(memoryContext);
  const recentHistory = getRecentUserMessages(history);
  const capabilityMap = buildCapabilityMap(capabilities);
  const intent = detectIntent(message, recentHistory);

  return {
    intent,
    userName: userMemory.nome,
    preferences: userMemory.preferencias,
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
