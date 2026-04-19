import assert from 'node:assert/strict';
import { buildExecutionProvenance, readPolicyHintEnvelope, attachProvenanceMetadata } from '../../core/brain/executionProvenance.js';

const saved = { ...process.env };

function testMatcherProvenance() {
  delete process.env.OMNI_POLICY_HINT_JSON;
  const p = buildExecutionProvenance({
    provider: { name: 'local-heuristic', model: 'native-heuristic' },
    toolCalls: [],
    strategyActual: 'conversational_matcher',
    executionMode: 'matcher_shortcut',
    provenanceSource: 'matcher_shortcut',
    latencyBreakdownMs: { authority_ms: 12 },
  });
  assert.equal(p.provider_actual, 'local-heuristic');
  assert.equal(p.tool_count, 0);
  assert.equal(p.policy_match, null);
}

function testPolicyMatchWhenHintActive() {
  process.env.OMNI_POLICY_HINT_JSON = JSON.stringify({
    recommended_provider: 'openai',
    baseline_provider: 'openai',
    shadow_only: false,
  });
  const hint = readPolicyHintEnvelope();
  assert.ok(hint);
  assert.equal(hint.recommended, 'openai');
  const p = buildExecutionProvenance({
    provider: { name: 'openai', model: 'gpt-4.1-mini' },
    toolCalls: ['read_file'],
    executionMode: 'live',
    policyHintEnvelope: hint,
  });
  assert.equal(p.policy_match, true);
  assert.equal(p.policy_applied, true);
  Object.assign(process.env, saved);
  delete process.env.OMNI_POLICY_HINT_JSON;
}

function testPolicyMismatch() {
  const p = buildExecutionProvenance({
    provider: { name: 'anthropic', model: 'claude' },
    toolCalls: [],
    policyHintEnvelope: {
      recommended: 'openai',
      baseline: 'openai',
      shadow_only: false,
    },
  });
  assert.equal(p.policy_match, false);
}

function testAttachMetadata() {
  const prov = buildExecutionProvenance({
    provider: { name: 'groq', model: 'llama' },
    toolCalls: [],
  });
  const out = attachProvenanceMetadata({ response: 'ok' }, prov);
  assert.ok(out.metadata);
  assert.equal(out.metadata.execution_provenance.provider_actual, 'groq');
}

testMatcherProvenance();
testPolicyMatchWhenHintActive();
testPolicyMismatch();
testAttachMetadata();
console.log('executionProvenance.test.mjs: ok');
