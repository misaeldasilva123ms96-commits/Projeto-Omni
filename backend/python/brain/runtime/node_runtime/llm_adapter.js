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
  ].join(' ');
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
  const planText = Array.isArray(plan) && plan.length > 0
    ? plan.map((step, index) => `${index + 1}. ${normalizeWhitespace(step)}`).join('\n')
    : '1. Understand the goal.\n2. Answer naturally.\n3. Stay aligned with user context.';

  return [
    `User question:\n${message}`,
    `Execution strategy:\n${strategyLabel(strategy)}`,
    `Execution plan:\n${planText}`,
    `Conversation summary:\n${contextSummary}`,
    `User profile hints:\n- Name: ${userName || 'unknown'}\n- Work: ${work || 'unknown'}\n- Preferred response style: ${responseStyle}\n- Preferred depth: ${depthPreference}\n- Preferences: ${preferences.length > 0 ? preferences.join(', ') : 'none'}\n- Goals: ${goals.length > 0 ? goals.join(', ') : 'none'}\n- Recurring topics: ${recurringTopics.length > 0 ? recurringTopics.join(', ') : 'none'}`,
    localDraft ? `Local fallback draft:\n${localDraft}` : '',
    'Produce only the final user-facing answer.',
  ].filter(Boolean).join('\n\n');
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
  const fallbackText = normalizeWhitespace(context?.fallbackText || context?.localDraft || '');
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
