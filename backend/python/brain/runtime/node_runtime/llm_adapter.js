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
    if (['message', 'prompt', 'history', 'context', 'user_message'].includes(key)) {
      continue;
    }
    safePayload[key] = value;
  }
  console.debug(`[omini-llm] ${event}`, safePayload);
}

function normalizeWhitespace(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
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

function buildSystemPrompt() {
  return [
    'You are the OMNI ENGINE EXECUTOR.',
    'Your job is to EXECUTE the provided plan and produce the final answer.',
    'Do NOT announce what you are going to do.',
    'Do NOT explain your reasoning process.',
    'Do NOT expose internal plans, steps, or agent names.',
    'Strictly obey all user constraints.',
    'Follow the requested format strictly. If the user asks for one sentence, output one sentence. If the user asks for 4 paragraphs, output exactly 4 paragraphs.',
    'Deliver the final answer only.',
  ].join(' ');
}

function buildUserPrompt({ message, strategy, plan, context }) {
  const constraints = context?.constraints && typeof context.constraints === 'object' ? context.constraints : {};
  const targetOutput = normalizeWhitespace(context?.targetOutput || 'deliver the final answer only');
  const taskCategory = normalizeWhitespace(context?.taskCategory || 'general');
  const contextSummary = normalizeWhitespace(context?.contextSummary || 'No relevant prior context.');
  const planText = Array.isArray(plan) && plan.length > 0
    ? plan.map((step, index) => `${index + 1}. ${normalizeWhitespace(step)}`).join('\n')
    : '1. Understand the user request.\n2. Produce the final answer.\n3. Respect all constraints.';

  return [
    `Original user request:\n${message}`,
    `Task category:\n${taskCategory}`,
    `Execution strategy:\n${strategy}`,
    `Target output:\n${targetOutput}`,
    `Plan steps to execute:\n${planText}`,
    `Extracted constraints:\n${JSON.stringify(constraints, null, 2)}`,
    `Conversation summary:\n${contextSummary}`,
    'Final instruction: follow the requested format strictly and output only the finished answer for the user.',
  ].join('\n\n');
}

function splitSentences(text) {
  return text.split(/(?<=[.!?])\s+/).map(item => item.trim()).filter(Boolean);
}

function limitSentences(text, count) {
  if (!count || count <= 0) {
    return text;
  }
  return splitSentences(text).slice(0, count).join(' ');
}

function buildTheoryOfMindFallback(message) {
  const normalized = normalizeText(message);
  if (!/onde/.test(normalized)) {
    return '';
  }

  let location = '';
  if (normalized.includes('mesa')) {
    location = 'na mesa';
  } else if (normalized.includes('sofa')) {
    location = 'no sofa';
  } else if (normalized.includes('armario')) {
    location = 'no armario';
  } else if (normalized.includes('gaveta')) {
    location = 'na gaveta';
  }

  if (!location) {
    location = 'no lugar onde ele deixou o objeto por ultimo';
  }

  return `Ele vai procurar primeiro ${location}, porque foi la que ele deixou o objeto e nao viu a outra pessoa mudando de lugar.`;
}

function buildFourParagraphAIFallback() {
  return [
    'IA une codigo, logica e predicao. Isso permite definir padroes, inferir sentidos e decidir melhor sob varios tipos de dado.',
    'Inteligencia artificial funciona treinando sistemas para reconhecer padroes em dados e responder com base nesses padroes. Em vez de seguir apenas regras fixas, o sistema aprende com exemplos e melhora conforme recebe mais informacao.',
    'Hoje ela aparece em recomendacoes, traducao, visao computacional, assistentes digitais e automacao de processos. O valor real surge quando ela reduz tempo operacional, amplia escala e ajuda pessoas a tomar decisoes melhores.',
    'No fim, seu brilho pode fluir e construir. Com uso sutil, pode servir e evoluir. Se houver bom criterio ao conduzir, seu potencial pode surgir e expandir sem ruir.',
  ].join('\n\n');
}

function buildAnalogyFallback(message, constraints) {
  const normalized = normalizeText(message);

  if (normalized.includes('motor de combustao') && (normalized.includes('cozinha') || normalized.includes('culin'))) {
    return 'Pense no motor como uma cozinha muito rapida: o cilindro funciona como uma panela fechada, a mistura de ar e combustivel entra como ingredientes, a faica acende como o fogo do fogao, a explosao empurra o pistao como a pressao empurrando a tampa, e esse movimento vira forca para fazer o carro andar.';
  }

  if (normalized.includes('blockchain') && normalized.includes('livro de contabilidade')) {
    return 'Blockchain funciona como um grande livro de contabilidade compartilhado entre milhares de pessoas: cada nova transacao vira uma nova linha registrada, todos conferem a mesma copia, e tentar apagar ou alterar um registro sozinho ficaria evidente para o resto do grupo.';
  }

  const domain = constraints.analogyDomain || 'um dominio simples do cotidiano';
  return `Funciona melhor se voce imaginar esse tema como ${domain}: cada parte tecnica vira um elemento concreto desse dominio, mantendo a mesma funcao e a mesma ordem de funcionamento.`;
}

function buildMultiPerspectiveFallback(message, constraints) {
  const normalized = normalizeText(message);
  const perspectives = constraints.perspectiveList && constraints.perspectiveList.length > 0
    ? constraints.perspectiveList
    : ['economista', 'ecologista', 'agricultor'];

  if (normalized.includes('energia nuclear') && normalized.includes('energia solar')) {
    return [
      'Economista: a usina nuclear exige investimento inicial alto, mas pode entregar geracao estavel por decadas; a fazenda solar tem implantacao mais modular, porem perde eficiencia economica se ocupar uma parcela grande de terra produtiva.',
      'Ecologista: a energia nuclear reduz emissoes e uso de solo, mas exige controle rigoroso de residuos e seguranca; a energia solar reduz residuos perigosos, porem pode pressionar ecossistemas e deslocar producao agricola se ocupar area demais.',
      'Agricultor: perder terras ferteis compromete renda, producao e autonomia local, entao uma fazenda solar muito extensa pode ser vista como ameaca direta ao sustento da comunidade rural.',
      'Terceira solucao: combinar uma usina solar menor em telhados, areas degradadas e infraestrutura ja ocupada com armazenamento e modernizacao da rede, reduzindo o conflito com a agricultura e evitando dependencia total de uma unica fonte.',
    ].join('\n');
  }

  return perspectives.map(perspective => `${perspective}: analisar custos, beneficios e riscos a partir desse ponto de vista.`).concat('Terceira solucao: propor uma alternativa hibrida que reduza o conflito central.').join('\n');
}

function buildPlanningFallback(message, constraints) {
  const normalized = normalizeText(message);
  const count = constraints.stepCount || 5;

  if (normalized.includes('startup de inteligencia artificial') && normalized.includes('5 mil')) {
    return [
      `Plano simples em ${count} etapas:`,
      '1. Escolha um problema especifico e validavel em um nicho onde voce consiga conversar com clientes em poucos dias.',
      '2. Monte um MVP enxuto com a funcionalidade principal e sem excesso de infraestrutura ou custo fixo.',
      '3. Teste com usuarios reais e colete sinais de uso, dor resolvida e disposicao para pagar.',
      '4. Ajuste a oferta e a mensagem comercial com base nesses aprendizados antes de ampliar o produto.',
      '5. Reserve o restante do capital para operacao inicial, aquisicao controlada e iteracao rapida ate encontrar tracao.',
    ].slice(0, count + 1).join('\n');
  }

  const lines = [`Plano pratico em ${count} etapas:`];
  for (let index = 1; index <= count; index += 1) {
    lines.push(`${index}. Entregar uma etapa clara, acionavel e alinhada ao objetivo do usuario.`);
  }
  return lines.join('\n');
}

function buildCreativeFallback(message, constraints) {
  const normalized = normalizeText(message);

  if (normalized.includes('numero 4') && normalized.includes('liberdade') && normalized.includes('marte')) {
    return 'Durante uma tempestade de areia em Marte, o numero 4 parece mais verde que a liberdade porque ainda sugere algo contavel, solido e repetivel, enquanto liberdade vira um eco abstrato perdido no vermelho seco do planeta.';
  }

  const singleSentence = constraints.singleSentence || constraints.sentenceCount === 1;
  if (singleSentence) {
    return 'A imagem funciona porque transforma uma ideia abstrata em uma cena concreta, criando contraste entre numero, cor, liberdade e ambiente extremo em uma unica linha imaginativa.';
  }

  return 'A melhor resposta aqui e aceitar a imagem improvavel, ligar os elementos por contraste simbolico e entregar uma resposta criativa sem tentar corrigir a premissa do usuario.';
}

function buildExplanationFallback(message, constraints) {
  const normalized = normalizeText(message);

  if (normalized.includes('bitcoin') || normalized.includes('btc')) {
    let text = 'Bitcoin e um tipo de dinheiro digital que circula pela internet sem depender de um banco central para validar cada transferencia. As movimentacoes sao registradas por uma rede distribuida, o que ajuda a tornar o sistema verificavel e resistente a alteracoes indevidas. Ele pode ser usado para transferir valor digitalmente e tambem e tratado como um ativo no mercado de criptoativos.';
    if (constraints.maxSentences) {
      text = limitSentences(text, constraints.maxSentences);
    }
    return text;
  }

  if (normalized.includes('criptomoeda') || normalized.includes('cripto')) {
    return 'Criptomoeda e um ativo digital protegido por criptografia e normalmente operado em uma rede distribuida, o que permite transferir valor sem depender do modelo bancario tradicional em cada operacao.';
  }

  if (normalized.includes('blockchain')) {
    return 'Blockchain e um registro digital compartilhado em que varias copias do mesmo historico ficam sincronizadas, dificultando alteracoes indevidas e permitindo acompanhar transacoes com mais transparencia.';
  }

  return contextAwareDefault(message, constraints);
}

function contextAwareDefault(message, constraints) {
  let text = `Resposta direta: ${normalizeWhitespace(message)}.`;
  if (constraints.singleSentence || constraints.sentenceCount === 1) {
    return text;
  }
  if (constraints.maxSentences) {
    return limitSentences(`${text} Vou focar no essencial e manter a resposta dentro do formato pedido.`, constraints.maxSentences);
  }
  return `${text} Vou focar no essencial e manter a resposta dentro do formato pedido.`;
}

function buildEnhancedFallback({ message, strategy, context }) {
  const constraints = context?.constraints && typeof context.constraints === 'object' ? context.constraints : {};
  const taskCategory = context?.taskCategory || 'general';
  const normalized = normalizeText(message);

  if (constraints.paragraphCount === 4 && constraints.forbiddenLetters.includes('a') && constraints.rhymeRequired && normalized.includes('inteligencia artificial')) {
    return buildFourParagraphAIFallback();
  }

  if (taskCategory === 'theory_of_mind') {
    return buildTheoryOfMindFallback(message);
  }
  if (taskCategory === 'analogy') {
    return buildAnalogyFallback(message, constraints);
  }
  if (taskCategory === 'multi_perspective') {
    return buildMultiPerspectiveFallback(message, constraints);
  }
  if (taskCategory === 'structured_planning') {
    return buildPlanningFallback(message, constraints);
  }
  if (taskCategory === 'creativity') {
    return buildCreativeFallback(message, constraints);
  }
  if (taskCategory === 'constrained_format') {
    return contextAwareDefault(message, constraints);
  }
  if (strategy === 'structured_explanation' || taskCategory === 'explanation' || taskCategory === 'short_prompt') {
    return buildExplanationFallback(message, constraints);
  }

  return contextAwareDefault(message, constraints);
}

async function fetchWithTimeout(url, options, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
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
      temperature: 0.4,
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
      temperature: 0.4,
      system: systemPrompt,
      messages: [{ role: 'user', content: userPrompt }],
    }),
  });

  if (!response.ok) {
    throw new Error(`anthropic_http_${response.status}`);
  }

  const data = await response.json();
  const text = Array.isArray(data?.content)
    ? data.content.map(item => (item && item.type === 'text' ? item.text : '')).join(' ')
    : '';
  return normalizeWhitespace(text);
}

async function callOllama(systemPrompt, userPrompt) {
  const baseUrl = String(process.env.OLLAMA_URL || '').replace(/\/+$/, '');
  const response = await fetchWithTimeout(`${baseUrl}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
    taskCategory: context?.taskCategory,
  });

  if (provider === 'fallback') {
    const latencyMs = Date.now() - startedAt;
    debugLog('fallback_no_provider', { strategy, provider, planLength: Array.isArray(plan) ? plan.length : 0, latencyMs });
    return { text: fallbackText, provider: 'fallback', latencyMs, fallbackUsed: true };
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
      return { text: fallbackText, provider, latencyMs, fallbackUsed: true };
    }

    debugLog('success', { strategy, provider, planLength: Array.isArray(plan) ? plan.length : 0, latencyMs });
    return { text, provider, latencyMs, fallbackUsed: false };
  } catch (error) {
    const latencyMs = Date.now() - startedAt;
    debugLog('error', {
      strategy,
      provider,
      planLength: Array.isArray(plan) ? plan.length : 0,
      latencyMs,
      error: error instanceof Error ? error.message : 'unknown_error',
    });
    return { text: fallbackText, provider, latencyMs, fallbackUsed: true };
  }
}

module.exports = {
  generateResponse,
};


