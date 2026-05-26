export const PUTER_AUTH_CONSENT_VERSION = 'puter_auth_consent_v1'

export type PuterAuthConsentStatus =
  | 'not_invoked'
  | 'runtime_not_loaded'
  | 'auth_api_unavailable'
  | 'consent_or_auth_pending'
  | 'consent_or_auth_completed'
  | 'consent_or_auth_cancelled'
  | 'consent_or_auth_failed_safe'

export type PuterAuthConsentRuntimeTruth = {
  puter_runtime_loaded: boolean
  auth_api_available: boolean
  auth_attempted: boolean
  auth_completed: boolean
  auth_failed_reason: string
  consent_state: PuterAuthConsentStatus
  raw_auth_payload_exposed: false
  provider_attempted: false
  provider_succeeded: false
  raw_provider_payload_exposed: false
}

export type PuterAuthConsentResult = {
  ok: boolean
  status: PuterAuthConsentStatus
  reason: string
  user_message: string
  retry_allowed: boolean
  manual_action_required: boolean
  runtime_truth: PuterAuthConsentRuntimeTruth
}

type PuterAuthRuntime = {
  puter?: unknown
  window?: {
    puter?: unknown
  }
}

type PuterAuthApi = {
  signIn?: unknown
}

type PuterAuthConsentOptions = {
  runtime?: unknown
  timeoutMs?: number
}

const DEFAULT_AUTH_TIMEOUT_MS = 60_000
const RESULT_KEYS = [
  'ok',
  'status',
  'reason',
  'user_message',
  'retry_allowed',
  'manual_action_required',
  'runtime_truth',
] as const

const RUNTIME_TRUTH_KEYS = [
  'puter_runtime_loaded',
  'auth_api_available',
  'auth_attempted',
  'auth_completed',
  'auth_failed_reason',
  'consent_state',
  'raw_auth_payload_exposed',
  'provider_attempted',
  'provider_succeeded',
  'raw_provider_payload_exposed',
] as const

export function createPuterAuthConsentResult(
  status: PuterAuthConsentStatus = 'not_invoked',
  overrides: Partial<PuterAuthConsentRuntimeTruth> = {},
): PuterAuthConsentResult {
  const runtimeTruth: PuterAuthConsentRuntimeTruth = {
    puter_runtime_loaded: false,
    auth_api_available: false,
    auth_attempted: false,
    auth_completed: false,
    auth_failed_reason: statusToFailedReason(status),
    consent_state: status,
    raw_auth_payload_exposed: false,
    provider_attempted: false,
    provider_succeeded: false,
    raw_provider_payload_exposed: false,
    ...overrides,
  }

  return {
    ok: status === 'consent_or_auth_completed',
    status,
    reason: status,
    user_message: statusToUserMessage(status),
    retry_allowed: status !== 'consent_or_auth_completed' && status !== 'consent_or_auth_pending',
    manual_action_required: status !== 'consent_or_auth_completed',
    runtime_truth: runtimeTruth,
  }
}

export function isPuterRuntimeLoadedForAuth(runtime: unknown = globalThis): boolean {
  return Boolean(resolvePuterRuntime(runtime))
}

export function isPuterAuthConsentResult(value: unknown): value is PuterAuthConsentResult {
  if (!isRecord(value)) {
    return false
  }

  const keys = Object.keys(value).sort()
  if (!sameKeySet(keys, [...RESULT_KEYS].sort())) {
    return false
  }

  if (!isRecord(value.runtime_truth)) {
    return false
  }

  return sameKeySet(Object.keys(value.runtime_truth).sort(), [...RUNTIME_TRUTH_KEYS].sort())
}

export async function requestPuterAuthConsent({
  runtime = globalThis,
  timeoutMs = DEFAULT_AUTH_TIMEOUT_MS,
}: PuterAuthConsentOptions = {}): Promise<PuterAuthConsentResult> {
  const puter = resolvePuterRuntime(runtime)
  if (!puter) {
    return createPuterAuthConsentResult('runtime_not_loaded')
  }

  const auth = isRecord(puter.auth) ? (puter.auth as PuterAuthApi) : null
  if (typeof auth?.signIn !== 'function') {
    return createPuterAuthConsentResult('auth_api_unavailable', {
      puter_runtime_loaded: true,
    })
  }

  const baseTruth: Partial<PuterAuthConsentRuntimeTruth> = {
    puter_runtime_loaded: true,
    auth_api_available: true,
    auth_attempted: true,
  }

  try {
    const outcome = await withTimeout(
      Promise.resolve().then(() => (auth.signIn as () => Promise<unknown> | unknown)()),
      timeoutMs,
    )

    if (outcome === 'puter_auth_timeout') {
      return createPuterAuthConsentResult('consent_or_auth_pending', {
        ...baseTruth,
        auth_failed_reason: 'consent_or_auth_pending',
      })
    }

    return createPuterAuthConsentResult('consent_or_auth_completed', {
      ...baseTruth,
      auth_completed: true,
      auth_failed_reason: 'none',
    })
  } catch (error) {
    const status = looksLikeUserCancelled(error)
      ? 'consent_or_auth_cancelled'
      : 'consent_or_auth_failed_safe'

    return createPuterAuthConsentResult(status, {
      ...baseTruth,
      auth_failed_reason: status,
    })
  }
}

function resolvePuterRuntime(runtime: unknown): Record<string, unknown> | null {
  if (!isRecord(runtime)) {
    return null
  }

  const candidate = runtime as PuterAuthRuntime
  if (isRecord(candidate.puter)) {
    return candidate.puter as Record<string, unknown>
  }

  if (isRecord(candidate.window?.puter)) {
    return candidate.window?.puter as Record<string, unknown>
  }

  return null
}

function statusToFailedReason(status: PuterAuthConsentStatus): string {
  if (status === 'not_invoked' || status === 'consent_or_auth_completed') {
    return 'none'
  }

  return status
}

function statusToUserMessage(status: PuterAuthConsentStatus): string {
  switch (status) {
    case 'not_invoked':
      return 'Puter auth has not been requested.'
    case 'runtime_not_loaded':
      return 'Load the Puter runtime before requesting auth.'
    case 'auth_api_unavailable':
      return 'Puter auth is unavailable in this browser session.'
    case 'consent_or_auth_pending':
      return 'Puter auth or consent is pending in the browser.'
    case 'consent_or_auth_completed':
      return 'Puter auth or consent completed.'
    case 'consent_or_auth_cancelled':
      return 'Puter auth or consent was cancelled.'
    case 'consent_or_auth_failed_safe':
      return 'Puter auth or consent failed safely.'
  }
}

async function withTimeout<T>(promise: Promise<T>, timeoutMs: number): Promise<T | 'puter_auth_timeout'> {
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) {
    return promise
  }

  let timeoutId: ReturnType<typeof setTimeout> | undefined
  const timeout = new Promise<'puter_auth_timeout'>((resolve) => {
    timeoutId = setTimeout(() => resolve('puter_auth_timeout'), timeoutMs)
  })

  try {
    return await Promise.race([promise, timeout])
  } finally {
    if (timeoutId !== undefined) {
      clearTimeout(timeoutId)
    }
  }
}

function looksLikeUserCancelled(error: unknown): boolean {
  if (!isRecord(error)) {
    return false
  }

  const name = typeof error.name === 'string' ? error.name.toLowerCase() : ''
  const message = typeof error.message === 'string' ? error.message.toLowerCase() : ''
  return [name, message].some((value) => (
    value.includes('abort') ||
    value.includes('cancel') ||
    value.includes('closed') ||
    value.includes('denied')
  ))
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function sameKeySet(left: string[], right: string[]): boolean {
  return left.length === right.length && left.every((key, index) => key === right[index])
}
