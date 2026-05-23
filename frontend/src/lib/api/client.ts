/**
 * Shared HTTP client for Omni Rust API (timeouts, JSON parse, Supabase bearer).
 */
import { API_BASE_URL, API_CONFIGURATION_ERROR } from '../env'
import { supabase } from '../supabase'

export const REQUEST_TIMEOUT_MS = 45_000

export function buildConfigurationError() {
  return new Error(
    API_CONFIGURATION_ERROR
      || 'VITE_OMNI_API_URL not configured for this environment',
  )
}

export async function parseResponseBody(res: Response) {
  const contentType = res.headers.get('content-type') || ''

  if (contentType.includes('application/json')) {
    return res.json()
  }

  const text = await res.text()
  if (!text.trim()) {
    return ''
  }

  try {
    return JSON.parse(text) as unknown
  } catch {
    return text
  }
}

export async function fetchWithTimeout(
  input: RequestInfo | URL,
  init?: RequestInit,
) {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  try {
    return await fetch(input, {
      ...init,
      signal: controller.signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('Omni took too long to respond. Please try again.')
    }
    throw error
  } finally {
    window.clearTimeout(timeout)
  }
}

export async function getSupabaseAuthHeaders() {
  const { data, error } = await supabase.auth.getSession()
  if (error) {
    throw error
  }

  if (!data.session?.access_token) {
    throw new Error('No active session')
  }

  return {
    Authorization: `Bearer ${data.session.access_token}`,
  }
}

export async function getJson<T>(path: string): Promise<T> {
  if (!API_BASE_URL) {
    throw buildConfigurationError()
  }

  const res = await fetchWithTimeout(`${API_BASE_URL}${path}`)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

/** Authenticated GET JSON (e.g. operator telemetry). Caller supplies `Authorization` from `getSupabaseAuthHeaders`. */
export async function getJsonWithAuth<T>(
  path: string,
  authHeaders: Record<string, string>,
): Promise<T> {
  if (!API_BASE_URL) {
    throw buildConfigurationError()
  }

  const res = await fetchWithTimeout(`${API_BASE_URL}${path}`, {
    headers: {
      Accept: 'application/json',
      ...authHeaders,
    },
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export { API_BASE_URL, API_CONFIGURATION_ERROR }
