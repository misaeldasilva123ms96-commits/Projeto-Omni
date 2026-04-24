/**
 * Phase 42 — canonical execution provenance for Node → Python bridge.
 * Field names must stay aligned with `brain.runtime.provenance.provenance_models`.
 */

'use strict';

function readPolicyHintEnvelope() {
  try {
    const raw = process.env.OMNI_POLICY_HINT_JSON;
    if (!raw || !String(raw).trim()) {
      return null;
    }
    const h = JSON.parse(String(raw));
    if (!h || typeof h !== 'object') {
      return null;
    }
    return {
      recommended: String(h.recommended_provider || '').trim().toLowerCase(),
      baseline: String(h.baseline_provider || '').trim().toLowerCase(),
      shadow_only: Boolean(h.shadow_only),
    };
  } catch (_) {
    return null;
  }
}

/**
 * @param {object} params
 * @returns {object} execution_provenance payload (plain JSON-serializable)
 */
function buildExecutionProvenance(params = {}) {
  const {
    provider,
    providerRequested = '',
    toolCalls = [],
    strategyActual = '',
    executionMode = '',
    fallbackPath = '',
    nodeRuntimePath = 'queryEngineAuthority',
    latencyBreakdownMs = {},
    usageTokensInput = null,
    usageTokensOutput = null,
    costEstimate = null,
    providerFailed = false,
    failureClass = '',
    failureReason = '',
    providerDiagnostics = [],
    providerFallbackOccurred = false,
    noProviderAvailable = false,
    provenanceSource = 'node_authority',
    provenanceConfidence = 0.75,
    policyHintEnvelope = null,
  } = params;

  const actualName = provider && typeof provider === 'object'
    ? String(provider.name || '').trim().toLowerCase()
    : String(provider || '').trim().toLowerCase();
  const actualModel = provider && typeof provider === 'object'
    ? String(provider.model || '').trim()
    : '';

  const hint = policyHintEnvelope || readPolicyHintEnvelope();
  const recommended = hint && hint.recommended ? hint.recommended : '';
  const baseline = hint && hint.baseline ? hint.baseline : '';
  const shadowOnly = hint ? Boolean(hint.shadow_only) : true;

  const policyApplied = Boolean(hint && !shadowOnly && recommended);
  let policyMatch = null;
  if (recommended && actualName) {
    policyMatch = actualName === recommended;
  }

  const tools = Array.isArray(toolCalls)
    ? toolCalls.map(t => String(t || '').trim()).filter(Boolean).slice(0, 48)
    : [];
  const diagnostics = Array.isArray(providerDiagnostics)
    ? providerDiagnostics
      .filter(item => item && typeof item === 'object')
      .map(item => ({
        provider: String(item.provider || '').trim().toLowerCase().slice(0, 64),
        configured: Boolean(item.configured),
        available: Boolean(item.available),
        selected: Boolean(item.selected),
        attempted: Boolean(item.attempted),
        succeeded: Boolean(item.succeeded),
        failed: Boolean(item.failed),
        failure_class: item.failure_class == null ? null : String(item.failure_class || '').trim().toLowerCase().slice(0, 64),
        failure_reason: item.failure_reason == null ? null : String(item.failure_reason || '').trim().slice(0, 256),
        latency_ms: typeof item.latency_ms === 'number' && Number.isFinite(item.latency_ms)
          ? Number(item.latency_ms)
          : null,
      }))
      .slice(0, 16)
    : [];

  return {
    provider_actual: actualName,
    model_actual: actualModel.slice(0, 128),
    provider_requested: String(providerRequested || baseline || '').trim().toLowerCase().slice(0, 64),
    provider_recommended: recommended.slice(0, 64),
    strategy_actual: String(strategyActual || '').trim().slice(0, 128),
    tool_calls: tools,
    tool_count: tools.length,
    execution_mode: String(executionMode || '').trim().slice(0, 64),
    fallback_path: String(fallbackPath || '').trim().slice(0, 256),
    node_runtime_path: String(nodeRuntimePath || '').trim().slice(0, 128),
    policy_applied: policyApplied,
    policy_match: policyMatch,
    latency_breakdown_ms: latencyBreakdownMs && typeof latencyBreakdownMs === 'object' ? latencyBreakdownMs : {},
    usage_tokens_input: usageTokensInput,
    usage_tokens_output: usageTokensOutput,
    cost_estimate: costEstimate,
    provider_failed: Boolean(providerFailed),
    failure_class: String(failureClass || '').trim().toLowerCase().slice(0, 64),
    failure_reason: String(failureReason || '').trim().slice(0, 256),
    provider_diagnostics: diagnostics,
    provider_fallback_occurred: Boolean(providerFallbackOccurred),
    no_provider_available: Boolean(noProviderAvailable),
    provenance_source: String(provenanceSource || '').trim().slice(0, 64),
    provenance_confidence: Math.min(1, Math.max(0, Number(provenanceConfidence) || 0)),
  };
}

function attachProvenanceMetadata(result, provenance) {
  if (!result || typeof result !== 'object') {
    return result;
  }
  const md = { ...(result.metadata || {}) };
  md.execution_provenance = provenance;
  if (provenance.provider_actual) {
    md.provider = provenance.provider_actual;
  }
  if (provenance.model_actual) {
    md.model = provenance.model_actual;
  }
  return { ...result, metadata: md };
}

module.exports = {
  readPolicyHintEnvelope,
  buildExecutionProvenance,
  attachProvenanceMetadata,
};
