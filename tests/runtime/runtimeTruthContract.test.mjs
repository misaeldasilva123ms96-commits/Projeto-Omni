import assert from 'node:assert/strict'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const {
  QueryEngineAuthority,
  RUNTIME_TRUTH_MODES,
  buildRuntimeTruth,
  inferIntentWithSource,
} = require('../../core/brain/queryEngineAuthority.js')

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

await testGreetingMatcherTruth()
testIntentWrapper()
testTruthHelperModes()
console.log('runtime truth contract: js checks passed')
