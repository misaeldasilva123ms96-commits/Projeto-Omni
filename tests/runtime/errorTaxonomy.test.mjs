import assert from 'node:assert/strict'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const {
  ERROR_MESSAGES,
  ERROR_RETRYABLE,
  ERROR_SEVERITY,
  OMNI_ERROR_CODE,
  buildPublicError,
  normalizePublicError,
} = require('../../runtime/tooling/errorTaxonomy.js')

const required = [
  'SHELL_TOOL_BLOCKED',
  'TOOL_BLOCKED_PUBLIC_DEMO',
  'TOOL_BLOCKED_BY_GOVERNANCE',
  'TOOL_APPROVAL_REQUIRED',
  'SPECIALIST_FAILED',
  'MATCHER_SHORTCUT_USED',
  'RULE_BASED_INTENT_USED',
  'PROVIDER_UNAVAILABLE',
  'NODE_EMPTY_RESPONSE',
  'NODE_RUNNER_FAILED',
  'PYTHON_ORCHESTRATOR_FAILED',
  'MEMORY_STORE_UNAVAILABLE',
  'SUPABASE_NOT_CONFIGURED',
  'TIMEOUT',
  'INTERNAL_ERROR_REDACTED',
]

for (const code of required) {
  assert.equal(OMNI_ERROR_CODE[code], code)
  assert.ok(ERROR_MESSAGES[code])
  assert.ok(['info', 'degraded', 'blocked', 'error', 'critical'].includes(ERROR_SEVERITY[code]))
  assert.equal(typeof ERROR_RETRYABLE[code], 'boolean')
}

assert.deepEqual(buildPublicError(OMNI_ERROR_CODE.SHELL_TOOL_BLOCKED), {
  error_public_code: 'SHELL_TOOL_BLOCKED',
  error_public_message: 'Shell execution is disabled by policy.',
  severity: 'blocked',
  retryable: false,
  internal_error_redacted: true,
})
assert.equal(normalizePublicError({ error_public_code: 'TOOL_BLOCKED_BY_GOVERNANCE' }).severity, 'blocked')
assert.equal(normalizePublicError('TIMEOUT').retryable, true)

const unknown = normalizePublicError({ code: 'NOPE', message: '/home/render/.env sk-proj-secret' })
assert.equal(unknown.error_public_code, 'INTERNAL_ERROR_REDACTED')
assert.equal(unknown.internal_error_redacted, true)
assert.equal(JSON.stringify(unknown).includes('/home/render'), false)
assert.equal(JSON.stringify(unknown).includes('sk-proj'), false)
assert.equal(buildPublicError('SPECIALIST_FAILED').severity, 'degraded')
assert.equal(buildPublicError('PROVIDER_UNAVAILABLE').retryable, true)
assert.equal(buildPublicError('NODE_EMPTY_RESPONSE').retryable, true)

console.log('runtime error taxonomy: js checks passed')
