import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const {
  PROVIDER_STATUS,
  buildProviderResult,
  toLegacyAliases,
} = require('../../platform/providers/providerContract.js');

assert.deepEqual(PROVIDER_STATUS, {
  UNSUPPORTED: 'unsupported',
  REGISTERED: 'registered',
  ACTIVE: 'active',
});

const defaults = buildProviderResult();
assert.deepEqual(defaults, {
  llm_provider_selected: '',
  llm_provider_attempted: false,
  llm_provider_succeeded: false,
  llm_provider_failed: false,
  llm_fallback_triggered: false,
  llm_fallback_reason: '',
  llm_model_used: '',
  llm_latency_ms: null,
  llm_public_error: '',
});

const normalized = buildProviderResult({
  providerName: ' Groq ',
  attempted: true,
  succeeded: false,
  fallbackTriggered: true,
  fallbackReason: 'Provider Timeout!',
  model: 'llama-test',
  durationMs: 12.7,
  error: 'Bearer unsafe-token-1234567890 sk-secretvalue',
});

assert.equal(normalized.llm_provider_selected, 'groq');
assert.equal(normalized.llm_provider_attempted, true);
assert.equal(normalized.llm_provider_succeeded, false);
assert.equal(normalized.llm_provider_failed, true);
assert.equal(normalized.llm_fallback_triggered, true);
assert.equal(normalized.llm_fallback_reason, 'provider_timeout_');
assert.equal(normalized.llm_model_used, 'llama-test');
assert.equal(normalized.llm_latency_ms, 13);
assert.equal(normalized.llm_public_error.includes('unsafe-token'), false);
assert.equal(normalized.llm_public_error.includes('sk-secretvalue'), false);

assert.deepEqual(toLegacyAliases(normalized), {
  provider_attempted: true,
  provider_succeeded: false,
  provider_failed: true,
  fallback_triggered: true,
  fallback_reason: 'provider_timeout_',
});

console.log('providerContract tests passed');
