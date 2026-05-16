'use strict';

const GROQ_ENDPOINT = 'https://api.groq.com/openai/v1/chat/completions';
const DEFAULT_TIMEOUT_MS = 15000;
const DEFAULT_SYSTEM_PROMPT =
  'You are Omni. Answer clearly and safely. Do not expose secrets, internal logs, raw tool payloads, or private runtime details.';

function elapsedSince(startedAt) {
  return Math.max(0, Date.now() - startedAt);
}

function providerName(providerConfig) {
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

function buildFailure({
  attempted,
  provider = 'groq',
  model,
  error,
  startedAt,
  status = null,
  statusText = '',
}) {
  const result = {
    attempted: Boolean(attempted),
    succeeded: false,
    providerName: provider,
    model,
    error,
    durationMs: elapsedSince(startedAt),
  };
  if (status != null) {
    result.status = Number(status);
    result.statusText = sanitizeStatusText(statusText);
  }
  return result;
}

async function executeRemoteProvider(providerConfig, payload = {}) {
  const startedAt = Date.now();
  const name = providerName(providerConfig);

  if (name !== 'groq') {
    return {
      attempted: false,
      succeeded: false,
      providerName: name,
      error: 'unsupported_provider',
      durationMs: elapsedSince(startedAt),
    };
  }

  const model = resolveGroqModel(providerConfig);
  const apiKey = String(providerConfig?.apiKey || providerConfig?.key || process.env.GROQ_API_KEY || '').trim();
  if (!apiKey) {
    return buildFailure({
      attempted: false,
      model,
      error: 'missing_api_key',
      startedAt,
    });
  }

  const fetchImpl = typeof payload.fetch === 'function' ? payload.fetch : globalThis.fetch;
  if (typeof fetchImpl !== 'function') {
    return buildFailure({
      attempted: false,
      model,
      error: 'fetch_unavailable',
      startedAt,
    });
  }

  const timeoutMs = Number.isFinite(Number(providerConfig?.timeoutMs))
    ? Math.max(1, Number(providerConfig.timeoutMs))
    : DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const requestBody = {
    model,
    messages: [
      {
        role: 'system',
        content: String(payload.systemPrompt || DEFAULT_SYSTEM_PROMPT).slice(0, 4000),
      },
      ...normalizeHistory(payload.history),
      {
        role: 'user',
        content: String(payload.message || '').slice(0, 12000),
      },
    ],
    temperature: 0.2,
  };

  try {
    const response = await fetchImpl(GROQ_ENDPOINT, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
      signal: controller.signal,
    });

    if (!response || !response.ok) {
      return buildFailure({
        attempted: true,
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
        model,
        error: 'invalid_json',
        startedAt,
      });
    }

    const responseText = String(data?.choices?.[0]?.message?.content || '').trim();
    if (!responseText) {
      return buildFailure({
        attempted: true,
        model,
        error: 'empty_response',
        startedAt,
      });
    }

    return {
      attempted: true,
      succeeded: true,
      providerName: 'groq',
      model,
      responseText,
      durationMs: elapsedSince(startedAt),
    };
  } catch (err) {
    return buildFailure({
      attempted: true,
      model,
      error: safeErrorCode(err),
      startedAt,
    });
  } finally {
    clearTimeout(timeout);
  }
}

module.exports = { executeRemoteProvider };
