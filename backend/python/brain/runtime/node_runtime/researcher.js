const { normalizeText, buildCapabilityMap, resolveDelegatesByIntent, normalizeStrategyState } = require('./registry');
const { getUserMemory, getRecentUserMessages, buildContextSummary } = require('./memory');

const GREETING_PATTERN = /^(ola|oi|bom dia|boa tarde|boa noite)(\b|[!,?.\s])/;
const SHORT_EXPLANATION_PATTERN = /^(?:o\s*que|oque|oq)(?:\s+e)?\s+(.+)$/;
const EXPLANATION_KEYWORDS = new Set(['btc', 'bitcoin', 'cripto', 'criptomoeda', 'blockchain']);
const STORY_NAMES = ['joao', 'joao', 'maria', 'ana', 'bruno', 'lucas', 'carla'];
const COMPLEX_MARKERS = [
  'depois',
  'analogia',
  'metafora',
  'metafora',
  'explique como se fosse',
  'responda em uma frase',
  'uma unica frase',
  'uma unica frase',
  'exatamente',
  'sem usar a letra',
  'nao pode conter a letra',
  'rima',
  'paragrafos',
  'perspectiva',
  'ponto de vista',
  'mais verde que a liberdade',
  'tempestade de areia em marte',
];

function containsAny(text, values) {
  return values.some(value => text.includes(value));
}

function detectShortConcept(message) {
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
  const shortConcept = detectShortConcept(message);

  if (GREETING_PATTERN.test(msg) && /funcionando|esta funcionando|ta funcionando|tudo bem|pode me ajudar/.test(msg)) {
    return 'pergunta_direta';
  }

  if (GREETING_PATTERN.test(msg)) {
    return 'saudacao';
  }

  if (containsAny(msg, ['qual e meu nome', 'qual e o meu nome', 'voce lembra meu nome', 'com o que eu trabalho'])) {
    return 'memoria';
  }

  if (shortConcept && (EXPLANATION_KEYWORDS.has(shortConcept) || shortConcept.startsWith('btc') || shortConcept.startsWith('bitcoin') || shortConcept.startsWith('cripto') || shortConcept.startsWith('criptomoeda') || shortConcept.startsWith('blockchain'))) {
    return 'explicacao';
  }

  if (containsAny(msg, ['perspectiva', 'perspectivas', 'ponto de vista', 'prisma'])) {
    return 'comparativo';
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

  if (
    containsAny(msg, ['crie', 'monte', 'estruture', 'organize', 'plano', 'roadmap', 'etapas', 'passos']) &&
    !containsAny(msg, ['o que e', 'oque e', 'oq e'])
  ) {
    return 'planejamento';
  }

  if (msg.includes('devo') || msg.includes(' ou ') || msg.includes('qual e melhor') || msg.includes('o que eu faco') || msg.includes('o que fazer') || msg.includes('vale a pena') || msg.includes('melhor opcao')) {
    return 'decision';
  }

  if (msg.includes('quero aprender') || msg.includes('por onde comeco') || msg.includes('programacao') || msg.includes('estudar') || historyText.includes('quero aprender')) {
    return 'aprendizado';
  }

  if (containsAny(msg, ['analogia', 'metafora', 'imagine', 'criativo', 'poetica'])) {
    return 'ideacao';
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

function detectConstraints(message) {
  const msg = normalizeText(message);
  const detected = [];

  if (/\bdepois\b/.test(msg)) {
    detected.push('nested_instructions');
  }
  if (/responda em uma frase|uma unica frase|1 frase/.test(msg)) {
    detected.push('single_sentence');
  }
  if (/exatamente\s+\d+/.test(msg)) {
    detected.push('exact_count');
  }
  if (/sem usar a letra|nao pode conter a letra/.test(msg)) {
    detected.push('forbidden_letter');
  }
  if (/rima|rimar/.test(msg)) {
    detected.push('rhyme');
  }
  if (/paragrafos?/.test(msg)) {
    detected.push('paragraph_count');
  }
  if (/analogia|metafora|explique como se fosse/.test(msg)) {
    detected.push('analogy');
  }
  if (/perspectiva|ponto de vista/.test(msg)) {
    detected.push('perspectives');
  }

  return detected;
}

function detectTaskCategory(message, intent) {
  const msg = normalizeText(message);
  const words = countWords(message);
  const hasStoryNames = STORY_NAMES.some(name => msg.includes(name));
  const hiddenBeliefMarkers = containsAny(msg, ['deixou', 'guardou', 'colocou', 'voltou', 'procurar primeiro', 'sem ver', 'sem que']);

  if (words <= 3) {
    return 'short_prompt';
  }
  if (containsAny(msg, ['qual e meu nome', 'qual e o meu nome', 'com o que eu trabalho', 'voce lembra meu nome', 'meu nome e', 'eu trabalho com'])) {
    return 'memory';
  }
  if (hasStoryNames && hiddenBeliefMarkers) {
    return 'theory_of_mind';
  }
  if (containsAny(msg, ['contraditorio', 'paradoxo'])) {
    return 'logic';
  }
  if (containsAny(msg, ['analogia', 'metafora', 'explique como se fosse'])) {
    return 'analogy';
  }
  if (containsAny(msg, ['perspectiva', 'perspectivas', 'ponto de vista', 'economista', 'ecologista', 'ambientalista', 'agricultor'])) {
    return 'multi_perspective';
  }
  if (containsAny(msg, ['mais verde que a liberdade', 'tempestade de areia em marte', 'imagine', 'criativo', 'poetica'])) {
    return 'creativity';
  }
  if (detectConstraints(message).length > 0) {
    return 'constrained_format';
  }
  if (intent === 'planejamento' || containsAny(msg, ['etapas', 'plano', 'roadmap', 'passos'])) {
    return 'structured_planning';
  }
  return 'explanation';
}

function detectComplexity(message, intent, taskCategory, strategyState) {
  const normalizedMessage = normalizeText(message);
  const words = countWords(message);
  const normalizedState = normalizeStrategyState(strategyState);
  const threshold = Number(normalizedState.params.complex_prompt_word_threshold || 20);
  const signals = [];
  const constraintsDetected = detectConstraints(message);

  if (words > threshold) {
    signals.push('long_prompt');
  }
  if (constraintsDetected.length > 0) {
    signals.push(...constraintsDetected);
  }
  if (containsAny(normalizedMessage, COMPLEX_MARKERS)) {
    signals.push('explicit_complex_marker');
  }
  if (containsAny(normalizedMessage, ['por que', 'porque'])) {
    signals.push('causal_reasoning');
  }
  if (containsAny(normalizedMessage, ['analise sob a perspectiva de', 'perspectiva', 'ponto de vista'])) {
    signals.push('multi_perspective');
  }
  if (containsAny(normalizedMessage, ['analogia', 'metafora', 'explique como se fosse'])) {
    signals.push('analogy');
  }
  if (taskCategory === 'theory_of_mind') {
    signals.push('theory_of_mind');
  }
  if (['comparativo', 'planejamento', 'ideacao', 'decision'].includes(intent)) {
    signals.push('deliberative_intent');
  }

  const highComplexity = ['theory_of_mind', 'logic', 'analogy', 'creativity', 'constrained_format', 'multi_perspective', 'structured_planning'].includes(taskCategory)
    || constraintsDetected.length > 0
    || words > threshold
    || signals.length >= 2;

  return {
    wordCount: words,
    signals: Array.from(new Set(signals)),
    constraintsDetected,
    isComplex: highComplexity,
    highComplexity,
    requiresStrictFormat: constraintsDetected.length > 0,
    requiresLlm: highComplexity,
  };
}

function think({ message, memoryContext, history, summary, capabilities, session }) {
  const userMemory = getUserMemory(memoryContext);
  const recentHistory = getRecentUserMessages(history);
  const capabilityMap = buildCapabilityMap(capabilities);
  const intent = detectIntent(message, recentHistory);
  const strategyState = normalizeStrategyState(session && typeof session === 'object' ? session.strategy_state : {});
  const taskCategory = detectTaskCategory(message, intent);
  const promptComplexity = detectComplexity(message, intent, taskCategory, strategyState);

  return {
    intent,
    taskCategory,
    task_category: taskCategory,
    promptComplexity,
    highComplexity: promptComplexity.highComplexity,
    high_complexity: promptComplexity.highComplexity,
    requiresLlm: promptComplexity.requiresLlm,
    requires_llm: promptComplexity.requiresLlm,
    constraintsDetected: promptComplexity.constraintsDetected,
    constraints_detected: promptComplexity.constraintsDetected,
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
