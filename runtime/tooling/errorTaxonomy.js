const OMNI_ERROR_CODE = Object.freeze({
  SHELL_TOOL_BLOCKED: 'SHELL_TOOL_BLOCKED',
  TOOL_BLOCKED_PUBLIC_DEMO: 'TOOL_BLOCKED_PUBLIC_DEMO',
  TOOL_BLOCKED_BY_GOVERNANCE: 'TOOL_BLOCKED_BY_GOVERNANCE',
  TOOL_APPROVAL_REQUIRED: 'TOOL_APPROVAL_REQUIRED',
  SPECIALIST_FAILED: 'SPECIALIST_FAILED',
  MATCHER_SHORTCUT_USED: 'MATCHER_SHORTCUT_USED',
  RULE_BASED_INTENT_USED: 'RULE_BASED_INTENT_USED',
  PROVIDER_UNAVAILABLE: 'PROVIDER_UNAVAILABLE',
  NODE_EMPTY_RESPONSE: 'NODE_EMPTY_RESPONSE',
  NODE_RUNNER_FAILED: 'NODE_RUNNER_FAILED',
  PYTHON_ORCHESTRATOR_FAILED: 'PYTHON_ORCHESTRATOR_FAILED',
  MEMORY_STORE_UNAVAILABLE: 'MEMORY_STORE_UNAVAILABLE',
  SUPABASE_NOT_CONFIGURED: 'SUPABASE_NOT_CONFIGURED',
  TIMEOUT: 'TIMEOUT',
  INTERNAL_ERROR_REDACTED: 'INTERNAL_ERROR_REDACTED',
});

const ERROR_MESSAGES = Object.freeze({
  [OMNI_ERROR_CODE.SHELL_TOOL_BLOCKED]: 'Shell execution is disabled by policy.',
  [OMNI_ERROR_CODE.TOOL_BLOCKED_PUBLIC_DEMO]: 'Tool execution is blocked in public demo mode.',
  [OMNI_ERROR_CODE.TOOL_BLOCKED_BY_GOVERNANCE]: 'Tool execution was blocked by governance policy.',
  [OMNI_ERROR_CODE.TOOL_APPROVAL_REQUIRED]: 'Tool execution requires explicit approval before running.',
  [OMNI_ERROR_CODE.SPECIALIST_FAILED]: 'Specialist execution failed. Using fallback.',
  [OMNI_ERROR_CODE.MATCHER_SHORTCUT_USED]: 'Responded using a local pattern matcher. No AI provider was used.',
  [OMNI_ERROR_CODE.RULE_BASED_INTENT_USED]: 'Intent was classified by deterministic rules.',
  [OMNI_ERROR_CODE.PROVIDER_UNAVAILABLE]: 'No usable AI provider was available for this request.',
  [OMNI_ERROR_CODE.NODE_EMPTY_RESPONSE]: 'Node runtime returned an empty response.',
  [OMNI_ERROR_CODE.NODE_RUNNER_FAILED]: 'Node runtime did not complete successfully.',
  [OMNI_ERROR_CODE.PYTHON_ORCHESTRATOR_FAILED]: 'Python orchestrator could not complete the request.',
  [OMNI_ERROR_CODE.MEMORY_STORE_UNAVAILABLE]: 'Memory store is unavailable for this request.',
  [OMNI_ERROR_CODE.SUPABASE_NOT_CONFIGURED]: 'Supabase is not configured for this environment.',
  [OMNI_ERROR_CODE.TIMEOUT]: 'The operation timed out.',
  [OMNI_ERROR_CODE.INTERNAL_ERROR_REDACTED]: 'An internal runtime error occurred and details were redacted.',
});

const ERROR_SEVERITY = Object.freeze({
  [OMNI_ERROR_CODE.SHELL_TOOL_BLOCKED]: 'blocked',
  [OMNI_ERROR_CODE.TOOL_BLOCKED_PUBLIC_DEMO]: 'blocked',
  [OMNI_ERROR_CODE.TOOL_BLOCKED_BY_GOVERNANCE]: 'blocked',
  [OMNI_ERROR_CODE.TOOL_APPROVAL_REQUIRED]: 'blocked',
  [OMNI_ERROR_CODE.SPECIALIST_FAILED]: 'degraded',
  [OMNI_ERROR_CODE.MATCHER_SHORTCUT_USED]: 'info',
  [OMNI_ERROR_CODE.RULE_BASED_INTENT_USED]: 'info',
  [OMNI_ERROR_CODE.PROVIDER_UNAVAILABLE]: 'degraded',
  [OMNI_ERROR_CODE.NODE_EMPTY_RESPONSE]: 'degraded',
  [OMNI_ERROR_CODE.NODE_RUNNER_FAILED]: 'degraded',
  [OMNI_ERROR_CODE.PYTHON_ORCHESTRATOR_FAILED]: 'error',
  [OMNI_ERROR_CODE.MEMORY_STORE_UNAVAILABLE]: 'degraded',
  [OMNI_ERROR_CODE.SUPABASE_NOT_CONFIGURED]: 'info',
  [OMNI_ERROR_CODE.TIMEOUT]: 'error',
  [OMNI_ERROR_CODE.INTERNAL_ERROR_REDACTED]: 'critical',
});

const ERROR_RETRYABLE = Object.freeze({
  [OMNI_ERROR_CODE.SHELL_TOOL_BLOCKED]: false,
  [OMNI_ERROR_CODE.TOOL_BLOCKED_PUBLIC_DEMO]: false,
  [OMNI_ERROR_CODE.TOOL_BLOCKED_BY_GOVERNANCE]: false,
  [OMNI_ERROR_CODE.TOOL_APPROVAL_REQUIRED]: false,
  [OMNI_ERROR_CODE.SPECIALIST_FAILED]: true,
  [OMNI_ERROR_CODE.MATCHER_SHORTCUT_USED]: false,
  [OMNI_ERROR_CODE.RULE_BASED_INTENT_USED]: false,
  [OMNI_ERROR_CODE.PROVIDER_UNAVAILABLE]: true,
  [OMNI_ERROR_CODE.NODE_EMPTY_RESPONSE]: true,
  [OMNI_ERROR_CODE.NODE_RUNNER_FAILED]: true,
  [OMNI_ERROR_CODE.PYTHON_ORCHESTRATOR_FAILED]: true,
  [OMNI_ERROR_CODE.MEMORY_STORE_UNAVAILABLE]: true,
  [OMNI_ERROR_CODE.SUPABASE_NOT_CONFIGURED]: false,
  [OMNI_ERROR_CODE.TIMEOUT]: true,
  [OMNI_ERROR_CODE.INTERNAL_ERROR_REDACTED]: false,
});

function normalizeCode(code) {
  const value = String(code || '').trim();
  return Object.prototype.hasOwnProperty.call(ERROR_MESSAGES, value)
    ? value
    : OMNI_ERROR_CODE.INTERNAL_ERROR_REDACTED;
}

function buildPublicError(code, overrides = {}) {
  const normalized = normalizeCode(code);
  return {
    error_public_code: normalized,
    error_public_message: overrides.error_public_message || ERROR_MESSAGES[normalized],
    severity: overrides.severity || ERROR_SEVERITY[normalized],
    retryable: typeof overrides.retryable === 'boolean' ? overrides.retryable : ERROR_RETRYABLE[normalized],
    internal_error_redacted: true,
  };
}

function normalizePublicError(errorOrCode) {
  if (errorOrCode && typeof errorOrCode === 'object') {
    return buildPublicError(errorOrCode.error_public_code || errorOrCode.code);
  }
  return buildPublicError(errorOrCode);
}

module.exports = {
  ERROR_MESSAGES,
  ERROR_RETRYABLE,
  ERROR_SEVERITY,
  OMNI_ERROR_CODE,
  buildPublicError,
  normalizePublicError,
};
