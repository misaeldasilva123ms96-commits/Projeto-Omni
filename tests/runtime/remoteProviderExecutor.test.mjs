import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { executeRemoteProvider } = require('../../platform/providers/remoteProviderExecutor.js');

const originalGroqApiKey = process.env.GROQ_API_KEY;
const originalGroqModel = process.env.GROQ_MODEL;
const originalOpenRouterApiKey = process.env.OPENROUTER_API_KEY;
const originalOpenRouterModel = process.env.OPENROUTER_MODEL;
const originalOpenAIApiKey = process.env.OPENAI_API_KEY;
const originalOpenAIModel = process.env.OPENAI_MODEL;
const originalAnthropicApiKey = process.env.ANTHROPIC_API_KEY;
const originalAnthropicModel = process.env.ANTHROPIC_MODEL;
const originalGeminiApiKey = process.env.GEMINI_API_KEY;
const originalGeminiModel = process.env.GEMINI_MODEL;

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
  if (originalOpenAIApiKey === undefined) {
    delete process.env.OPENAI_API_KEY;
  } else {
    process.env.OPENAI_API_KEY = originalOpenAIApiKey;
  }
  if (originalOpenAIModel === undefined) {
    delete process.env.OPENAI_MODEL;
  } else {
    process.env.OPENAI_MODEL = originalOpenAIModel;
  }
  if (originalAnthropicApiKey === undefined) {
    delete process.env.ANTHROPIC_API_KEY;
  } else {
    process.env.ANTHROPIC_API_KEY = originalAnthropicApiKey;
  }
  if (originalAnthropicModel === undefined) {
    delete process.env.ANTHROPIC_MODEL;
  } else {
    process.env.ANTHROPIC_MODEL = originalAnthropicModel;
  }
  if (originalGeminiApiKey === undefined) {
    delete process.env.GEMINI_API_KEY;
  } else {
    process.env.GEMINI_API_KEY = originalGeminiApiKey;
  }
  if (originalGeminiModel === undefined) {
    delete process.env.GEMINI_MODEL;
  } else {
    process.env.GEMINI_MODEL = originalGeminiModel;
  }
}

try {
  delete process.env.GROQ_API_KEY;
  delete process.env.GROQ_MODEL;
  delete process.env.OPENROUTER_API_KEY;
  delete process.env.OPENROUTER_MODEL;
  delete process.env.OPENAI_API_KEY;
  delete process.env.OPENAI_MODEL;
  delete process.env.ANTHROPIC_API_KEY;
  delete process.env.ANTHROPIC_MODEL;
  delete process.env.GEMINI_API_KEY;
  delete process.env.GEMINI_MODEL;

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

  const openAIMissingKey = await executeRemoteProvider(
    { name: 'openai', model: 'openai-test-model' },
    {
      message: 'hello',
      fetch: async () => {
        throw new Error('fetch must not be called without an API key');
      },
    },
  );
  assert.equal(openAIMissingKey.attempted, false);
  assert.equal(openAIMissingKey.succeeded, false);
  assert.equal(openAIMissingKey.providerName, 'openai');
  assert.equal(openAIMissingKey.error, 'missing_api_key');
  assert.equal(openAIMissingKey.llm_provider_selected, 'openai');
  assert.equal(openAIMissingKey.llm_provider_attempted, false);
  assert.equal(openAIMissingKey.llm_provider_succeeded, false);
  assert.equal(openAIMissingKey.llm_provider_failed, true);

  const openAISuccess = await executeRemoteProvider(
    { name: 'openai', key: 'openai-test-key-not-secret', model: 'openai-test-model' },
    {
      message: 'Say ok',
      history: [{ role: 'assistant', content: 'Previous safe context' }],
      fetch: async (url, options) => {
        const body = JSON.parse(options.body);
        assert.equal(url, 'https://api.openai.com/v1/chat/completions');
        assert.equal(options.method, 'POST');
        assert.equal(options.headers.Authorization, 'Bearer openai-test-key-not-secret');
        assert.equal(options.headers['Content-Type'], 'application/json');
        assert.equal(body.model, 'openai-test-model');
        assert.equal(body.temperature, 0.2);
        assert.equal(body.stream, undefined);
        assert.equal(body.messages.at(-1).role, 'user');
        assert.equal(body.messages.at(-1).content, 'Say ok');
        return {
          ok: true,
          status: 200,
          statusText: 'OK',
          json: async () => ({
            choices: [{ message: { content: 'OpenAI mock response' } }],
          }),
        };
      },
    },
  );
  assert.equal(openAISuccess.attempted, true);
  assert.equal(openAISuccess.succeeded, true);
  assert.equal(openAISuccess.providerName, 'openai');
  assert.equal(openAISuccess.model, 'openai-test-model');
  assert.equal(openAISuccess.responseText, 'OpenAI mock response');
  assert.equal(openAISuccess.llm_provider_selected, 'openai');
  assert.equal(openAISuccess.llm_provider_attempted, true);
  assert.equal(openAISuccess.llm_provider_succeeded, true);
  assert.equal(openAISuccess.llm_provider_failed, false);
  assert.equal(openAISuccess.provider_attempted, true);
  assert.equal(openAISuccess.provider_succeeded, true);
  assert.equal(openAISuccess.provider_failed, false);

  const openAIHttpFailure = await executeRemoteProvider(
    { name: 'openai', key: 'openai-test-key-not-secret', model: 'openai-test-model' },
    {
      message: 'hello',
      fetch: async () => ({
        ok: false,
        status: 403,
        statusText: 'Forbidden Bearer unsafe-token-1234567890 sk-should-not-leak',
      }),
    },
  );
  assert.equal(openAIHttpFailure.attempted, true);
  assert.equal(openAIHttpFailure.succeeded, false);
  assert.equal(openAIHttpFailure.error, 'http_403');
  assert.equal(openAIHttpFailure.status, 403);
  assert.equal(JSON.stringify(openAIHttpFailure).includes('unsafe-token'), false);
  assert.equal(JSON.stringify(openAIHttpFailure).includes('sk-should-not-leak'), false);

  const openAIInvalidJson = await executeRemoteProvider(
    { name: 'openai', key: 'openai-test-key-not-secret', model: 'openai-test-model' },
    {
      message: 'hello',
      fetch: async () => ({
        ok: true,
        status: 200,
        json: async () => {
          throw new Error('invalid provider body with openai-test-key-not-secret');
        },
      }),
    },
  );
  assert.equal(openAIInvalidJson.error, 'invalid_json');
  assert.equal(JSON.stringify(openAIInvalidJson).includes('openai-test-key-not-secret'), false);

  const openAIEmptyResponse = await executeRemoteProvider(
    { name: 'openai', key: 'openai-test-key-not-secret', model: 'openai-test-model' },
    {
      message: 'hello',
      fetch: async () => ({
        ok: true,
        status: 200,
        json: async () => ({ choices: [{ message: { content: '' } }] }),
      }),
    },
  );
  assert.equal(openAIEmptyResponse.error, 'empty_response');
  assert.equal(openAIEmptyResponse.llm_public_error, 'empty_response');

  const openAINetworkFailure = await executeRemoteProvider(
    { name: 'openai', key: 'openai-test-key-not-secret', model: 'openai-test-model' },
    {
      message: 'hello',
      fetch: async () => {
        throw new TypeError('network failure with openai-test-key-not-secret');
      },
    },
  );
  const serializedOpenAIFailure = JSON.stringify(openAINetworkFailure);
  assert.equal(openAINetworkFailure.error, 'network_error');
  assert.equal(serializedOpenAIFailure.includes('openai-test-key-not-secret'), false);
  assert.equal(serializedOpenAIFailure.includes('Authorization'), false);
  assert.equal(serializedOpenAIFailure.includes('headers'), false);
  assert.equal(serializedOpenAIFailure.includes('stack'), false);

  const anthropicMissingKey = await executeRemoteProvider(
    { name: 'anthropic', model: 'anthropic-test-model' },
    {
      message: 'hello',
      fetch: async () => {
        throw new Error('fetch must not be called without an API key');
      },
    },
  );
  assert.equal(anthropicMissingKey.attempted, false);
  assert.equal(anthropicMissingKey.succeeded, false);
  assert.equal(anthropicMissingKey.providerName, 'anthropic');
  assert.equal(anthropicMissingKey.error, 'missing_api_key');
  assert.equal(anthropicMissingKey.llm_provider_selected, 'anthropic');
  assert.equal(anthropicMissingKey.llm_provider_attempted, false);
  assert.equal(anthropicMissingKey.llm_provider_succeeded, false);
  assert.equal(anthropicMissingKey.llm_provider_failed, true);

  const anthropicSuccess = await executeRemoteProvider(
    { name: 'anthropic', key: 'anthropic-test-key-not-secret', model: 'anthropic-test-model' },
    {
      message: 'Say ok',
      systemPrompt: 'Use safe concise answers.',
      history: [{ role: 'assistant', content: 'Previous safe context' }],
      fetch: async (url, options) => {
        const body = JSON.parse(options.body);
        assert.equal(url, 'https://api.anthropic.com/v1/messages');
        assert.equal(options.method, 'POST');
        assert.equal(options.headers['x-api-key'], 'anthropic-test-key-not-secret');
        assert.equal(options.headers['anthropic-version'], '2023-06-01');
        assert.equal(options.headers['Content-Type'], 'application/json');
        assert.equal(options.headers.Authorization, undefined);
        assert.equal(body.model, 'anthropic-test-model');
        assert.equal(body.max_tokens, 1024);
        assert.equal(body.temperature, undefined);
        assert.equal(body.system, 'Use safe concise answers.');
        assert.equal(body.messages.some(item => item.role === 'system'), false);
        assert.equal(body.messages.at(-1).role, 'user');
        assert.equal(body.messages.at(-1).content, 'Say ok');
        return {
          ok: true,
          status: 200,
          statusText: 'OK',
          json: async () => ({
            content: [{ type: 'text', text: 'Anthropic mock response' }],
          }),
        };
      },
    },
  );
  assert.equal(anthropicSuccess.attempted, true);
  assert.equal(anthropicSuccess.succeeded, true);
  assert.equal(anthropicSuccess.providerName, 'anthropic');
  assert.equal(anthropicSuccess.model, 'anthropic-test-model');
  assert.equal(anthropicSuccess.responseText, 'Anthropic mock response');
  assert.equal(anthropicSuccess.llm_provider_selected, 'anthropic');
  assert.equal(anthropicSuccess.llm_provider_attempted, true);
  assert.equal(anthropicSuccess.llm_provider_succeeded, true);
  assert.equal(anthropicSuccess.llm_provider_failed, false);
  assert.equal(anthropicSuccess.provider_attempted, true);
  assert.equal(anthropicSuccess.provider_succeeded, true);
  assert.equal(anthropicSuccess.provider_failed, false);

  const anthropicHttpFailure = await executeRemoteProvider(
    { name: 'anthropic', key: 'anthropic-test-key-not-secret', model: 'anthropic-test-model' },
    {
      message: 'hello',
      fetch: async () => ({
        ok: false,
        status: 401,
        statusText: 'Unauthorized x-api-key anthropic-test-key-not-secret Bearer unsafe-token-1234567890',
      }),
    },
  );
  assert.equal(anthropicHttpFailure.attempted, true);
  assert.equal(anthropicHttpFailure.succeeded, false);
  assert.equal(anthropicHttpFailure.error, 'http_401');
  assert.equal(anthropicHttpFailure.status, 401);
  assert.equal(JSON.stringify(anthropicHttpFailure).includes('anthropic-test-key-not-secret'), false);
  assert.equal(JSON.stringify(anthropicHttpFailure).includes('unsafe-token'), false);

  const anthropicInvalidJson = await executeRemoteProvider(
    { name: 'anthropic', key: 'anthropic-test-key-not-secret', model: 'anthropic-test-model' },
    {
      message: 'hello',
      fetch: async () => ({
        ok: true,
        status: 200,
        json: async () => {
          throw new Error('invalid provider body with anthropic-test-key-not-secret');
        },
      }),
    },
  );
  assert.equal(anthropicInvalidJson.error, 'invalid_json');
  assert.equal(JSON.stringify(anthropicInvalidJson).includes('anthropic-test-key-not-secret'), false);

  const anthropicEmptyResponse = await executeRemoteProvider(
    { name: 'anthropic', key: 'anthropic-test-key-not-secret', model: 'anthropic-test-model' },
    {
      message: 'hello',
      fetch: async () => ({
        ok: true,
        status: 200,
        json: async () => ({ content: [{ type: 'text', text: '   ' }] }),
      }),
    },
  );
  assert.equal(anthropicEmptyResponse.error, 'empty_response');
  assert.equal(anthropicEmptyResponse.llm_public_error, 'empty_response');

  const anthropicNetworkFailure = await executeRemoteProvider(
    { name: 'anthropic', key: 'anthropic-test-key-not-secret', model: 'anthropic-test-model' },
    {
      message: 'hello',
      fetch: async () => {
        throw new TypeError('network failure with anthropic-test-key-not-secret');
      },
    },
  );
  const serializedAnthropicFailure = JSON.stringify(anthropicNetworkFailure);
  assert.equal(anthropicNetworkFailure.error, 'network_error');
  assert.equal(serializedAnthropicFailure.includes('anthropic-test-key-not-secret'), false);
  assert.equal(serializedAnthropicFailure.includes('x-api-key'), false);
  assert.equal(serializedAnthropicFailure.includes('headers'), false);
  assert.equal(serializedAnthropicFailure.includes('stack'), false);

  const geminiMissingKey = await executeRemoteProvider(
    { name: 'gemini', model: 'gemini-test-model' },
    {
      message: 'hello',
      fetch: async () => {
        throw new Error('fetch must not be called without an API key');
      },
    },
  );
  assert.equal(geminiMissingKey.attempted, false);
  assert.equal(geminiMissingKey.succeeded, false);
  assert.equal(geminiMissingKey.providerName, 'gemini');
  assert.equal(geminiMissingKey.error, 'missing_api_key');
  assert.equal(geminiMissingKey.llm_provider_selected, 'gemini');
  assert.equal(geminiMissingKey.llm_provider_attempted, false);
  assert.equal(geminiMissingKey.llm_provider_succeeded, false);
  assert.equal(geminiMissingKey.llm_provider_failed, true);

  const geminiSuccess = await executeRemoteProvider(
    { name: 'gemini', key: 'gemini-test-key-not-secret', model: 'gemini-test-model' },
    {
      message: 'Say ok',
      systemPrompt: 'Use safe concise answers.',
      history: [{ role: 'assistant', content: 'Previous safe context' }],
      fetch: async (url, options) => {
        const body = JSON.parse(options.body);
        assert.equal(
          url,
          'https://generativelanguage.googleapis.com/v1beta/models/gemini-test-model:generateContent?key=gemini-test-key-not-secret',
        );
        assert.equal(options.method, 'POST');
        assert.equal(options.headers['Content-Type'], 'application/json');
        assert.equal(options.headers.Authorization, undefined);
        assert.equal(options.headers['x-api-key'], undefined);
        assert.equal(body.system_instruction.parts[0].text, 'Use safe concise answers.');
        assert.equal(body.contents.some(item => item.role === 'system'), false);
        assert.equal(body.contents.some(item => item.role === 'model'), true);
        assert.equal(body.contents.at(-1).role, 'user');
        assert.equal(body.contents.at(-1).parts[0].text, 'Say ok');
        return {
          ok: true,
          status: 200,
          statusText: 'OK',
          json: async () => ({
            candidates: [{ content: { parts: [{ text: 'Gemini mock response' }] } }],
          }),
        };
      },
    },
  );
  assert.equal(geminiSuccess.attempted, true);
  assert.equal(geminiSuccess.succeeded, true);
  assert.equal(geminiSuccess.providerName, 'gemini');
  assert.equal(geminiSuccess.model, 'gemini-test-model');
  assert.equal(geminiSuccess.responseText, 'Gemini mock response');
  assert.equal(geminiSuccess.llm_provider_selected, 'gemini');
  assert.equal(geminiSuccess.llm_provider_attempted, true);
  assert.equal(geminiSuccess.llm_provider_succeeded, true);
  assert.equal(geminiSuccess.llm_provider_failed, false);
  assert.equal(geminiSuccess.provider_attempted, true);
  assert.equal(geminiSuccess.provider_succeeded, true);
  assert.equal(geminiSuccess.provider_failed, false);

  const geminiHttpFailure = await executeRemoteProvider(
    { name: 'gemini', key: 'gemini-test-key-not-secret', model: 'gemini-test-model' },
    {
      message: 'hello',
      fetch: async () => ({
        ok: false,
        status: 400,
        statusText:
          'Bad Request https://generativelanguage.googleapis.com/v1beta/models/gemini-test-model:generateContent?key=gemini-test-key-not-secret Bearer unsafe-token-1234567890',
      }),
    },
  );
  assert.equal(geminiHttpFailure.attempted, true);
  assert.equal(geminiHttpFailure.succeeded, false);
  assert.equal(geminiHttpFailure.error, 'http_400');
  assert.equal(geminiHttpFailure.status, 400);
  assert.equal(JSON.stringify(geminiHttpFailure).includes('gemini-test-key-not-secret'), false);
  assert.equal(JSON.stringify(geminiHttpFailure).includes('unsafe-token'), false);

  const geminiInvalidJson = await executeRemoteProvider(
    { name: 'gemini', key: 'gemini-test-key-not-secret', model: 'gemini-test-model' },
    {
      message: 'hello',
      fetch: async () => ({
        ok: true,
        status: 200,
        json: async () => {
          throw new Error('invalid provider body with gemini-test-key-not-secret');
        },
      }),
    },
  );
  assert.equal(geminiInvalidJson.error, 'invalid_json');
  assert.equal(JSON.stringify(geminiInvalidJson).includes('gemini-test-key-not-secret'), false);

  const geminiEmptyResponse = await executeRemoteProvider(
    { name: 'gemini', key: 'gemini-test-key-not-secret', model: 'gemini-test-model' },
    {
      message: 'hello',
      fetch: async () => ({
        ok: true,
        status: 200,
        json: async () => ({ candidates: [{ content: { parts: [{ text: '   ' }] } }] }),
      }),
    },
  );
  assert.equal(geminiEmptyResponse.error, 'empty_response');
  assert.equal(geminiEmptyResponse.llm_public_error, 'empty_response');

  const geminiNetworkFailure = await executeRemoteProvider(
    { name: 'gemini', key: 'gemini-test-key-not-secret', model: 'gemini-test-model' },
    {
      message: 'hello',
      fetch: async () => {
        throw new TypeError('network failure with gemini-test-key-not-secret');
      },
    },
  );
  const serializedGeminiFailure = JSON.stringify(geminiNetworkFailure);
  assert.equal(geminiNetworkFailure.error, 'network_error');
  assert.equal(serializedGeminiFailure.includes('gemini-test-key-not-secret'), false);
  assert.equal(serializedGeminiFailure.includes('Authorization'), false);
  assert.equal(serializedGeminiFailure.includes('headers'), false);
  assert.equal(serializedGeminiFailure.includes('stack'), false);

  const unsupported = await executeRemoteProvider(
    { name: 'deepseek', model: 'deepseek-test' },
    { message: 'hello' },
  );
  assert.equal(unsupported.attempted, false);
  assert.equal(unsupported.succeeded, false);
  assert.equal(unsupported.providerName, 'deepseek');
  assert.equal(unsupported.error, 'unsupported_provider');
  assert.equal(unsupported.llm_provider_selected, 'deepseek');
  assert.equal(unsupported.llm_provider_attempted, false);
  assert.equal(unsupported.llm_provider_succeeded, false);
  assert.equal(unsupported.llm_provider_failed, true);
  assert.equal(unsupported.provider_failed, true);
  assert.equal(unsupported.llm_public_error, 'unsupported_provider');

  console.log('remoteProviderExecutor tests passed');
} finally {
  restoreEnv();
}
