import assert from 'node:assert/strict'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const {
  TOKEN_COMPRESSION_MODES,
  compressTokenPayload,
  normalizeTokenCompressionMode,
} = require('../../core/brain/tokenCompressionPipeline.js')
const {
  RUNTIME_TRUTH_MODES,
  buildRuntimeTruth,
  inferIntentWithSource,
} = require('../../core/brain/queryEngineAuthority.js')

function repeatedLog(line, count) {
  return Array.from({ length: count }, () => line).join('\n')
}

function assertNoSecretOrRawContent(value, fragments) {
  const serialized = JSON.stringify(value)
  for (const fragment of fragments) {
    assert.equal(serialized.includes(fragment), false, `public metadata leaked fragment: ${fragment}`)
  }
}

function testModesAreStable() {
  assert.deepEqual(TOKEN_COMPRESSION_MODES, ['off', 'lite', 'standard', 'aggressive'])
  assert.equal(normalizeTokenCompressionMode('standard'), 'standard')
  assert.equal(normalizeTokenCompressionMode('unknown'), 'off')
}

function testOffModeSkipsCompression() {
  const content = 'line one\nline two'
  const result = compressTokenPayload({
    content,
    payloadType: 'long_log',
    mode: 'off',
  })

  assert.equal(result.ok, true)
  assert.equal(result.compressedText, content)
  assert.equal(result.runtimeTruth.compression_mode, 'off')
  assert.equal(result.runtimeTruth.skipped_reason, 'mode_off')
  assert.equal(result.runtimeTruth.compression_ratio, 1)
}

function testLiteStandardAndAggressiveCompression() {
  const content = `${repeatedLog('WARN retryable worker timeout', 80)}\n\n\n${repeatedLog('INFO recovery complete', 30)}`
  const lite = compressTokenPayload({ content, payloadType: 'long_log', mode: 'lite' })
  const standard = compressTokenPayload({ content, payloadType: 'test_output', mode: 'standard' })
  const aggressive = compressTokenPayload({ content, payloadType: 'large_diff', mode: 'aggressive' })

  assert.equal(lite.ok, true)
  assert.equal(standard.ok, true)
  assert.equal(aggressive.ok, true)
  assert.equal(lite.runtimeTruth.strategy_used, 'lite_blankline_dedupe')
  assert.equal(standard.runtimeTruth.strategy_used, 'standard_head_tail_dedupe')
  assert.equal(aggressive.runtimeTruth.strategy_used, 'aggressive_head_tail_dedupe')
  assert.ok(lite.runtimeTruth.output_size < lite.runtimeTruth.input_size)
  assert.ok(standard.runtimeTruth.output_size < lite.runtimeTruth.output_size)
  assert.ok(aggressive.runtimeTruth.output_size <= standard.runtimeTruth.output_size)
}

function testRedactionBeforeCompression() {
  const content = [
    'test failed for owner@example.invalid',
    'C:\\Users\\Misael\\private\\fixture.txt',
    repeatedLog('same message', 20),
  ].join('\n')
  const result = compressTokenPayload({
    content,
    payloadType: 'test_output',
    mode: 'standard',
  })

  assert.equal(result.ok, true)
  assert.equal(result.runtimeTruth.redaction_applied, true)
  assert.equal(result.compressedText.includes('owner@example.invalid'), false)
  assert.equal(result.compressedText.includes('C:\\Users\\Misael'), false)
}

function testSecretContentFailsClosed() {
  const secret = 'sk-test-token-compression-secret'
  const result = compressTokenPayload({
    content: `OPENAI_API_KEY=${secret}\n${repeatedLog('safe line', 10)}`,
    payloadType: 'long_log',
    mode: 'standard',
  })

  assert.equal(result.ok, false)
  assert.equal(result.compressedText, '')
  assert.equal(result.runtimeTruth.fail_closed_reason, 'secret_indicator_detected')
  assertNoSecretOrRawContent(result.runtimeTruth, [secret, 'OPENAI_API_KEY'])
}

function testPolicyUnsafeTypeAndAuditabilityFailClosed() {
  const content = repeatedLog('safe line', 12)
  const policyBlocked = compressTokenPayload({
    content,
    payloadType: 'long_log',
    mode: 'lite',
    policyResult: 'block',
  })
  const unsafeType = compressTokenPayload({
    content,
    payloadType: 'headers',
    mode: 'lite',
  })
  const auditRisk = compressTokenPayload({
    content,
    payloadType: 'text_history',
    mode: 'lite',
    preserveAuditability: false,
  })

  assert.equal(policyBlocked.ok, false)
  assert.equal(policyBlocked.runtimeTruth.fail_closed_reason, 'policy_blocked')
  assert.equal(unsafeType.ok, false)
  assert.equal(unsafeType.runtimeTruth.fail_closed_reason, 'unsafe_payload_type')
  assert.equal(auditRisk.ok, false)
  assert.equal(auditRisk.runtimeTruth.fail_closed_reason, 'auditability_risk')
}

function testRuntimeTruthMetadataIsPublicOnly() {
  const compression = compressTokenPayload({
    content: repeatedLog('safe output', 50),
    payloadType: 'test_output',
    mode: 'standard',
  })
  const truth = buildRuntimeTruth({
    runtimeMode: RUNTIME_TRUTH_MODES.TOOL_EXECUTED,
    runtimeReason: 'node_local_tool_run',
    intentInfo: inferIntentWithSource('rode os testes'),
    toolInvoked: true,
    toolExecuted: true,
    toolStatus: 'executed',
    tokenCompression: {
      ...compression.runtimeTruth,
      api_key: 'sk-test-token-compression-secret',
      raw_payload: 'safe output',
      headers: { Authorization: 'Bearer sk-test-token-compression-secret' },
      stack: 'stack trace with sensitive path',
    },
  })

  assert.equal(truth.token_compression.compression_mode, 'standard')
  assert.equal(truth.token_compression.strategy_used, 'standard_head_tail_dedupe')
  assert.equal(typeof truth.token_compression.input_size, 'number')
  assertNoSecretOrRawContent(truth, [
    'sk-test-token-compression-secret',
    'Authorization',
    'Bearer',
    'raw_payload',
    'safe output',
    'stack trace',
  ])
}

testModesAreStable()
testOffModeSkipsCompression()
testLiteStandardAndAggressiveCompression()
testRedactionBeforeCompression()
testSecretContentFailsClosed()
testPolicyUnsafeTypeAndAuditabilityFailClosed()
testRuntimeTruthMetadataIsPublicOnly()

console.log('token compression pipeline: js checks passed')
