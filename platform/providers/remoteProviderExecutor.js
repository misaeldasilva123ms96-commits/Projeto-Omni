'use strict';

const { buildProviderResult, toLegacyAliases } = require('./providerContract');

const GROQ_ENDPOINT = 'https://api.groq.com/openai/v1/chat/completions';
const OPENROUTER_ENDPOINT = 'https://openrouter.ai/api/v1/chat/completions';
const DEFAULT_TIMEOUT_MS = 15000;
const DEFAULT_SYSTEM_PROMPT =
  'You are Omni. Answer clearly and safely. Do not expose secrets, internal logs, raw tool payloads, or private runtime details.';
const DEFAULT_OPENROUTER_MODEL = 'openai/gpt-4o-mini';

function elapsedSince(startedAt) {
  return Math.max(0, Date.now() - startedAt);
}

function normalizedProviderName(providerConfig) {
  return String(providerConfig?.name || 'unknown').trim().toLowerCase() || 'unknown';
}

function resolveGroqModel(providerConfig = {}) {
  if (providerConfig.model) {
    return String(providerConfig.model).trim();
  }
  if (process.env.GROQ_MODEL) {
    return String(process.env.GROQ_MODEL).trim();
  }
  // Mirrors the repository's providerRouter Groq default; override with GROQ_MODEL or providerConfig.model.
  return 'llama-3.3-70b-versatile';
}

function resolveOpenRouterModel(providerConfig = {}) {
  if (providerConfig.model) {
    return String(providerConfig.model).trim();
  }
  if (process.env.OPENROUTER_MODEL) {
    return String(process.env.OPENROUTER_MODEL).trim();
  }
  return DEFAULT_OPENROUTER_MODEL;
}

function sanitizeStatusText(value) {
  return String(value || '')
    .replace(/sk-[A-Za-z0-9_-]{8,}/g, '[REDACTED_API_KEY]')
    .replace(/gsk_[A-Za-z0-9_-]{8,}/g, '[REDACTED_API_KEY]')
    .replace(/Bearer\s+[A-Za-z0-9._=-]{8,}/gi, 'Bearer [REDACTED_TOKEN]')
    .replace(/[^\w .:/()-]/g, '')
    .slice(0, 96);
}

function safeErrorCode(err) {
  const name = String(err?.name || '').toLowerCase();
  if (name === 'aborterror') {
    return 'timeout';
  }
  if (name === 'typeerror') {
    return 'network_error';
  }
  return 'provider_request_failed';
}

function normalizeHistory(history) {
  if (!Array.isArray(history)) {
    return [];
  }
  return history
    .map(item => {
      const role = String(item?.role || '').toLowerCase() === 'assistant' ? 'assistant' : 'user';
      const content = String(item?.content || item?.message || '').trim();
      return content ? { role, content } : null;
    })
    .filter(Boolean)
    .slice(-12);
}

function buildMessages(payload = {}) {
  return [
    {
      role: 'system',
      content: String(payload.systemPrompt || DEFAULT_SYSTEM_PROMPT).slice(0, 4000),
    },
    ...normalizeHistory(payload.history),
    {
      role: 'user',
      content: String(payload.message || '').slice(0, 12000),
    },
  ];
}

function buildFailure({
  attempted,
  provider = 'groq',
  model,
  error,
  startedAt,
  status = null,
  statusText = '',
}) {
  const canonical = buildProviderResult({
    providerName: provider,
    attempted,
    succeeded: false,
    failed: true,
    model,
    error,
    durationMs: elapsedSince(startedAt),
  });
  const result = {
    ...canonical,
    ...toLegacyAliases(canonical),
    attempted: Boolean(attempted),
    succeeded: false,
    providerName: provider,
    model,
    error: canonical.llm_public_error,
    durationMs: canonical.llm_latency_ms,
  };
  if (status != null) {
    result.status = Number(status);
    result.statusText = sanitizeStatusText(statusText);
  }
  return result;
}

function buildSuccess({
  provider,
  model,
  responseText,
  startedAt,
}) {
  const canonical = buildProviderResult({
    providerName: provider,
    attempted: true,
    succeeded: true,
    failed: false,
    model,
    durationMs: elapsedSince(startedAt),
  });
  return {
    ...canonical,
    ...toLegacyAliases(canonical),
    attempted: true,
    succeeded: true,
    providerName: provider,
    model,
    responseText,
    durationMs: canonical.llm_latency_ms,
  };
}

async function executeOpenAICompatibleProvider({
  providerName,
  apiKey,
  model,
  endpoint,
  messages,
  timeout,
  fetchImpl,
  startedAt = Date.now(),
}) {
  const provider = normalizedProviderName(providerName ? { name: providerName } : {});
  const normalizedKey = String(apiKey || '').trim();
  if (!normalizedKey) {
    return buildFailure({
      attempted: false,
      provider,
      model,
      error: 'missing_api_key',
      startedAt,
    });
  }

  if (typeof fetchImpl !== 'function') {
    return buildFailure({
      attempted: false,
      provider,
      model,
      error: 'fetch_unavailable',
      startedAt,
    });
  }

  const timeoutMs = Number.isFinite(Number(timeout))
    ? Math.max(1, Number(timeout))
    : DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const requestBody = {
    model,
    messages: Array.isArray(messages) ? messages : [],
    temperature: 0.2,
  };

  try {
    const response = await fetchImpl(endpoint, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${normalizedKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
      signal: controller.signal,
    });

    if (!response || !response.ok) {
      return buildFailure({
        attempted: true,
        provider,
        model,
        error: `http_${Number(response?.status || 0) || 'error'}`,
        status: response?.status ?? null,
        statusText: response?.statusText || '',
        startedAt,
      });
    }

    let data;
    try {
      data = await response.json();
    } catch (_) {
      return buildFailure({
        attempted: true,
        provider,
        model,
        error: 'invalid_json',
        startedAt,
      });
    }

    const responseText = String(data?.choices?.[0]?.message?.content || '').trim();
    if (!responseText) {
      return buildFailure({
        attempted: true,
        provider,
        model,
        error: 'empty_response',
        startedAt,
      });
    }

    return buildSuccess({
      provider,
      model,
      responseText,
      startedAt,
    });
  } catch (err) {
    return buildFailure({
      attempted: true,
      provider,
      model,
      error: safeErrorCode(err),
      startedAt,
    });
  } finally {
    clearTimeout(timer);
  }
}

async function executeRemoteProvider(providerConfig, payload = {}) {
  const startedAt = Date.now();
  const name = normalizedProviderName(providerConfig);

  if (name !== 'groq' && name !== 'openrouter') {
    const canonical = buildProviderResult({
      providerName: name,
      attempted: false,
      succeeded: false,
      failed: true,
      model: providerConfig?.model,
      error: 'unsupported_provider',
      durationMs: elapsedSince(startedAt),
    });
    return {
      ...canonical,
      ...toLegacyAliases(canonical),
      attempted: false,
      succeeded: false,
      providerName: name,
      model: providerConfig?.model,
      error: canonical.llm_public_error,
      durationMs: canonical.llm_latency_ms,
    };
  }

  const model = name === 'openrouter'
    ? resolveOpenRouterModel(providerConfig)
    : resolveGroqModel(providerConfig);
  const apiKey = name === 'openrouter'
    ? String(providerConfig?.apiKey || providerConfig?.key || process.env.OPENROUTER_API_KEY || '').trim()
    : String(providerConfig?.apiKey || providerConfig?.key || process.env.GROQ_API_KEY || '').trim();
  const endpoint = name === 'openrouter' ? OPENROUTER_ENDPOINT : GROQ_ENDPOINT;
  const fetchImpl = typeof payload.fetch === 'function' ? payload.fetch : globalThis.fetch;
  return executeOpenAICompatibleProvider({
    providerName: name,
    apiKey,
    model,
    endpoint,
    messages: buildMessages(payload),
    timeout: providerConfig?.timeoutMs,
    fetchImpl,
    startedAt,
  });
}

module.exports = { executeRemoteProvider };
