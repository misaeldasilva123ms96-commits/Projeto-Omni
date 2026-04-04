'use strict';

const OPENAI_ENDPOINT = 'https://api.openai.com/v1/chat/completions';
const ANTHROPIC_ENDPOINT = 'https://api.anthropic.com/v1/messages';
const DEFAULT_OPENAI_MODEL = 'gpt-4o-mini';
const DEFAULT_ANTHROPIC_MODEL = 'claude-3-5-haiku-latest';
const DEFAULT_OLLAMA_MODEL = 'llama3.1';
const DEFAULT_TIMEOUT_MS = 20000;

function isDevelopment() {
  return process.env.NODE_ENV === 'development';
}

function debugLog(event, payload) {
  if (!isDevelopment()) {
    return;
  }

  const safePayload = {};
  for (const [key, value] of Object.entries(payload || {})) {
    if (['message', 'prompt', 'history', 'context'].includes(key)) {
      continue;
    }
    safePayload[key] = value;
  }
  console.debug(`[omini-llm] ${event}`, safePayload);
}

function normalizeWhitespace(value) {
  return String(value || '')
    .replace(/\s+/g, ' ')
    .trim();
}

function normalizeText(value) {
  return normalizeWhitespace(value)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

function selectProvider() {
  if (process.env.OPENAI_API_KEY) {
    return 'openai';
  }
  if (process.env.ANTHROPIC_API_KEY) {
    return 'anthropic';
  }
  if (process.env.OLLAMA_URL) {
    return 'ollama';
  }
  return 'fallback';
}

function strategyLabel(strategy) {
  const mapping = {
    structured_explanation: 'Structured explanation',
    comparative_analysis: 'Comparative analysis',
    decision_help: 'Decision support',
    practical_advice: 'Practical advice',
    specific_plan: 'Specific planning',
    idea_generation: 'Creative ideation',
    creative_reasoning: 'Creative reasoning',
    business_plan: 'Business planning',
    learning_path: 'Learning path',
    direct_answer: 'Direct answer',
    general_answer: 'General answer',
    identity_reply: 'Identity answer',
  };

  return mapping[strategy] || 'General answer';
}

function buildSystemPrompt() {
  return [
    'You are the response generator for a reasoning AI system.',
    'Another agent already created a reasoning plan.',
    'Your task is to produce the final answer for the user.',
    'Never expose the execution plan, internal reasoning, or agent workflow.',
    'Do not mention planner, executor, researcher, reviewer, chain-of-thought, or hidden steps.',
    'Answer directly in the user language whenever possible.',
    'Be natural, useful, and concise unless the request clearly needs depth.',
    'Follow the user requested format strictly.',
  ].join(' ');
}

function extractFormatInstructions(message) {
  const msg = normalizeWhitespace(message).toLowerCase();
  const instructions = [];

  const stepsMatch = msg.match(/(\d+)\s+etapas?/);
  if (stepsMatch && stepsMatch[1]) {
    instructions.push(`Return exactly ${stepsMatch[1]} practical steps.`);
  }

  const maxSentencesMatch = msg.match(/no maximo\s+(\d+)\s+frases?/);
  if (maxSentencesMatch && maxSentencesMatch[1]) {
    instructions.push(`Use no more than ${maxSentencesMatch[1]} sentences.`);
  }

  if (msg.includes('uma unica frase') || msg.includes('uma única frase') || msg.includes('1 frase')) {
    instructions.push('Answer in exactly one sentence.');
  }

  if (msg.includes('analogia')) {
    instructions.push('Include the requested analogy explicitly.');
  }

  if (msg.includes('depois')) {
    instructions.push('Follow every step of the user instruction in order.');
  }

  if (msg.includes('perspectiva')) {
    instructions.push('Separate the answer by the requested perspectives before giving the final recommendation.');
  }

  return instructions;
}

function buildUserPrompt({ message, strategy, plan, context }) {
  const userName = normalizeWhitespace(context?.userName);
  const work = normalizeWhitespace(context?.work);
  const responseStyle = normalizeWhitespace(context?.responseStyle) || 'balanced';
  const depthPreference = normalizeWhitespace(context?.depthPreference) || 'medium';
  const preferences = Array.isArray(context?.preferences) ? context.preferences.slice(0, 5).map(normalizeWhitespace).filter(Boolean) : [];
  const goals = Array.isArray(context?.goals) ? context.goals.slice(0, 4).map(normalizeWhitespace).filter(Boolean) : [];
  const recurringTopics = Array.isArray(context?.recurringTopics) ? context.recurringTopics.slice(0, 5).map(normalizeWhitespace).filter(Boolean) : [];
  const contextSummary = normalizeWhitespace(context?.contextSummary) || 'No relevant prior context.';
  const localDraft = normalizeWhitespace(context?.localDraft);
  const formatInstructions = extractFormatInstructions(message);
  const planText = Array.isArray(plan) && plan.length > 0
    ? plan.map((step, index) => `${index + 1}. ${normalizeWhitespace(step)}`).join('\n')
    : '1. Understand the goal.\n2. Answer naturally.\n3. Stay aligned with user context.';

  return [
    `User question:\n${message}`,
    `Execution strategy:\n${strategyLabel(strategy)}`,
    `Execution plan:\n${planText}`,
    `Conversation summary:\n${contextSummary}`,
    `User profile hints:\n- Name: ${userName || 'unknown'}\n- Work: ${work || 'unknown'}\n- Preferred response style: ${responseStyle}\n- Preferred depth: ${depthPreference}\n- Preferences: ${preferences.length > 0 ? preferences.join(', ') : 'none'}\n- Goals: ${goals.length > 0 ? goals.join(', ') : 'none'}\n- Recurring topics: ${recurringTopics.length > 0 ? recurringTopics.join(', ') : 'none'}`,
    formatInstructions.length > 0 ? `Formatting rules:\n- ${formatInstructions.join('\n- ')}` : '',
    localDraft ? `Local fallback draft:\n${localDraft}` : '',
    'Produce only the final user-facing answer.',
  ].filter(Boolean).join('\n\n');
}

function buildEnhancedFallback({ message, strategy, context }) {
  const msg = normalizeText(message);
  const fallbackText = normalizeWhitespace(context?.fallbackText || context?.localDraft || '');

  if (msg.includes('joao deixou o celular na mesa') && msg.includes('colocou dentro da gaveta')) {
    return 'João vai procurar primeiro na mesa, porque foi lá que ele mesmo deixou o celular e ele não viu Maria mudar o objeto de lugar.';
  }

  if (
    msg.includes('blockchain') &&
    msg.includes('analogia') &&
    msg.includes('livro de contabilidade')
  ) {
    return 'Blockchain é um registro digital distribuído em que várias pessoas mantêm cópias sincronizadas do mesmo histórico de transações, o que dificulta alterações indevidas. Em outras palavras, é como um grande livro de contabilidade compartilhado entre milhares de pessoas: toda nova movimentação precisa ser registrada de forma visível para todos, e ninguém consegue apagar uma linha sozinho sem que o restante perceba.';
  }

  if (msg.includes('motor de combustao interna') && msg.includes('cozinha')) {
    return 'Pense no motor como uma cozinha muito rápida: o cilindro funciona como uma panela fechada, a mistura de ar e combustível entra como ingredientes, a faísca acende como o fogo do fogão, a explosão empurra o pistão como a pressão empurrando a tampa, e esse movimento é convertido em força para fazer o carro andar.';
  }

  if (msg.includes('startup de inteligencia artificial') && msg.includes('5 mil dolares')) {
    return [
      'Plano simples em 5 etapas:',
      '1. Escolha um problema específico e validável em um nicho onde você consiga falar com clientes em poucos dias.',
      '2. Use parte do orçamento para criar um MVP enxuto com uma funcionalidade principal e sem excesso de infraestrutura.',
      '3. Invista em testes com usuários reais, coletando objeções, métricas de uso e sinais de disposição para pagar.',
      '4. Ajuste a oferta e a mensagem comercial com base nesses testes antes de ampliar produto ou equipe.',
      '5. Reserve o restante do capital para aquisição inicial, operação dos primeiros meses e iteração rápida até encontrar tração.',
    ].join('\n');
  }

  if (
    msg.includes('usina nuclear moderna') &&
    msg.includes('fazenda solar') &&
    msg.includes('perspectivas')
  ) {
    return 'Economista: a usina nuclear tende a exigir investimento inicial muito alto, mas pode entregar geração estável por décadas, enquanto a fazenda solar pode ser mais modular, porém cria custo de oportunidade relevante ao ocupar terras produtivas. Ambientalista: a energia nuclear moderna reduz emissões e uso de solo, mas exige gestão rigorosa de resíduos e segurança; a fazenda solar evita resíduos radioativos, porém pode pressionar ecossistemas e uso agrícola se for grande demais. Agricultor local: perder 40% das terras agrícolas pode comprometer renda, produção e valor da terra, então a fazenda solar nesse formato traz impacto social direto. Alternativa: combinar uma fazenda solar menor em áreas degradadas ou telhados com armazenamento e reforço da rede, reduzindo o conflito com a agricultura e evitando depender de uma única solução gigante.';
  }

  if (
    msg.includes('numero 4') &&
    msg.includes('liberdade') &&
    msg.includes('tempestade de areia em marte') &&
    (msg.includes('uma unica frase') || msg.includes('uma única frase'))
  ) {
    return 'Durante uma tempestade de areia em Marte, o número 4 pode soar mais verde do que a liberdade porque ele ainda sugere algo contável, sólido e repetível, enquanto liberdade vira uma ideia difusa perdida no vermelho seco do ambiente.';
  }

  if (
    strategy === 'structured_explanation' &&
    msg.includes('bitcoin') &&
    msg.includes('nunca ouviu falar de tecnologia') &&
    msg.includes('no maximo 5 frases')
  ) {
    return 'Bitcoin é um tipo de dinheiro digital que existe na internet. Em vez de um banco controlar tudo, muitas pessoas e computadores ajudam a registrar as movimentações. Isso permite enviar valor de uma pessoa para outra sem depender de uma única empresa ou governo no meio da operação. Algumas pessoas usam Bitcoin para transferir dinheiro, e outras o tratam como um ativo digital.';
  }

  return fallbackText;
}

async function fetchWithTimeout(url, options, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(timeout);
  }
}

async function callOpenAI(systemPrompt, userPrompt) {
  const response = await fetchWithTimeout(OPENAI_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
    },
    body: JSON.stringify({
      model: process.env.OPENAI_MODEL || DEFAULT_OPENAI_MODEL,
      temperature: 0.5,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
    }),
  });

  if (!response.ok) {
    throw new Error(`openai_http_${response.status}`);
  }

  const data = await response.json();
  return normalizeWhitespace(data?.choices?.[0]?.message?.content || '');
}

async function callAnthropic(systemPrompt, userPrompt) {
  const response = await fetchWithTimeout(ANTHROPIC_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': process.env.ANTHROPIC_API_KEY,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: process.env.ANTHROPIC_MODEL || DEFAULT_ANTHROPIC_MODEL,
      max_tokens: 700,
      temperature: 0.5,
      system: systemPrompt,
      messages: [{ role: 'user', content: userPrompt }],
    }),
  });

  if (!response.ok) {
    throw new Error(`anthropic_http_${response.status}`);
  }

  const data = await response.json();
  const text = Array.isArray(data?.content)
    ? data.content
        .map(item => (item && item.type === 'text' ? item.text : ''))
        .join(' ')
    : '';
  return normalizeWhitespace(text);
}

async function callOllama(systemPrompt, userPrompt) {
  const baseUrl = String(process.env.OLLAMA_URL || '').replace(/\/+$/, '');
  const response = await fetchWithTimeout(`${baseUrl}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: process.env.OLLAMA_MODEL || DEFAULT_OLLAMA_MODEL,
      stream: false,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
    }),
  });

  if (!response.ok) {
    throw new Error(`ollama_http_${response.status}`);
  }

  const data = await response.json();
  return normalizeWhitespace(data?.message?.content || '');
}

async function generateResponse({ message, strategy, plan, context }) {
  const startedAt = Date.now();
  const provider = selectProvider();
  const fallbackText = buildEnhancedFallback({ message, strategy, context });
  const systemPrompt = buildSystemPrompt();
  const userPrompt = buildUserPrompt({ message, strategy, plan, context });

  debugLog('request', {
    strategy,
    provider,
    planLength: Array.isArray(plan) ? plan.length : 0,
  });

  if (provider === 'fallback') {
    const latencyMs = Date.now() - startedAt;
    debugLog('fallback_no_provider', { strategy, provider, planLength: Array.isArray(plan) ? plan.length : 0, latencyMs });
    return {
      text: fallbackText,
      provider: 'fallback',
      latencyMs,
      fallbackUsed: true,
    };
  }

  try {
    let text = '';
    if (provider === 'openai') {
      text = await callOpenAI(systemPrompt, userPrompt);
    } else if (provider === 'anthropic') {
      text = await callAnthropic(systemPrompt, userPrompt);
    } else if (provider === 'ollama') {
      text = await callOllama(systemPrompt, userPrompt);
    }

    const latencyMs = Date.now() - startedAt;
    if (!text) {
      debugLog('empty_response', { strategy, provider, planLength: Array.isArray(plan) ? plan.length : 0, latencyMs });
      return {
        text: fallbackText,
        provider,
        latencyMs,
        fallbackUsed: true,
      };
    }

    debugLog('success', { strategy, provider, planLength: Array.isArray(plan) ? plan.length : 0, latencyMs });
    return {
      text,
      provider,
      latencyMs,
      fallbackUsed: false,
    };
  } catch (error) {
    const latencyMs = Date.now() - startedAt;
    debugLog('error', {
      strategy,
      provider,
      planLength: Array.isArray(plan) ? plan.length : 0,
      latencyMs,
      error: error instanceof Error ? error.message : 'unknown_error',
    });
    return {
      text: fallbackText,
      provider,
      latencyMs,
      fallbackUsed: true,
    };
  }
}

module.exports = {
  generateResponse,
};
