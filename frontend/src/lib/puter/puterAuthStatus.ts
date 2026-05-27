export type PuterAuthStatusResult =
  | 'not_invoked'
  | 'runtime_not_loaded'
  | 'auth_api_unavailable'
  | 'auth_status_check_failed_safe'
  | 'signed_out'
  | 'signed_in_sanitized'
  | 'user_unavailable_safe'

export type PuterAuthStatusSanitizedUser = {
  user_present: boolean
  username_present: boolean
  email_present: boolean
  id_present: boolean
}

export type PuterAuthStatusRuntimeTruth = {
  puter_runtime_loaded: boolean
  auth_api_available: boolean
  auth_status_checked: boolean
  is_signed_in: boolean
  user_present: boolean
  sanitized_user_present: boolean
  raw_auth_payload_exposed: false
  provider_attempted: false
  provider_succeeded: false
  raw_provider_payload_exposed: false
}

export type PuterAuthStatusOutput = {
  ok: boolean
  status: PuterAuthStatusResult
  reason: string
  user_message: string
  is_signed_in: boolean
  user_present: boolean
  sanitized_user: PuterAuthStatusSanitizedUser | null
  retry_allowed: boolean
  manual_action_required: boolean
  runtime_truth: PuterAuthStatusRuntimeTruth
}

type PuterAuthApi = {
  getUser?: unknown
  isSignedIn?: unknown
}

type PuterAuthBrowserWindow = Window & {
  puter?: unknown
}

const OUTPUT_KEYS = [
  'ok',
  'status',
  'reason',
  'user_message',
  'is_signed_in',
  'user_present',
  'sanitized_user',
  'retry_allowed',
  'manual_action_required',
  'runtime_truth',
] as const

const RUNTIME_TRUTH_KEYS = [
  'puter_runtime_loaded',
  'auth_api_available',
  'auth_status_checked',
  'is_signed_in',
  'user_present',
  'sanitized_user_present',
  'raw_auth_payload_exposed',
  'provider_attempted',
  'provider_succeeded',
  'raw_provider_payload_exposed',
] as const

export function getInitialPuterAuthStatusOutput(): PuterAuthStatusOutput {
  return createPuterAuthStatusOutput('not_invoked')
}

export function isPuterAuthStatusOutput(value: unknown): value is PuterAuthStatusOutput {
  if (!isRecord(value) || !isRecord(value.runtime_truth)) {
    return false
  }

  return sameKeySet(Object.keys(value).sort(), [...OUTPUT_KEYS].sort())
    && sameKeySet(Object.keys(value.runtime_truth).sort(), [...RUNTIME_TRUTH_KEYS].sort())
}

export async function checkPuterAuthStatus(runtime: unknown = globalThis): Promise<PuterAuthStatusOutput> {
  const puter = resolveTrustedPuterRuntime(runtime)
  if (!puter) {
    return createPuterAuthStatusOutput('runtime_not_loaded')
  }

  const auth = isRecord(puter.auth) ? (puter.auth as PuterAuthApi) : null
  if (typeof auth?.isSignedIn !== 'function') {
    return createPuterAuthStatusOutput('auth_api_unavailable', {
      puter_runtime_loaded: true,
    })
  }

  try {
    const isSignedIn = Boolean((auth.isSignedIn as () => unknown)())
    if (!isSignedIn) {
      return createPuterAuthStatusOutput('signed_out', {
        puter_runtime_loaded: true,
        auth_api_available: true,
        auth_status_checked: true,
      })
    }

    let user: unknown = null
    if (typeof auth.getUser === 'function') {
      try {
        user = await Promise.resolve((auth.getUser as () => unknown)())
      } catch {
        return createPuterAuthStatusOutput('user_unavailable_safe', {
          puter_runtime_loaded: true,
          auth_api_available: true,
          auth_status_checked: true,
          is_signed_in: true,
        })
      }
    }

    if (user === null || typeof user !== 'object' || Array.isArray(user)) {
      return createPuterAuthStatusOutput('user_unavailable_safe', {
        puter_runtime_loaded: true,
        auth_api_available: true,
        auth_status_checked: true,
        is_signed_in: true,
      })
    }

    const sanitizedUser = sanitizeUserPresence(user as Record<string, unknown>)
    return createPuterAuthStatusOutput('signed_in_sanitized', {
      puter_runtime_loaded: true,
      auth_api_available: true,
      auth_status_checked: true,
      is_signed_in: true,
      user_present: true,
      sanitized_user_present: true,
    }, sanitizedUser)
  } catch {
    return createPuterAuthStatusOutput('auth_status_check_failed_safe', {
      puter_runtime_loaded: true,
      auth_api_available: true,
    })
  }
}

function createPuterAuthStatusOutput(
  status: PuterAuthStatusResult,
  truth: Partial<PuterAuthStatusRuntimeTruth> = {},
  sanitizedUser: PuterAuthStatusSanitizedUser | null = null,
): PuterAuthStatusOutput {
  const runtimeTruth: PuterAuthStatusRuntimeTruth = {
    puter_runtime_loaded: false,
    auth_api_available: false,
    auth_status_checked: false,
    is_signed_in: false,
    user_present: false,
    sanitized_user_present: false,
    raw_auth_payload_exposed: false,
    provider_attempted: false,
    provider_succeeded: false,
    raw_provider_payload_exposed: false,
    ...truth,
  }

  return {
    ok: status === 'signed_out'
      || status === 'signed_in_sanitized'
      || status === 'user_unavailable_safe',
    status,
    reason: status,
    user_message: statusToUserMessage(status),
    is_signed_in: runtimeTruth.is_signed_in,
    user_present: runtimeTruth.user_present,
    sanitized_user: sanitizedUser,
    retry_allowed: status === 'auth_api_unavailable'
      || status === 'auth_status_check_failed_safe'
      || status === 'signed_in_sanitized'
      || status === 'user_unavailable_safe',
    manual_action_required: status !== 'signed_in_sanitized'
      && status !== 'user_unavailable_safe',
    runtime_truth: runtimeTruth,
  }
}

function resolveTrustedPuterRuntime(runtime: unknown): Record<string, unknown> | null {
  const browserWindow = resolveTrustedBrowserWindow(runtime)
  if (!browserWindow || !isRecord(browserWindow.puter)) {
    return null
  }

  return browserWindow.puter as Record<string, unknown>
}

function resolveTrustedBrowserWindow(runtime: unknown): PuterAuthBrowserWindow | null {
  if (
    typeof globalThis.window === 'undefined'
    || typeof globalThis.document === 'undefined'
    || globalThis.window.document !== globalThis.document
  ) {
    return null
  }

  const browserWindow = globalThis.window as PuterAuthBrowserWindow
  if (runtime === globalThis || runtime === browserWindow) {
    return browserWindow
  }

  if (isRecord(runtime) && runtime.window === browserWindow) {
    return browserWindow
  }

  return null
}

function sanitizeUserPresence(user: Record<string, unknown>): PuterAuthStatusSanitizedUser {
  return {
    user_present: true,
    username_present: typeof user.username === 'string' && user.username.length > 0,
    email_present: typeof user.email === 'string' && user.email.length > 0,
    id_present: user.id !== undefined && user.id !== null,
  }
}

function statusToUserMessage(status: PuterAuthStatusResult): string {
  switch (status) {
    case 'not_invoked':
      return 'Auth status has not been checked.'
    case 'runtime_not_loaded':
      return 'Load the Puter runtime before checking auth status.'
    case 'auth_api_unavailable':
      return 'Puter auth status API is unavailable in this browser session.'
    case 'auth_status_check_failed_safe':
      return 'Puter auth status check failed safely.'
    case 'signed_out':
      return 'Puter reports signed out.'
    case 'signed_in_sanitized':
      return 'Puter reports signed in. Only sanitized user presence was returned.'
    case 'user_unavailable_safe':
      return 'Puter reports signed in, but user details were unavailable safely.'
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function sameKeySet(left: string[], right: string[]): boolean {
  return left.length === right.length && left.every((key, index) => key === right[index])
}
