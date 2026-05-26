import type { PuterManualHarnessResult } from './freeModePuterManualHarness'

export const PUTER_AUTH_RETRY_STATE_VERSION = 'puter_auth_retry_state_v1'

export type PuterAuthRetryStatus =
  | 'not_invoked'
  | 'runtime_not_loaded'
  | 'auth_required'
  | 'auth_completed'
  | 'retry_not_allowed'
  | 'retry_ready'
  | 'retry_invoked'
  | 'provider_consent_or_auth_pending'
  | 'provider_failed_safe'
  | 'provider_succeeded_sanitized'

export type PuterAuthRetryRuntimeTruth = {
  auth_completed: boolean
  retry_allowed: boolean
  retry_attempted: boolean
  provider_attempted: boolean
  provider_succeeded: boolean
  provider_failed_reason: string
  raw_auth_payload_exposed: false
  raw_provider_payload_exposed: false
  sanitized_output_present: boolean
}

export type PuterAuthRetryState = {
  state_version: typeof PUTER_AUTH_RETRY_STATE_VERSION
  status: PuterAuthRetryStatus
  reason: string
  user_message: string
  sanitized_output: string
  runtime_truth: PuterAuthRetryRuntimeTruth
}

export type PuterAuthRetryStateInput = {
  authCompleted?: boolean
  providerAttempted?: boolean
  providerFailedReason?: string
  providerSucceeded?: boolean
  retryAllowed?: boolean
  retryAttempted?: boolean
  sanitizedOutput?: string
  status?: PuterAuthRetryStatus
}

const RETRY_STATE_KEYS = [
  'state_version',
  'status',
  'reason',
  'user_message',
  'sanitized_output',
  'runtime_truth',
] as const

const RETRY_RUNTIME_TRUTH_KEYS = [
  'auth_completed',
  'retry_allowed',
  'retry_attempted',
  'provider_attempted',
  'provider_succeeded',
  'provider_failed_reason',
  'raw_auth_payload_exposed',
  'raw_provider_payload_exposed',
  'sanitized_output_present',
] as const

export function createPuterAuthRetryState({
  authCompleted = false,
  providerAttempted = false,
  providerFailedReason,
  providerSucceeded = false,
  retryAllowed,
  retryAttempted = false,
  sanitizedOutput = '',
  status,
}: PuterAuthRetryStateInput = {}): PuterAuthRetryState {
  const resolvedStatus = status ?? (authCompleted ? 'retry_ready' : 'auth_required')
  const safeOutput = sanitizeVisibleText(sanitizedOutput)
  const safeProviderReason = providerFailedReason
    ? safeReason(providerFailedReason)
    : statusToProviderReason(resolvedStatus)

  return {
    state_version: PUTER_AUTH_RETRY_STATE_VERSION,
    status: resolvedStatus,
    reason: resolvedStatus,
    user_message: statusToUserMessage(resolvedStatus),
    sanitized_output: safeOutput,
    runtime_truth: {
      auth_completed: authCompleted,
      retry_allowed: retryAllowed ?? resolvedStatus === 'retry_ready',
      retry_attempted: retryAttempted,
      provider_attempted: providerAttempted,
      provider_succeeded: providerSucceeded,
      provider_failed_reason: safeProviderReason,
      raw_auth_payload_exposed: false,
      raw_provider_payload_exposed: false,
      sanitized_output_present: safeOutput.length > 0,
    },
  }
}

export function retryStateFromManualHarnessResult(
  result: PuterManualHarnessResult,
  authCompleted: boolean,
): PuterAuthRetryState {
  if (!authCompleted) {
    return createPuterAuthRetryState({
      authCompleted: false,
      retryAllowed: false,
      retryAttempted: true,
      status: 'retry_not_allowed',
    })
  }

  if (result.ok) {
    return createPuterAuthRetryState({
      authCompleted: true,
      providerAttempted: true,
      providerSucceeded: true,
      retryAllowed: true,
      retryAttempted: true,
      sanitizedOutput: result.sanitized_text,
      status: 'provider_succeeded_sanitized',
    })
  }

  const providerAttempted = result.reason === 'puter_call_failed'
    || result.reason === 'provider_consent_or_auth_pending'

  return createPuterAuthRetryState({
    authCompleted: true,
    providerAttempted,
    providerFailedReason: result.reason,
    providerSucceeded: false,
    retryAllowed: true,
    retryAttempted: true,
    status: result.reason === 'provider_consent_or_auth_pending'
      ? 'provider_consent_or_auth_pending'
      : 'provider_failed_safe',
  })
}

export function isPuterAuthRetryState(value: unknown): value is PuterAuthRetryState {
  if (!isRecord(value) || !isRecord(value.runtime_truth)) {
    return false
  }

  return sameKeySet(Object.keys(value).sort(), [...RETRY_STATE_KEYS].sort())
    && sameKeySet(Object.keys(value.runtime_truth).sort(), [...RETRY_RUNTIME_TRUTH_KEYS].sort())
}

function statusToProviderReason(status: PuterAuthRetryStatus): string {
  if (status === 'provider_failed_safe') {
    return 'provider_failed_safe'
  }

  if (status === 'provider_consent_or_auth_pending') {
    return 'provider_consent_or_auth_pending'
  }

  return 'none'
}

function statusToUserMessage(status: PuterAuthRetryStatus): string {
  switch (status) {
    case 'not_invoked':
      return 'Retry has not been requested.'
    case 'runtime_not_loaded':
      return 'Load the Puter runtime before retrying.'
    case 'auth_required':
      return 'Complete Puter auth or consent before retrying.'
    case 'auth_completed':
      return 'Puter auth or consent completed.'
    case 'retry_not_allowed':
      return 'Retry is not allowed yet.'
    case 'retry_ready':
      return 'Retry is ready for a manual click.'
    case 'retry_invoked':
      return 'Retry was manually invoked.'
    case 'provider_consent_or_auth_pending':
      return 'Provider consent or auth is still pending.'
    case 'provider_failed_safe':
      return 'Provider failed safely.'
    case 'provider_succeeded_sanitized':
      return 'Provider returned a sanitized result.'
  }
}

function sanitizeVisibleText(value: string): string {
  return String(value || '').replace(/\bsk-(?:proj-)?[A-Za-z0-9_-]{8,}\b/g, '[redacted]').trim()
}

function safeReason(value: string): string {
  const normalized = String(value || '').trim().toLowerCase()
  return /^[a-z0-9_]+$/.test(normalized) ? normalized : 'provider_failed_safe'
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function sameKeySet(left: string[], right: string[]): boolean {
  return left.length === right.length && left.every((key, index) => key === right[index])
}
