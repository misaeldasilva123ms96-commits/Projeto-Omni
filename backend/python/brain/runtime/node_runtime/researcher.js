const { normalizeText, buildCapabilityMap, resolveDelegatesByIntent, normalizeStrategyState } = require('./registry');
const { getUserMemory, getRecentUserMessages, buildContextSummary } = require('./memory');

const GREETING_PATTERN = /^(ola|oi|bom dia|boa tarde|boa noite)(\b|[!,?.\s])/;
const SHORT_EXPLANATION_PATTERN = /^(?:o\s*que|oque|oq)(?:\s+e)?\s+(.+)$/;
const EXPLANATION_KEYWORDS = new Set(['btc', 'bitcoin', 'cripto', 'criptomoeda']);

function extractShortConcept(message) {
  const msg = normalizeText(message);
  const compact = msg.replace(/[?!.]+$/g, '').trim();

  if (EXPLANATION_KEYWORDS.has(compact)) {
    return compact;
  }

  const shortMatch = compact.match(SHORT_EXPLANATION_PATTERN);
  if (shortMatch && shortMatch[1]) {
    return shortMatch[1].trim();
  }

  return '';
}

function detectIntent(message, recentHistory) {
  const msg = normalizeText(message);
  const historyText = normalizeText(recentHistory.join(' '));
  const shortConcept = extractShortConcept(message);

  if (GREETING_PATTERN.test(msg) && /funcionando|esta funcionando|ta funcionando|tudo bem|pode me ajudar/.test(msg)) {
    return 'pergunta_direta';
  }

  if (GREETING_PATTERN.test(msg)) {
    return 'saudacao';
  }

  if (shortConcept && (EXPLANATION_KEYWORDS.has(shortConcept) || shortConcept.startsWith('btc') || shortConcept.startsWith('bitcoin') || shortConcept.startsWith('cripto') || shortConcept.startsWith('criptomoeda'))) {
    return 'explicacao';
  }

  if (msg.includes('pros e contras') || msg.includes('vantagens e desvantagens') || msg.includes('compare') || msg.includes('comparar') || msg.includes(' vs ') || msg.includes(' versus ') || msg.includes('analise ') || msg.includes('analisa ')) {
    return 'comparativo';
  }

  if (msg.includes('plano de negocios') || msg.includes('plano de negocio') || msg.includes('modelo de negocio') || msg.includes('crie um plano') || msg.includes('monte um plano') || msg.includes('estrategia para')) {
    return 'planejamento';
  }

  if (msg.includes('ideias de startup') || msg.includes('ideias inovadoras') || msg.includes('ideia de startup') || msg.includes('me de 3 ideias') || msg.includes('gere ideias')) {
    return 'ideacao';
  }

  if (msg.includes('devo') || msg.includes(' ou ') || msg.includes('qual e melhor') || msg.includes('o que eu faco') || msg.includes('o que fazer') || msg.includes('vale a pena') || msg.includes('melhor opcao')) {
    return 'decision';
  }

  if (msg.includes('ganhar dinheiro') || msg.includes('negocio') || msg.includes('dinheiro') || msg.includes('renda') || msg.includes('vender online')) {
    return 'dinheiro';
  }

  if (msg.includes('quero aprender') || msg.includes('por onde comeco') || msg.includes('programacao') || msg.includes('estudar') || historyText.includes('quero aprender')) {
    return 'aprendizado';
  }

  if (msg.includes('como melhorar') || msg.includes('conselho') || msg.includes('dica')) {
    return 'conselho';
  }

  if (msg.includes('o que e') || msg.includes('oque e') || msg.includes('o que ') || msg.includes('oque ') || msg.includes('oq e') || msg.includes('oq ') || msg.includes('explique') || msg.includes('por que') || msg.includes('porque') || msg.includes('como funciona') || msg.includes('me diga o que e')) {
    return 'explicacao';
  }

  if (msg.includes('quem e voce') || msg.includes('como voce responde') || msg.includes('como voce funciona')) {
    return 'pessoal';
  }

  if (msg.includes('?') || msg.includes('voce esta funcionando')) {
    return 'pergunta_direta';
  }

  return 'conversa';
}

function countWords(message) {
  return normalizeText(message).split(/\s+/).filter(Boolean).length;
}

function detectTaskCategory(message, intent) {
  const msg = normalizeText(message);
  const words = countWords(message);

  if (words <= 3) {
    return 'short_prompt';
  }
  if (msg.includes('qual e meu nome') || msg.includes('qual e o meu nome') || msg.includes('com o que eu trabalho')) {
    return 'memory';
  }
  if (msg.includes('perspectiva')) {
    return 'multi_perspective';
  }
  if (msg.includes('joao') && msg.includes('maria')) {
    return 'logic';
  }
  if (msg.includes('analogia') || msg.includes('imagine') || msg.includes('cozinha') || msg.includes('tempestade de areia em marte')) {
    return 'creativity';
  }
  if (intent === 'planejamento' || msg.includes('etapas') || msg.includes('plano')) {
    return 'planning';
  }
  return 'explanation';
}

function detectComplexity(message, intent, strategyState) {
  const normalizedMessage = normalizeText(message);
  const words = countWords(message);
  const normalizedState = normalizeStrategyState(strategyState);
  const threshold = Number(normalizedState.params.complex_prompt_word_threshold || 20);
  const signals = [];

  if (words > threshold) {
    signals.push('long_prompt');
  }
  if (normalizedMessage.includes('depois')) {
    signals.push('multi_step');
  }
  if (normalizedMessage.includes('analogia')) {
    signals.push('analogy');
  }
  if (normalizedMessage.includes('perspectiva')) {
    signals.push('perspective');
  }
  if (normalizedMessage.includes('imagine')) {
    signals.push('creative_prompt');
  }
  if (normalizedMessage.includes('por que') || normalizedMessage.includes('porque')) {
    signals.push('causal_reasoning');
  }
  if (/\d+\s+etapas?/.test(normalizedMessage) || normalizedMessage.includes('uma unica frase') || normalizedMessage.includes('1 frase')) {
    signals.push('strict_format');
  }
  if (intent === 'comparativo' || intent === 'planejamento' || intent === 'ideacao') {
    signals.push('deliberative_intent');
  }

  return {
    wordCount: words,
    signals,
    isComplex: signals.length > 0,
    requiresStrictFormat: signals.includes('strict_format') || signals.includes('multi_step'),
  };
}

function think({ message, memoryContext, history, summary, capabilities, session }) {
  const userMemory = getUserMemory(memoryContext);
  const recentHistory = getRecentUserMessages(history);
  const capabilityMap = buildCapabilityMap(capabilities);
  const intent = detectIntent(message, recentHistory);
  const strategyState = normalizeStrategyState(session && typeof session === 'object' ? session.strategy_state : {});
  const promptComplexity = detectComplexity(message, intent, strategyState);
  const taskCategory = detectTaskCategory(message, intent);

  return {
    intent,
    taskCategory,
    promptComplexity,
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
    strategyState,
    session: session && typeof session === 'object' ? session : {},
    delegates: resolveDelegatesByIntent(intent),
  };
}

module.exports = {
  think,
  detectIntent,
};
