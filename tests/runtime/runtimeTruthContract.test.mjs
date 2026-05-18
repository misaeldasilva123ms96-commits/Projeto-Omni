import assert from 'node:assert/strict'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const {
  QueryEngineAuthority,
  RUNTIME_TRUTH_MODES,
  buildRuntimeTruth,
  inferIntentWithSource,
} = require('../../core/brain/queryEngineAuthority.js')

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

async function testNoRemoteProviderFallbackTruth() {
  await withNoProviderEnv(async () => {
    const engine = new QueryEngineAuthority()
    const result = await engine.submitMessage({
      message: 'Explique este projeto em uma frase curta.',
      memoryContext: {},
      history: [],
      summary: '',
      capabilities: [],
      session: { session_id: 'truth-contract-no-provider' },
      cwd: process.cwd(),
    })

    assert.equal(result.selected_provider, 'local-heuristic')
    assert.equal(result.executed_provider, '')
    assert.equal(result.execution_fallback_used, true)
    assert.equal(result.llm_fallback_triggered, true)
    assert.equal(result.llm_fallback_reason, 'no_remote_provider_available')
    assert.equal(result.fallback_triggered, true)
    assert.equal(result.fallback_reason, 'no_remote_provider_available')
    assert.equal(result.runtime_truth.llm_provider_attempted, false)
    assert.equal(result.runtime_truth.llm_provider_succeeded, false)
    assert.equal(result.runtime_truth.fallback_triggered, true)
    const diagnostics = result.metadata.execution_provenance.provider_diagnostics
    const local = diagnostics.find(row => row.provider === 'local-heuristic')
    assert.equal(local.selected, true)
    assert.equal(local.attempted, false)
  })
}

async function testByokFailClosedDoesNotFallbackToSystemProvider() {
  const saved = Object.fromEntries(providerEnvKeys.map(key => [key, process.env[key]]))
  for (const key of providerEnvKeys) {
    delete process.env[key]
  }
  process.env.OMNI_BYOK_SESSION_MODE = 'true'
  process.env.OMNI_BYOK_PROVIDER = 'openai'
  process.env.OMNI_BYOK_FAIL_CLOSED = 'true'
  process.env.GROQ_API_KEY = 'system-groq-key'
  try {
    const engine = new QueryEngineAuthority()
    const result = await engine.submitMessage({
      message: 'Explique este projeto em uma frase curta.',
      memoryContext: {},
      history: [],
      summary: '',
      capabilities: [],
      session: { session_id: 'truth-contract-byok-fail-closed' },
      cwd: process.cwd(),
    })

    assert.equal(result.selected_provider, 'openai')
    assert.equal(result.executed_provider, '')
    assert.equal(result.provider_failed, true)
    assert.equal(result.failure_class, 'byok_execution_failed')
    assert.equal(result.runtime_truth.runtime_mode, RUNTIME_TRUTH_MODES.PROVIDER_UNAVAILABLE)
    assert.equal(result.runtime_truth.llm_provider_attempted, false)
    assert.equal(result.response.includes('byok_session'), true)
    const diagnostics = result.metadata.execution_provenance.provider_diagnostics
    const groq = diagnostics.find(row => row.provider === 'groq')
    assert.equal(groq.attempted, false)
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

async function testByokHappyPathUsesSessionProviderOnly() {
  const saved = Object.fromEntries(providerEnvKeys.map(key => [key, process.env[key]]))
  const savedFetch = globalThis.fetch
  for (const key of providerEnvKeys) {
    delete process.env[key]
  }
  process.env.OMNI_BYOK_SESSION_MODE = 'true'
  process.env.OMNI_BYOK_PROVIDER = 'openai'
  process.env.OMNI_BYOK_FAIL_CLOSED = 'true'
  process.env.GROQ_API_KEY = 'sk-test-system-groq'
  process.env.OPENAI_API_KEY = 'sk-test-byok-session-openai'
  process.env.OPENAI_MODEL = 'byok-test-model'
  let fetchCalls = 0
  globalThis.fetch = async (url, options = {}) => {
    fetchCalls += 1
    assert.equal(url, 'https://api.openai.com/v1/chat/completions')
    assert.equal(options.headers.Authorization, 'Bearer sk-test-byok-session-openai')
    assert.equal(String(options.headers.Authorization).includes('sk-test-system-groq'), false)
    assert.equal(JSON.parse(options.body).model, 'byok-test-model')
    return {
      ok: true,
      status: 200,
      statusText: 'OK',
      json: async () => ({ choices: [{ message: { content: 'BYOK OpenAI mock response' } }] }),
    }
  }
  try {
    const engine = new QueryEngineAuthority()
    const result = await engine.submitMessage({
      message: 'Explique este projeto em uma frase curta.',
      memoryContext: {},
      history: [],
      summary: '',
      capabilities: [],
      session: { session_id: 'truth-contract-byok-happy-path' },
      cwd: process.cwd(),
    })
    const serialized = JSON.stringify(result)

    assert.equal(fetchCalls, 1)
    assert.equal(result.selected_provider, 'openai')
    assert.equal(result.executed_provider, 'openai')
    assert.equal(result.runtime_truth.llm_provider_attempted, true)
    assert.equal(result.runtime_truth.llm_provider_succeeded, true)
    assert.notEqual(result.provider_failed, true)
    assert.equal(result.response, 'BYOK OpenAI mock response')
    assert.equal(result.metadata.execution_provenance.model_actual, 'byok-test-model')
    assert.equal(result.metadata.model, 'byok-test-model')
    assert.equal(serialized.includes('sk-test-byok-session-openai'), false)
    assert.equal(serialized.includes('sk-test-system-groq'), false)
    assert.equal(serialized.includes('sk-test-system-openai'), false)
    assert.equal(serialized.includes('Authorization'), false)
    assert.equal(serialized.includes('x-api-key'), false)
    assert.equal(serialized.includes('bearer token'), false)
    assert.equal(serialized.includes('session_provider_credentials'), false)
    assert.equal(serialized.includes('raw request'), false)
    assert.equal(serialized.includes('raw response'), false)
    assert.equal(serialized.includes('stack'), false)
    const diagnostics = result.metadata.execution_provenance.provider_diagnostics
    assert.equal(JSON.stringify(diagnostics).includes('byok-test-model'), false)
    assert.equal(JSON.stringify(result.provider_diagnostics ?? []).includes('byok-test-model'), false)
    assert.equal(JSON.stringify(result.provider_diagnostics_snapshot ?? {}).includes('byok-test-model'), false)
    assert.equal(JSON.stringify(result.error ?? {}).includes('byok-test-model'), false)
    assert.equal(JSON.stringify(result.runtime_truth ?? {}).includes('byok-test-model'), false)
    assert.equal(JSON.stringify(result.cognitive_runtime_inspection ?? {}).includes('byok-test-model'), false)
    const groq = diagnostics.find(row => row.provider === 'groq')
    assert.equal(groq.attempted, false)
  } finally {
    globalThis.fetch = savedFetch
    for (const [key, value] of Object.entries(saved)) {
      if (value === undefined) {
        delete process.env[key]
      } else {
        process.env[key] = value
      }
    }
  }
}

async function testByokProviderFailureDoesNotFallbackToSystemProvider() {
  const saved = Object.fromEntries(providerEnvKeys.map(key => [key, process.env[key]]))
  const savedFetch = globalThis.fetch
  for (const key of providerEnvKeys) {
    delete process.env[key]
  }
  process.env.OMNI_BYOK_SESSION_MODE = 'true'
  process.env.OMNI_BYOK_PROVIDER = 'openai'
  process.env.OMNI_BYOK_FAIL_CLOSED = 'true'
  process.env.GROQ_API_KEY = 'sk-test-system-groq'
  process.env.OPENROUTER_API_KEY = 'sk-test-system-openrouter'
  process.env.OPENAI_API_KEY = 'sk-test-byok-session-openai'
  let fetchCalls = 0
  globalThis.fetch = async (url, options = {}) => {
    fetchCalls += 1
    assert.equal(url, 'https://api.openai.com/v1/chat/completions')
    assert.equal(options.headers.Authorization, 'Bearer sk-test-byok-session-openai')
    return {
      ok: false,
      status: 401,
      statusText: 'Unauthorized Bearer sk-test-byok-session-openai',
      json: async () => ({ error: { message: 'should not be exposed' } }),
    }
  }
  try {
    const engine = new QueryEngineAuthority()
    const result = await engine.submitMessage({
      message: 'Explique este projeto em uma frase curta.',
      memoryContext: {},
      history: [],
      summary: '',
      capabilities: [],
      session: { session_id: 'truth-contract-byok-provider-failure' },
      cwd: process.cwd(),
    })
    const serialized = JSON.stringify(result)

    assert.equal(fetchCalls, 1)
    assert.equal(result.selected_provider, 'openai')
    assert.equal(result.executed_provider, '')
    assert.equal(result.runtime_truth.llm_provider_attempted, true)
    assert.equal(result.runtime_truth.llm_provider_succeeded, false)
    assert.equal(result.provider_failed, true)
    assert.equal(result.failure_class, 'byok_execution_failed')
    assert.equal(result.failure_reason, 'http_401')
    assert.equal(result.response.includes('byok_session'), true)
    assert.equal(result.runtime_truth.runtime_mode, RUNTIME_TRUTH_MODES.PROVIDER_UNAVAILABLE)
    assert.equal(serialized.includes('sk-test-byok-session-openai'), false)
    assert.equal(serialized.includes('sk-test-system-groq'), false)
    assert.equal(serialized.includes('sk-test-system-openrouter'), false)
    assert.equal(serialized.includes('Authorization'), false)
    assert.equal(serialized.includes('x-api-key'), false)
    assert.equal(serialized.includes('Bearer'), false)
    assert.equal(serialized.includes('bearer token'), false)
    assert.equal(serialized.includes('session_provider_credentials'), false)
    assert.equal(serialized.includes('raw request'), false)
    assert.equal(serialized.includes('raw response'), false)
    assert.equal(serialized.includes('stack'), false)
    assert.equal(serialized.includes('should not be exposed'), false)
    const diagnostics = result.metadata.execution_provenance.provider_diagnostics
    assert.equal(diagnostics.find(row => row.provider === 'groq').attempted, false)
    assert.equal(diagnostics.find(row => row.provider === 'openrouter').attempted, false)
  } finally {
    globalThis.fetch = savedFetch
    for (const [key, value] of Object.entries(saved)) {
      if (value === undefined) {
        delete process.env[key]
      } else {
        process.env[key] = value
      }
    }
  }
}

async function testByokUnsupportedProviderHintFailsClosedPublicly() {
  const saved = Object.fromEntries(providerEnvKeys.map(key => [key, process.env[key]]))
  const savedFetch = globalThis.fetch
  for (const key of providerEnvKeys) {
    delete process.env[key]
  }
  process.env.OMNI_BYOK_SESSION_MODE = 'true'
  process.env.OMNI_BYOK_PROVIDER = 'deepseek'
  process.env.OMNI_BYOK_FAIL_CLOSED = 'true'
  process.env.DEEPSEEK_API_KEY = 'sk-test-byok-deepseek'
  let fetchCalls = 0
  globalThis.fetch = async () => {
    fetchCalls += 1
    throw new Error('fetch must not be called for unsupported BYOK provider')
  }
  try {
    const engine = new QueryEngineAuthority()
    const result = await engine.submitMessage({
      message: 'Explique este projeto em uma frase curta.',
      memoryContext: {},
      history: [],
      summary: '',
      capabilities: [],
      session: { session_id: 'truth-contract-byok-unsupported-provider' },
      cwd: process.cwd(),
    })
    const serialized = JSON.stringify(result)

    assert.equal(fetchCalls, 0)
    assert.equal(result.selected_provider, 'deepseek')
    assert.equal(result.executed_provider, '')
    assert.equal(result.provider_failed, true)
    assert.equal(result.failure_class, 'byok_execution_failed')
    assert.equal(result.failure_reason, 'byok_credentials_incomplete')
    assert.equal(result.response.includes('byok_session'), true)
    assert.equal(serialized.includes('sk-test-byok-deepseek'), false)
  } finally {
    globalThis.fetch = savedFetch
    for (const [key, value] of Object.entries(saved)) {
      if (value === undefined) {
        delete process.env[key]
      } else {
        process.env[key] = value
      }
    }
  }
}

async function testNormalRemoteFallbackPreservesCanonicalAndLegacyAliases() {
  const saved = Object.fromEntries(providerEnvKeys.map(key => [key, process.env[key]]))
  const savedFetch = globalThis.fetch
  for (const key of providerEnvKeys) {
    delete process.env[key]
  }
  process.env.OPENROUTER_API_KEY = 'sk-test-openrouter-normal-fallback'
  process.env.OMNI_POLICY_HINT_JSON = JSON.stringify({ recommended_provider: 'groq', shadow_only: false })
  let fetchCalls = 0
  globalThis.fetch = async (url, options = {}) => {
    fetchCalls += 1
    assert.equal(url, 'https://openrouter.ai/api/v1/chat/completions')
    assert.equal(options.headers.Authorization, 'Bearer sk-test-openrouter-normal-fallback')
    return {
      ok: true,
      status: 200,
      statusText: 'OK',
      json: async () => ({ choices: [{ message: { content: 'OpenRouter fallback response' } }] }),
    }
  }
  try {
    const engine = new QueryEngineAuthority()
    const result = await engine.submitMessage({
      message: 'Explique este projeto em uma frase curta.',
      memoryContext: {},
      history: [],
      summary: '',
      capabilities: [],
      session: { session_id: 'truth-contract-normal-fallback' },
      cwd: process.cwd(),
    })
    const serialized = JSON.stringify(result)

    assert.equal(fetchCalls, 1)
    assert.equal(result.selected_provider, 'openrouter')
    assert.equal(result.executed_provider, 'openrouter')
    assert.equal(result.runtime_truth.llm_provider_attempted, true)
    assert.equal(result.runtime_truth.llm_provider_succeeded, true)
    assert.equal(result.llm_fallback_triggered, true)
    assert.equal(result.llm_fallback_reason, 'requested_provider_unavailable')
    assert.equal(result.fallback_triggered, result.llm_fallback_triggered)
    assert.equal(result.fallback_reason, result.llm_fallback_reason)
    assert.equal(serialized.includes('sk-test-openrouter-normal-fallback'), false)
    assert.equal(serialized.includes('Authorization'), false)
    assert.equal(serialized.includes('raw request'), false)
    assert.equal(serialized.includes('raw response'), false)
    assert.equal(serialized.includes('stack'), false)
  } finally {
    globalThis.fetch = savedFetch
    for (const [key, value] of Object.entries(saved)) {
      if (value === undefined) {
        delete process.env[key]
      } else {
        process.env[key] = value
      }
    }
  }
}

async function testByokUnknownProviderHintFailsClosedPublicly() {
  const saved = Object.fromEntries(providerEnvKeys.map(key => [key, process.env[key]]))
  const savedFetch = globalThis.fetch
  for (const key of providerEnvKeys) {
    delete process.env[key]
  }
  process.env.OMNI_BYOK_SESSION_MODE = 'true'
  process.env.OMNI_BYOK_PROVIDER = 'unknown-provider'
  process.env.OMNI_BYOK_FAIL_CLOSED = 'true'
  process.env.GROQ_API_KEY = 'sk-test-system-groq'
  let fetchCalls = 0
  globalThis.fetch = async () => {
    fetchCalls += 1
    throw new Error('fetch must not be called for unknown BYOK provider')
  }
  try {
    const engine = new QueryEngineAuthority()
    const result = await engine.submitMessage({
      message: 'Explique este projeto em uma frase curta.',
      memoryContext: {},
      history: [],
      summary: '',
      capabilities: [],
      session: { session_id: 'truth-contract-byok-unknown-provider' },
      cwd: process.cwd(),
    })
    const serialized = JSON.stringify(result)

    assert.equal(fetchCalls, 0)
    assert.equal(result.selected_provider, 'unknown-provider')
    assert.equal(result.executed_provider, '')
    assert.equal(result.provider_failed, true)
    assert.equal(result.failure_class, 'byok_execution_failed')
    assert.equal(result.failure_reason, 'byok_credentials_incomplete')
    assert.equal(result.response.includes('byok_session'), true)
    assert.equal(result.runtime_truth.llm_provider_attempted, false)
    assert.equal(serialized.includes('sk-test-system-groq'), false)
    assert.equal(serialized.includes('Authorization'), false)
    assert.equal(serialized.includes('raw request'), false)
    assert.equal(serialized.includes('raw response'), false)
    assert.equal(serialized.includes('stack'), false)
  } finally {
    globalThis.fetch = savedFetch
    for (const [key, value] of Object.entries(saved)) {
      if (value === undefined) {
        delete process.env[key]
      } else {
        process.env[key] = value
      }
    }
  }
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
console.log('runtime truth contract: js checks passed')
