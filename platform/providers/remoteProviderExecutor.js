'use strict';

const { performance } = require('perf_hooks');

function envValue(name) {
  const value = process.env[name];
  return typeof value === 'string' ? value.trim() : '';
}

function safeFailure(provider, model, failureClass, startedAt) {
  return {
    ok: false,
    text: '',
    provider: String(provider || '').trim().toLowerCase(),
    model: String(model || '').trim(),
    failure_class: String(failureClass || 'provider_error').trim().toLowerCase(),
    failure_reason: 'Remote provider request failed.',
    latency_ms: Math.max(0, Math.round(performance.now() - startedAt)),
  };
}

function extractGeminiText(payload) {
  const parts = payload?.candidates?.[0]?.content?.parts;
  if (!Array.isArray(parts)) {
    return '';
  }
  return parts
    .map(part => (typeof part?.text === 'string' ? part.text : ''))
    .filter(Boolean)
    .join('\n')
    .trim();
}

function compactContext({ message, intent, summary }) {
  const safeSummary = String(summary || '').trim().slice(0, 1000);
  const safeIntent = String(intent || 'conversation').trim().slice(0, 64);
  return [
    'You are Omni, a concise and safe assistant inside a governed cognitive runtime.',
    'Answer the user directly. Do not claim tools or files were executed unless the prompt explicitly provides that evidence.',
    `Runtime intent: ${safeIntent}.`,
    safeSummary ? `Conversation summary: ${safeSummary}` : '',
    '',
    `User message:\n${String(message || '').trim().slice(0, 12000)}`,
  ].filter(Boolean).join('\n');
}

async function executeGeminiCompletion({ provider, message, intent, summary, fetchImpl = globalThis.fetch } = {}) {
  const model = String(provider?.model || envValue('GEMINI_MODEL') || 'gemini-2.0-flash').trim();
  const startedAt = performance.now();
  const apiKey = envValue('GEMINI_API_KEY');

  if (!apiKey) {
    return safeFailure('gemini', model, 'provider_not_configured', startedAt);
  }
  if (typeof fetchImpl !== 'function') {
    return safeFailure('gemini', model, 'provider_fetch_unavailable', startedAt);
  }

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(apiKey)}`;

  try {
    const response = await fetchImpl(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        contents: [
          {
            role: 'user',
            parts: [{ text: compactContext({ message, intent, summary }) }],
          },
        ],
        generationConfig: {
          temperature: 0.2,
          maxOutputTokens: 1024,
        },
      }),
    });

    if (!response || !response.ok) {
      return safeFailure('gemini', model, 'provider_http_error', startedAt);
    }

    const payload = await response.json();
    const text = extractGeminiText(payload);
    if (!text) {
      return safeFailure('gemini', model, 'provider_empty_response', startedAt);
    }

    return {
      ok: true,
      text,
      provider: 'gemini',
      model,
      latency_ms: Math.max(0, Math.round(performance.now() - startedAt)),
    };
  } catch (_) {
    return safeFailure('gemini', model, 'provider_request_failed', startedAt);
  }
}

async function executeRemoteProviderCompletion({ provider, message, intent, summary, fetchImpl } = {}) {
  const providerName = String(provider?.name || '').trim().toLowerCase();
  if (providerName === 'gemini') {
    return executeGeminiCompletion({ provider, message, intent, summary, fetchImpl });
  }

  return {
    ok: false,
    text: '',
    provider: providerName,
    model: String(provider?.model || '').trim(),
    failure_class: 'provider_not_implemented',
    failure_reason: 'Remote provider is configured but not implemented in QueryEngine.',
    latency_ms: 0,
  };
}

module.exports = {
  executeRemoteProviderCompletion,
  executeGeminiCompletion,
};
