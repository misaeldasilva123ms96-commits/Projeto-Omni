import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { executeRemoteProvider } = require('../../platform/providers/remoteProviderExecutor.js');

const originalGroqApiKey = process.env.GROQ_API_KEY;
const originalGroqModel = process.env.GROQ_MODEL;

function restoreEnv() {
  if (originalGroqApiKey === undefined) {
    delete process.env.GROQ_API_KEY;
  } else {
    process.env.GROQ_API_KEY = originalGroqApiKey;
  }
  if (originalGroqModel === undefined) {
    delete process.env.GROQ_MODEL;
  } else {
    process.env.GROQ_MODEL = originalGroqModel;
  }
}

try {
  delete process.env.GROQ_API_KEY;
  delete process.env.GROQ_MODEL;

  const missingKey = await executeRemoteProvider(
    { name: 'groq', model: 'test-model' },
    {
      message: 'hello',
      fetch: async () => {
        throw new Error('fetch must not be called without an API key');
      },
    },
  );
  assert.equal(missingKey.attempted, false);
  assert.equal(missingKey.succeeded, false);
  assert.equal(missingKey.error, 'missing_api_key');
  assert.equal(missingKey.providerName, 'groq');
  assert.equal(missingKey.llm_provider_selected, 'groq');
  assert.equal(missingKey.llm_provider_attempted, false);
  assert.equal(missingKey.llm_provider_succeeded, false);
  assert.equal(missingKey.llm_provider_failed, true);
  assert.equal(missingKey.provider_failed, true);
  assert.equal(missingKey.llm_public_error, 'missing_api_key');

  const success = await executeRemoteProvider(
    { name: 'groq', key: 'test-key-not-secret', model: 'test-model' },
    {
      message: 'Say ok',
      history: [{ role: 'assistant', content: 'Previous safe context' }],
      fetch: async (_url, options) => {
        const body = JSON.parse(options.body);
        assert.equal(options.method, 'POST');
        assert.equal(options.headers.Authorization, 'Bearer test-key-not-secret');
        assert.equal(body.model, 'test-model');
        assert.equal(body.messages.at(-1).role, 'user');
        assert.equal(body.messages.at(-1).content, 'Say ok');
        return {
          ok: true,
          status: 200,
          statusText: 'OK',
          json: async () => ({
            choices: [{ message: { content: 'Groq mock response' } }],
          }),
        };
      },
    },
  );
  assert.equal(success.attempted, true);
  assert.equal(success.succeeded, true);
  assert.equal(success.providerName, 'groq');
  assert.equal(success.model, 'test-model');
  assert.equal(success.responseText, 'Groq mock response');
  assert.equal(success.llm_provider_selected, 'groq');
  assert.equal(success.llm_provider_attempted, true);
  assert.equal(success.llm_provider_succeeded, true);
  assert.equal(success.llm_provider_failed, false);
  assert.equal(success.provider_attempted, true);
  assert.equal(success.provider_succeeded, true);
  assert.equal(success.provider_failed, false);
  assert.equal(success.llm_model_used, 'test-model');
  assert.equal(typeof success.llm_latency_ms, 'number');

  const httpFailure = await executeRemoteProvider(
    { name: 'groq', key: 'test-key-not-secret', model: 'test-model' },
    {
      message: 'hello',
      fetch: async () => ({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests sk-should-not-leak',
      }),
    },
  );
  assert.equal(httpFailure.attempted, true);
  assert.equal(httpFailure.succeeded, false);
  assert.equal(httpFailure.error, 'http_429');
  assert.equal(httpFailure.status, 429);
  assert.equal(JSON.stringify(httpFailure).includes('sk-should-not-leak'), false);
  assert.equal(httpFailure.llm_provider_selected, 'groq');
  assert.equal(httpFailure.llm_provider_attempted, true);
  assert.equal(httpFailure.llm_provider_succeeded, false);
  assert.equal(httpFailure.llm_provider_failed, true);
  assert.equal(httpFailure.provider_attempted, true);
  assert.equal(httpFailure.provider_succeeded, false);
  assert.equal(httpFailure.provider_failed, true);
  assert.equal(httpFailure.llm_public_error, 'http_429');

  const unsupported = await executeRemoteProvider(
    { name: 'gemini', model: 'gemini-test' },
    { message: 'hello' },
  );
  assert.equal(unsupported.attempted, false);
  assert.equal(unsupported.succeeded, false);
  assert.equal(unsupported.providerName, 'gemini');
  assert.equal(unsupported.error, 'unsupported_provider');
  assert.equal(unsupported.llm_provider_selected, 'gemini');
  assert.equal(unsupported.llm_provider_attempted, false);
  assert.equal(unsupported.llm_provider_succeeded, false);
  assert.equal(unsupported.llm_provider_failed, true);
  assert.equal(unsupported.provider_failed, true);
  assert.equal(unsupported.llm_public_error, 'unsupported_provider');

  console.log('remoteProviderExecutor tests passed');
} finally {
  restoreEnv();
}
