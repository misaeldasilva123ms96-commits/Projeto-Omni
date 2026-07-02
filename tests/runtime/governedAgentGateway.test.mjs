import assert from 'node:assert/strict'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const {
  SAFE_AGENT_CAPABILITIES,
  SENSITIVE_AGENT_CAPABILITIES,
  evaluateGovernedAgentRequest,
} = require('../../core/brain/governedAgentGateway.js')
const {
  RUNTIME_TRUTH_MODES,
  buildRuntimeTruth,
  inferIntentWithSource,
} = require('../../core/brain/queryEngineAuthority.js')

const fixedNow = new Date('2026-07-02T00:00:00.000Z')

function assertNoSecret(value, fragments = []) {
  const serialized = JSON.stringify(value)
  for (const fragment of [
    'sk-test-governed-agent-secret',
    'Authorization',
    'Bearer',
    'OPENAI_API_KEY',
    'raw_prompt',
    'raw_payload',
    'stack trace',
    ...fragments,
  ]) {
    assert.equal(serialized.includes(fragment), false, `leaked public fragment: ${fragment}`)
  }
}

function evaluate(requestedCapability, extra = {}) {
  return evaluateGovernedAgentRequest({
    agent: {
      agent_id: 'agent-runtime-1',
      agent_name: 'Runtime Inspector',
      agent_type: 'internal_specialist',
      ...(extra.agent || {}),
    },
    requestedCapability,
    context: extra.context || { source: 'runtime_truth_public' },
    policyResult: extra.policyResult ?? 'allow',
    now: fixedNow,
  })
}

function testSafeCapabilitiesAllowed() {
  for (const capability of ['read_safe', 'summarize', 'inspect_runtime', 'inspect_docs', 'create_report']) {
    const result = evaluate(capability)
    assert.equal(result.ok, true)
    assert.equal(result.decision, 'allow')
    assert.equal(result.decision_reason, 'safe_capability_allowed')
    assert.equal(result.policy_result, 'allow')
    assert.equal(result.risk_level, 'low')
    assert.equal(result.runtimeTruth.requested_capability, capability)
  }
}

function testProposePatchIsProposalOnly() {
  const result = evaluate('propose_patch')
  assert.equal(result.ok, true)
  assert.equal(result.decision, 'allow')
  assert.equal(result.tool_scope, 'proposal_only')
  assert.equal(result.decision_reason, 'proposal_only_capability_allowed')
  assert.equal(result.risk_level, 'medium')
}

function testSensitiveCapabilitiesDeniedByDefault() {
  for (const capability of SENSITIVE_AGENT_CAPABILITIES) {
    const result = evaluate(capability)
    assert.equal(result.ok, false)
    assert.equal(result.decision, 'deny')
    assert.equal(result.decision_reason, 'sensitive_capability_blocked')
    assert.equal(result.risk_level, 'high')
    assert.ok(result.denied_capabilities.includes(capability))
  }
}

function testUnknownCapabilityDenied() {
  const result = evaluate('mcp_remote_execute')
  assert.equal(result.ok, false)
  assert.equal(result.decision, 'deny')
  assert.equal(result.decision_reason, 'unknown_capability')
}

function testPolicyBlockFailsClosed() {
  const result = evaluate('read_safe', { policyResult: 'block' })
  assert.equal(result.ok, false)
  assert.equal(result.decision, 'deny')
  assert.equal(result.decision_reason, 'policy_blocked')
  assert.equal(result.policy_result, 'block')
  assert.equal(result.risk_level, 'high')
}

function testSecretIndicatorFailsClosedAndIsNotEchoed() {
  const result = evaluate('read_safe', {
    agent: {
      agent_name: 'Bearer sk-test-governed-agent-secret',
    },
    context: {
      raw_prompt: 'OPENAI_API_KEY=sk-test-governed-agent-secret',
      headers: { Authorization: 'Bearer sk-test-governed-agent-secret' },
      stack: 'stack trace should not render',
    },
  })

  assert.equal(result.ok, false)
  assert.equal(result.decision, 'deny')
  assert.equal(result.decision_reason, 'secret_indicator_detected')
  assertNoSecret(result)
}

function testRuntimeTruthIsSanitized() {
  const gateway = evaluate('inspect_runtime')
  const truth = buildRuntimeTruth({
    runtimeMode: RUNTIME_TRUTH_MODES.PARTIAL_COGNITIVE,
    runtimeReason: 'governed_agent_gateway_decision',
    intentInfo: inferIntentWithSource('inspecione runtime truth'),
    governedAgentGateway: {
      ...gateway.runtimeTruth,
      api_key: 'sk-test-governed-agent-secret',
      headers: { Authorization: 'Bearer sk-test-governed-agent-secret' },
      raw_prompt: 'prompt with sk-test-governed-agent-secret',
      raw_payload: 'payload with secret',
      stack: 'stack trace with secret',
    },
  })

  assert.equal(truth.governed_agent_gateway.agent_id, 'agent-runtime-1')
  assert.equal(truth.governed_agent_gateway.agent_type, 'internal_specialist')
  assert.equal(truth.governed_agent_gateway.requested_capability, 'inspect_runtime')
  assert.equal(truth.governed_agent_gateway.decision, 'allow')
  assert.equal(truth.governed_agent_gateway.policy_result, 'allow')
  assert.deepEqual(
    Object.keys(truth.governed_agent_gateway).sort(),
    [
      'agent_id',
      'agent_type',
      'created_at',
      'decision',
      'decision_reason',
      'denied_capabilities',
      'policy_result',
      'requested_capability',
      'risk_level',
    ].sort(),
  )
  assertNoSecret(truth)
}

assert.deepEqual(SAFE_AGENT_CAPABILITIES, [
  'read_safe',
  'summarize',
  'inspect_runtime',
  'inspect_docs',
  'propose_patch',
  'create_report',
])

testSafeCapabilitiesAllowed()
testProposePatchIsProposalOnly()
testSensitiveCapabilitiesDeniedByDefault()
testUnknownCapabilityDenied()
testPolicyBlockFailsClosed()
testSecretIndicatorFailsClosedAndIsNotEchoed()
testRuntimeTruthIsSanitized()

console.log('governed agent gateway: js checks passed')
