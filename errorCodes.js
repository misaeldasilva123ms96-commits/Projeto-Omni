/**
 * Centralized public error codes — Phase 8 (Roadmap Oficial v2.1).
 *
 * Rules:
 * - All public-facing error codes are defined here.
 * - Codes are uppercase snake_case strings.
 * - error_public_message must never contain internal details.
 * - severity: 'fatal' | 'degraded' | 'warning' | 'info'
 * - retryable: true if the client may retry the same request.
 */

/** @typedef {{ code: string, message: string, severity: string, retryable: boolean }} PublicErrorSpec */

/** @type {Record<string, PublicErrorSpec>} */
const PUBLIC_ERROR_CODES = {
  SHELL_TOOL_BLOCKED: {
    code: 'SHELL_TOOL_BLOCKED',
    message: 'Shell execution is disabled by policy.',
    severity: 'warning',
    retryable: false,
  },
  TOOL_BLOCKED_PUBLIC_DEMO: {
    code: 'TOOL_BLOCKED_PUBLIC_DEMO',
    message: 'This tool is not available in public demo mode.',
    severity: 'warning',
    retryable: false,
  },
  TOOL_BLOCKED_BY_GOVERNANCE: {
    code: 'TOOL_BLOCKED_BY_GOVERNANCE',
    message: 'Tool execution was blocked by governance policy.',
    severity: 'warning',
    retryable: false,
  },
  TOOL_APPROVAL_REQUIRED: {
    code: 'TOOL_APPROVAL_REQUIRED',
    message: 'This operation requires explicit approval before execution.',
    severity: 'warning',
    retryable: false,
  },
  SPECIALIST_FAILED: {
    code: 'SPECIALIST_FAILED',
    message: 'Specialist execution failed. Using fallback.',
    severity: 'degraded',
    retryable: true,
  },
  PROVIDER_UNAVAILABLE: {
    code: 'PROVIDER_UNAVAILABLE',
    message: 'No AI provider is available at this time.',
    severity: 'degraded',
    retryable: true,
  },
  NODE_EMPTY_RESPONSE: {
    code: 'NODE_EMPTY_RESPONSE',
    message: 'The Node runtime did not return a usable response.',
    severity: 'degraded',
    retryable: true,
  },
  NODE_RUNNER_FAILED: {
    code: 'NODE_RUNNER_FAILED',
    message: 'The Node runtime failed to process the request.',
    severity: 'degraded',
    retryable: true,
  },
  PYTHON_ORCHESTRATOR_FAILED: {
    code: 'PYTHON_ORCHESTRATOR_FAILED',
    message: 'The Python orchestrator failed to process the request.',
    severity: 'degraded',
    retryable: true,
  },
  MATCHER_SHORTCUT_USED: {
    code: 'MATCHER_SHORTCUT_USED',
    message: 'Responded using a local pattern matcher. No AI provider was used.',
    severity: 'info',
    retryable: false,
  },
  RULE_BASED_INTENT_USED: {
    code: 'RULE_BASED_INTENT_USED',
    message: 'Intent was classified by rule-based heuristics, not an AI model.',
    severity: 'info',
    retryable: false,
  },
  MEMORY_STORE_UNAVAILABLE: {
    code: 'MEMORY_STORE_UNAVAILABLE',
    message: 'Memory store is unavailable. Responses may lack context.',
    severity: 'degraded',
    retryable: true,
  },
  SUPABASE_NOT_CONFIGURED: {
    code: 'SUPABASE_NOT_CONFIGURED',
    message: 'Supabase is not configured. Persistence features are unavailable.',
    severity: 'info',
    retryable: false,
  },
  TIMEOUT: {
    code: 'TIMEOUT',
    message: 'The operation timed out.',
    severity: 'degraded',
    retryable: true,
  },
  INTERNAL_ERROR_REDACTED: {
    code: 'INTERNAL_ERROR_REDACTED',
    message: 'An internal error occurred. Details have been redacted for security.',
    severity: 'fatal',
    retryable: false,
  },
  INPUT_TOO_LONG: {
    code: 'INPUT_TOO_LONG',
    message: 'The message exceeds the maximum allowed length.',
    severity: 'warning',
    retryable: false,
  },
  INPUT_INVALID: {
    code: 'INPUT_INVALID',
    message: 'The input contains invalid characters or format.',
    severity: 'warning',
    retryable: false,
  },
  RATE_LIMITED: {
    code: 'RATE_LIMITED',
    message: 'Too many requests. Please wait before sending another message.',
    severity: 'warning',
    retryable: true,
  },
};

/**
 * Build a standardized public error response object.
 * @param {string} code - key from PUBLIC_ERROR_CODES
 * @param {object} [overrides] - optional field overrides
 * @returns {object}
 */
function buildPublicError(code, overrides = {}) {
  const spec = PUBLIC_ERROR_CODES[code] || PUBLIC_ERROR_CODES.INTERNAL_ERROR_REDACTED;
  return {
    ok: false,
    error_public_code: spec.code,
    error_public_message: overrides.message || spec.message,
    severity: overrides.severity || spec.severity,
    retryable: overrides.retryable !== undefined ? overrides.retryable : spec.retryable,
    internal_error_redacted: true,
  };
}

module.exports = {
  PUBLIC_ERROR_CODES,
  buildPublicError,
};
