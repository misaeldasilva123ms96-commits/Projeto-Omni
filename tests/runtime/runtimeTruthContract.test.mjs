import assert from 'node:assert/strict'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const {
  QueryEngineAuthority,
  RUNTIME_TRUTH_MODES,
  buildRuntimeTruth,
  inferIntentWithSource,
} = require('../../core/brain/queryEngineAuthority.js')
const { getAvailableProviders } = require('../../platform/providers/providerRouter.js')
const { executeGeminiCompletion } = require('../../platform/providers/remoteProviderExecutor.js')

const providerEnvKeys = [
  'OPENAI_API_KEY',
  'OPENAI_MODEL',
  'ANTHROPIC_API_KEY',
  'ANTHROPIC_MODEL',
  'GROQ_API_KEY',
  'GROQ_MODEL',
  'GEMINI_API_KEY',
  'GEMINI_MODEL',
  'DEEPSEEK_API_KEY',
  'DEEPSEEK_MODEL',
  'OLLAMA_URL',
  'OLLAMA_MODEL',
  'OMNI_AVAILABLE_PROVIDERS',
  'OMINI_AVAILABLE_PROVIDERS',
  'OMINI_SKIP_CONVERSATIONAL_MATCHERS',
]

async function withEnv(values, fn) {
  const keys = Array.from(new Set([...providerEnvKeys, ...Object.keys(values)]))
  const saved = Object.fromEntries(keys.map(key => [key, process.env[key]]))
  for (const key of keys) {
    if (Object.prototype.hasOwnProperty.call(values, key)) {
      if (values[key] === undefined) {
        delete process.env[key]
      } else {
        process.env[key] = values[key]
      }
    } else {
      delete process.env[key]
    }
  }
  try {
    return await fn()
  } finally {
    for (const key of keys) {
      if (saved[key] === undefined) {
        delete process.env[key]
      } else {
        process.env[key] = saved[key]
      }
    }
  }
}

async function withFetchMock(mockFetch, fn) {
  const savedFetch = globalThis.fetch
  globalThis.fetch = mockFetch
  try {
    return await fn()
  } finally {
    if (savedFetch === undefined) {
      delete globalThis.fetch
    } else {
      globalThis.fetch = savedFetch
    }
  }
}

const providerEnvKeys = [
  'GROQ_API_KEY',
  'OPENROUTER_API_KEY',
  'OPENAI_API_KEY',
  'OPENAI_MODEL',
  'ANTHROPIC_API_KEY',
  'GEMINI_API_KEY',
  'DEEPSEEK_API_KEY',
  'OLLAMA_URL',
  'LMSTUDIO_URL',
  'OMINI_AVAILABLE_PROVIDERS',
  'OMNI_BYOK_SESSION_MODE',
  'OMNI_BYOK_PROVIDER',
  'OMNI_BYOK_FAIL_CLOSED',
  'OMNI_POLICY_HINT_JSON',
]

async function withNoProviderEnv(fn) {
  const saved = Object.fromEntries(providerEnvKeys.map(key => [key, process.env[key]]))
  for (const key of providerEnvKeys) {
    delete process.env[key]
  }
  try {
    await fn()
  } finally {
    for (const [key, value] of Object.entries(saved)) {
      if (value === undefined) {
        delete process.env[key]
      } else {
        process.env[key] = value
      }
    }
  }
}

const forbiddenPublicFragments = [
  'Authorization',
  'x-api-key',
  'Bearer ',
  'bearer token',
  'session_provider_credentials',
  'raw request',
  'raw response',
  'stack trace',
  'traceback',
]

function assertNoForbiddenPublicFragments(payload, fragments, label) {
  const serialized = JSON.stringify(payload)
  for (const fragment of [...forbiddenPublicFragments, ...fragments].filter(Boolean)) {
    assert.equal(serialized.includes(fragment), false, `${label} leaked public fragment: ${fragment}`)
  }
}

function collectStringPaths(value, target, prefix = '') {
  if (typeof value === 'string') {
    return value.includes(target) ? [prefix] : []
  }
  if (!value || typeof value !== 'object') {
    return []
  }
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => collectStringPaths(item, target, `${prefix}[${index}]`))
  }
  return Object.entries(value).flatMap(([key, item]) => {
    const path = prefix ? `${prefix}.${key}` : key
    return collectStringPaths(item, target, path)
  })
}

function assertModelOnlyInApprovedFields(payload, model) {
  const paths = collectStringPaths(payload, model)
  const forbiddenPaths = paths.filter(path => {
    const lastSegment = path.split(/[.[\]]/).filter(Boolean).at(-1) ?? ''
    return !lastSegment.includes('model') && lastSegment !== 'llm_model_used'
  })
  assert.deepEqual(forbiddenPaths, [], `model appeared outside approved model metadata fields: ${forbiddenPaths.join(', ')}`)
}

async function testGreetingMatcherTruth() {
  const engine = new QueryEngineAuthority()
  const result = await engine.submitMessage({
    message: 'oi',
    memoryContext: {},
    history: [],
    summary: '',
    capabilities: [],
    session: { session_id: 'truth-contract-greeting' },
    cwd: process.cwd(),
  })

  assert.equal(result.runtime_truth.runtime_mode, RUNTIME_TRUTH_MODES.MATCHER_SHORTCUT)
  assert.equal(result.runtime_truth.error_public_code, 'MATCHER_SHORTCUT_USED')
  assert.equal(result.runtime_truth.matcher_used, true)
  assert.equal(result.runtime_truth.llm_provider_attempted, false)
  assert.equal(result.runtime_truth.tool_invoked, false)
}

function testIntentWrapper() {
  const intent = inferIntentWithSource('analise o arquivo package.json')
  assert.equal(intent.intent, 'execution')
  assert.equal(intent.intent_source, 'rule_based')
  assert.equal(intent.classifier_version, 'regex_v1')
  assert.equal(intent.confidence, 0.7)
}

function testTruthHelperModes() {
  const providerUnavailable = buildRuntimeTruth({
    runtimeMode: RUNTIME_TRUTH_MODES.PROVIDER_UNAVAILABLE,
    runtimeReason: 'provider_unavailable',
    intentInfo: inferIntentWithSource('resuma este texto'),
    providerAttempted: true,
    providerSucceeded: false,
  })
  assert.equal(providerUnavailable.runtime_mode, RUNTIME_TRUTH_MODES.PROVIDER_UNAVAILABLE)
  assert.equal(providerUnavailable.error_public_code, 'PROVIDER_UNAVAILABLE')
  assert.equal(providerUnavailable.llm_provider_succeeded, false)

  const toolBlocked = buildRuntimeTruth({
    runtimeMode: RUNTIME_TRUTH_MODES.TOOL_BLOCKED,
    runtimeReason: 'tool_blocked',
    intentInfo: inferIntentWithSource('apague tudo'),
    toolInvoked: true,
    toolExecuted: false,
    toolStatus: 'blocked',
  })
  assert.equal(toolBlocked.tool_executed, false)
  assert.equal(toolBlocked.error_public_code, 'TOOL_BLOCKED_BY_GOVERNANCE')
  assert.equal(toolBlocked.tool_status, 'blocked')

  const toolExecuted = buildRuntimeTruth({
    runtimeMode: RUNTIME_TRUTH_MODES.TOOL_EXECUTED,
    runtimeReason: 'node_local_tool_run',
    intentInfo: inferIntentWithSource('leia package.json'),
    toolInvoked: true,
    toolExecuted: true,
    toolStatus: 'executed',
  })
  assert.equal(toolExecuted.runtime_mode, RUNTIME_TRUTH_MODES.TOOL_EXECUTED)
  assert.equal(toolExecuted.tool_executed, true)

  const fallback = buildRuntimeTruth({
    runtimeMode: RUNTIME_TRUTH_MODES.FULL_COGNITIVE_RUNTIME,
    runtimeReason: 'safe_fallback',
    intentInfo: inferIntentWithSource('teste'),
    fallbackTriggered: true,
  })
  assert.notEqual(fallback.runtime_mode, RUNTIME_TRUTH_MODES.FULL_COGNITIVE_RUNTIME)
}

async function testGeminiProviderSuccessTruth() {
  await withEnv({
    GEMINI_API_KEY: 'test-gemini-key',
    GEMINI_MODEL: 'gemini-test-model',
    OMNI_AVAILABLE_PROVIDERS: 'gemini',
    OMINI_SKIP_CONVERSATIONAL_MATCHERS: '1',
  }, async () => {
    await withFetchMock(async () => ({
      ok: true,
      async json() {
        return {
          candidates: [
            {
              content: {
                parts: [{ text: 'OMNI_PROVIDER_TEST_OK' }],
              },
            },
          ],
        }
      },
    }), async () => {
      const engine = new QueryEngineAuthority()
      const result = await engine.submitMessage({
        message: 'Responda apenas: OMNI_PROVIDER_TEST_OK',
        memoryContext: {},
        history: [],
        summary: '',
        capabilities: [],
        session: { session_id: 'truth-contract-gemini-success' },
        cwd: process.cwd(),
      })

      assert.equal(result.response, 'OMNI_PROVIDER_TEST_OK')
      assert.equal(result.runtime_truth.runtime_mode, RUNTIME_TRUTH_MODES.PARTIAL_COGNITIVE)
      assert.equal(result.runtime_truth.runtime_reason, 'remote_provider_response')
      assert.equal(result.runtime_truth.llm_provider_attempted, true)
      assert.equal(result.runtime_truth.llm_provider_succeeded, true)
      assert.equal(result.runtime_truth.tool_invoked, false)
      assert.equal(result.metadata.execution_provenance.provider_actual, 'gemini')
      assert.equal(result.metadata.execution_provenance.model_actual, 'gemini-test-model')
      const gemini = result.metadata.execution_provenance.provider_diagnostics.find(row => row.provider === 'gemini')
      assert.equal(gemini.selected, true)
      assert.equal(gemini.attempted, true)
      assert.equal(gemini.succeeded, true)
      assert.equal(gemini.failed, false)
    })
  })
}

async function testGeminiProviderFailureFallsBackSafely() {
  await withEnv({
    GEMINI_API_KEY: 'test-gemini-key',
    GEMINI_MODEL: 'gemini-test-model',
    OMNI_AVAILABLE_PROVIDERS: 'gemini',
    OMINI_SKIP_CONVERSATIONAL_MATCHERS: '1',
  }, async () => {
    await withFetchMock(async () => ({
      ok: false,
      status: 500,
      async json() {
        return { error: { message: 'raw upstream detail must not appear' } }
      },
    }), async () => {
      const engine = new QueryEngineAuthority()
      const result = await engine.submitMessage({
        message: 'Explique de forma curta o que e uma API distribuida',
        memoryContext: {},
        history: [],
        summary: '',
        capabilities: [],
        session: { session_id: 'truth-contract-gemini-failure' },
        cwd: process.cwd(),
      })

      assert.equal(typeof result.response, 'string')
      assert.ok(result.response.trim().length > 0)
      assert.notEqual(result.response, 'raw upstream detail must not appear')
      assert.equal(result.runtime_truth.llm_provider_attempted, true)
      assert.equal(result.runtime_truth.llm_provider_succeeded, false)
      const provenance = result.metadata.execution_provenance
      assert.equal(provenance.provider_failed, true)
      assert.equal(provenance.failure_class, 'provider_http_error')
      const serialized = JSON.stringify(result)
      assert.equal(serialized.includes('test-gemini-key'), false)
      assert.equal(serialized.includes('raw upstream detail must not appear'), false)
      const gemini = provenance.provider_diagnostics.find(row => row.provider === 'gemini')
      assert.equal(gemini.attempted, true)
      assert.equal(gemini.succeeded, false)
      assert.equal(gemini.failed, true)
    })
  })
}

async function testNoProviderKeepsLocalHeuristicBehavior() {
  await withEnv({
    OMINI_SKIP_CONVERSATIONAL_MATCHERS: '1',
  }, async () => {
    await withFetchMock(async () => {
      throw new Error('fetch should not be called without a remote provider')
    }, async () => {
      const engine = new QueryEngineAuthority()
      const result = await engine.submitMessage({
        message: 'Explique brevemente arquitetura hexagonal',
        memoryContext: {},
        history: [],
        summary: '',
        capabilities: [],
        session: { session_id: 'truth-contract-local-fallback' },
        cwd: process.cwd(),
      })

      assert.equal(typeof result.response, 'string')
      assert.ok(result.response.trim().length > 0)
      assert.equal(result.runtime_truth.llm_provider_attempted, false)
      assert.equal(result.runtime_truth.llm_provider_succeeded, false)
      assert.equal(result.metadata.execution_provenance.provider_actual, 'local-heuristic')
    })
  })
}

async function testProviderRouterAcceptsOmniAndOminiAliases() {
  await withEnv({
    GEMINI_API_KEY: 'test-gemini-key',
    GROQ_API_KEY: 'test-groq-key',
    OMNI_AVAILABLE_PROVIDERS: 'gemini',
    OMINI_AVAILABLE_PROVIDERS: 'groq',
  }, async () => {
    const providers = getAvailableProviders()
    assert.equal(providers[0].name, 'gemini')
  })

  await withEnv({
    GEMINI_API_KEY: 'test-gemini-key',
    GROQ_API_KEY: 'test-groq-key',
    OMINI_AVAILABLE_PROVIDERS: 'gemini',
  }, async () => {
    const providers = getAvailableProviders()
    assert.equal(providers[0].name, 'gemini')
  })
}

async function testGeminiDefaultModel() {
  await withEnv({
    GEMINI_API_KEY: 'test-gemini-key',
    OMNI_AVAILABLE_PROVIDERS: 'gemini',
  }, async () => {
    const providers = getAvailableProviders()
    const gemini = providers.find(provider => provider.name === 'gemini')
    assert.equal(gemini.model, 'gemini-2.5-flash-lite')
  })
}

async function testRemoteExecutorDefaultGeminiModel() {
  await withEnv({
    GEMINI_API_KEY: 'test-gemini-key',
  }, async () => {
    let requestedUrl = ''
    const result = await executeGeminiCompletion({
      provider: { name: 'gemini' },
      message: 'Responda apenas: OK',
      fetchImpl: async url => {
        requestedUrl = String(url)
        return {
          ok: true,
          async json() {
            return {
              candidates: [
                {
                  content: {
                    parts: [{ text: 'OK' }],
                  },
                },
              ],
            }
          },
        }
      },
    })

    assert.equal(result.ok, true)
    assert.equal(result.model, 'gemini-2.5-flash-lite')
    assert.equal(requestedUrl.includes('gemini-2.5-flash-lite'), true)
    assert.equal(requestedUrl.includes('test-gemini-key'), true)
  })
}

await testGreetingMatcherTruth()
await testNoRemoteProviderFallbackTruth()
await testByokFailClosedDoesNotFallbackToSystemProvider()
await testByokHappyPathUsesSessionProviderOnly()
await testByokProviderFailureDoesNotFallbackToSystemProvider()
await testByokUnsupportedProviderHintFailsClosedPublicly()
await testNormalRemoteFallbackPreservesCanonicalAndLegacyAliases()
await testByokUnknownProviderHintFailsClosedPublicly()
testIntentWrapper()
testTruthHelperModes()
await testGeminiProviderSuccessTruth()
await testGeminiProviderFailureFallsBackSafely()
await testNoProviderKeepsLocalHeuristicBehavior()
await testProviderRouterAcceptsOmniAndOminiAliases()
await testGeminiDefaultModel()
await testRemoteExecutorDefaultGeminiModel()
console.log('runtime truth contract: js checks passed')
