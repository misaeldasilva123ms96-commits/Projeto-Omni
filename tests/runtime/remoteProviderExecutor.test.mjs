import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { executeRemoteProvider } = require('../../platform/providers/remoteProviderExecutor.js');

const originalGroqApiKey = process.env.GROQ_API_KEY;
const originalGroqModel = process.env.GROQ_MODEL;
const originalOpenRouterApiKey = process.env.OPENROUTER_API_KEY;
const originalOpenRouterModel = process.env.OPENROUTER_MODEL;

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
  if (originalOpenRouterApiKey === undefined) {
    delete process.env.OPENROUTER_API_KEY;
  } else {
    process.env.OPENROUTER_API_KEY = originalOpenRouterApiKey;
  }
  if (originalOpenRouterModel === undefined) {
    delete process.env.OPENROUTER_MODEL;
  } else {
    process.env.OPENROUTER_MODEL = originalOpenRouterModel;
  }
}

try {
  delete process.env.GROQ_API_KEY;
  delete process.env.GROQ_MODEL;
  delete process.env.OPENROUTER_API_KEY;
  delete process.env.OPENROUTER_MODEL;

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

  const openRouterMissingKey = await executeRemoteProvider(
    { name: 'openrouter', model: 'openrouter-test-model' },
    {
      message: 'hello',
      fetch: async () => {
        throw new Error('fetch must not be called without an API key');
      },
    },
  );
  assert.equal(openRouterMissingKey.attempted, false);
  assert.equal(openRouterMissingKey.succeeded, false);
  assert.equal(openRouterMissingKey.providerName, 'openrouter');
  assert.equal(openRouterMissingKey.error, 'missing_api_key');
  assert.equal(openRouterMissingKey.llm_provider_selected, 'openrouter');
  assert.equal(openRouterMissingKey.llm_provider_attempted, false);
  assert.equal(openRouterMissingKey.llm_provider_succeeded, false);
  assert.equal(openRouterMissingKey.llm_provider_failed, true);

  const openRouterSuccess = await executeRemoteProvider(
    { name: 'openrouter', key: 'openrouter-test-key-not-secret', model: 'openrouter-test-model' },
    {
      message: 'Say ok',
      history: [{ role: 'assistant', content: 'Previous safe context' }],
      fetch: async (url, options) => {
        const body = JSON.parse(options.body);
        assert.equal(url, 'https://openrouter.ai/api/v1/chat/completions');
        assert.equal(options.method, 'POST');
        assert.equal(options.headers.Authorization, 'Bearer openrouter-test-key-not-secret');
        assert.equal(options.headers['Content-Type'], 'application/json');
        assert.equal(options.headers['HTTP-Referer'], undefined);
        assert.equal(options.headers['X-OpenRouter-Title'], undefined);
        assert.equal(body.model, 'openrouter-test-model');
        assert.equal(body.temperature, 0.2);
        assert.equal(body.stream, undefined);
        assert.equal(body.messages.at(-1).role, 'user');
        assert.equal(body.messages.at(-1).content, 'Say ok');
        return {
          ok: true,
          status: 200,
          statusText: 'OK',
          json: async () => ({
            choices: [{ message: { content: 'OpenRouter mock response' } }],
          }),
        };
      },
    },
  );
  assert.equal(openRouterSuccess.attempted, true);
  assert.equal(openRouterSuccess.succeeded, true);
  assert.equal(openRouterSuccess.providerName, 'openrouter');
  assert.equal(openRouterSuccess.responseText, 'OpenRouter mock response');
  assert.equal(openRouterSuccess.llm_provider_selected, 'openrouter');
  assert.equal(openRouterSuccess.llm_provider_attempted, true);
  assert.equal(openRouterSuccess.llm_provider_succeeded, true);
  assert.equal(openRouterSuccess.llm_provider_failed, false);
  assert.equal(openRouterSuccess.provider_attempted, true);
  assert.equal(openRouterSuccess.provider_succeeded, true);
  assert.equal(openRouterSuccess.provider_failed, false);

  const openRouterHttpFailure = await executeRemoteProvider(
    { name: 'openrouter', key: 'openrouter-test-key-not-secret', model: 'openrouter-test-model' },
    {
      message: 'hello',
      fetch: async () => ({
        ok: false,
        status: 401,
        statusText: 'Unauthorized Bearer unsafe-token-1234567890 sk-should-not-leak',
      }),
    },
  );
  assert.equal(openRouterHttpFailure.attempted, true);
  assert.equal(openRouterHttpFailure.succeeded, false);
  assert.equal(openRouterHttpFailure.error, 'http_401');
  assert.equal(openRouterHttpFailure.status, 401);
  assert.equal(JSON.stringify(openRouterHttpFailure).includes('unsafe-token'), false);
  assert.equal(JSON.stringify(openRouterHttpFailure).includes('sk-should-not-leak'), false);

  const openRouterInvalidJson = await executeRemoteProvider(
    { name: 'openrouter', key: 'openrouter-test-key-not-secret', model: 'openrouter-test-model' },
    {
      message: 'hello',
      fetch: async () => ({
        ok: true,
        status: 200,
        json: async () => {
          throw new Error('invalid provider body with openrouter-test-key-not-secret');
        },
      }),
    },
  );
  assert.equal(openRouterInvalidJson.error, 'invalid_json');
  assert.equal(JSON.stringify(openRouterInvalidJson).includes('openrouter-test-key-not-secret'), false);

  const openRouterEmptyResponse = await executeRemoteProvider(
    { name: 'openrouter', key: 'openrouter-test-key-not-secret', model: 'openrouter-test-model' },
    {
      message: 'hello',
      fetch: async () => ({
        ok: true,
        status: 200,
        json: async () => ({ choices: [{ message: { content: '   ' } }] }),
      }),
    },
  );
  assert.equal(openRouterEmptyResponse.error, 'empty_response');
  assert.equal(openRouterEmptyResponse.llm_public_error, 'empty_response');

  const openRouterNetworkFailure = await executeRemoteProvider(
    { name: 'openrouter', key: 'openrouter-test-key-not-secret', model: 'openrouter-test-model' },
    {
      message: 'hello',
      fetch: async () => {
        throw new TypeError('network failure with openrouter-test-key-not-secret');
      },
    },
  );
  const serializedOpenRouterFailure = JSON.stringify(openRouterNetworkFailure);
  assert.equal(openRouterNetworkFailure.error, 'network_error');
  assert.equal(serializedOpenRouterFailure.includes('openrouter-test-key-not-secret'), false);
  assert.equal(serializedOpenRouterFailure.includes('Authorization'), false);
  assert.equal(serializedOpenRouterFailure.includes('headers'), false);
  assert.equal(serializedOpenRouterFailure.includes('stack'), false);

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
