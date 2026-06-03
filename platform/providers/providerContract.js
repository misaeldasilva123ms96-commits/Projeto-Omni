'use strict';

const PROVIDER_STATUS = Object.freeze({
  UNSUPPORTED: 'unsupported',
  REGISTERED: 'registered',
  ACTIVE: 'active',
});

function cleanIdentifier(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_.:-]/g, '')
    .slice(0, 64);
}

function cleanReason(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_.:-]/g, '_')
    .slice(0, 96);
}

function sanitizePublicError(value) {
  return String(value || '')
    .replace(/sk-[A-Za-z0-9_-]{8,}/g, '[REDACTED_API_KEY]')
    .replace(/gsk_[A-Za-z0-9_-]{8,}/g, '[REDACTED_API_KEY]')
    .replace(/Bearer\s+[A-Za-z0-9._=-]{8,}/gi, 'Bearer [REDACTED_TOKEN]')
    .replace(/[\r\n\t]+/g, ' ')
    .replace(/[^\w .:/()-]/g, '')
    .trim()
    .slice(0, 160);
}

function normalizeLatency(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return null;
  }
  return Math.max(0, Math.round(numeric));
}

function buildProviderResult(input = {}) {
  const attempted = Boolean(input.llm_provider_attempted ?? input.attempted);
  const succeeded = Boolean(input.llm_provider_succeeded ?? input.succeeded);
  const publicError = sanitizePublicError(input.llm_public_error ?? input.publicError ?? input.error);
  const failed = Boolean(
    input.llm_provider_failed
    ?? input.failed
    ?? (attempted && !succeeded)
    ?? false,
  );

  return {
    llm_provider_selected: cleanIdentifier(
      input.llm_provider_selected
      ?? input.selectedProviderName
      ?? input.providerName
      ?? input.provider
      ?? input.name,
    ),
    llm_provider_attempted: attempted,
    llm_provider_succeeded: succeeded,
    llm_provider_failed: failed,
    llm_fallback_triggered: Boolean(input.llm_fallback_triggered ?? input.fallbackTriggered),
    llm_fallback_reason: cleanReason(input.llm_fallback_reason ?? input.fallbackReason),
    llm_model_used: String(input.llm_model_used ?? input.modelUsed ?? input.model ?? '').trim().slice(0, 128),
    llm_latency_ms: normalizeLatency(input.llm_latency_ms ?? input.latencyMs ?? input.durationMs),
    llm_public_error: publicError,
  };
}

function toLegacyAliases(result = {}) {
  const normalized = buildProviderResult(result);
  return {
    provider_attempted: normalized.llm_provider_attempted,
    provider_succeeded: normalized.llm_provider_succeeded,
    provider_failed: normalized.llm_provider_failed,
    fallback_triggered: normalized.llm_fallback_triggered,
    fallback_reason: normalized.llm_fallback_reason,
  };
}

module.exports = {
  PROVIDER_STATUS,
  buildProviderResult,
  toLegacyAliases,
};
