/**
 * Authenticated observability (`GET /api/observability/*`).
 */
import type {
  ObservabilityApiResponse,
  ObservabilityTracesResponse,
} from '../../types/observability'
import {
  API_BASE_URL,
  buildConfigurationError,
  fetchWithTimeout,
  getSupabaseAuthHeaders,
} from './client'

export async function fetchObservabilitySnapshot() {
  if (!API_BASE_URL) {
    throw buildConfigurationError()
  }

  const res = await fetchWithTimeout(`${API_BASE_URL}/api/observability/snapshot`, {
    headers: await getSupabaseAuthHeaders(),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error ${res.status}: ${text}`)
  }
  return res.json() as Promise<ObservabilityApiResponse>
}

export async function fetchObservabilityTraces(limit = 10) {
  if (!API_BASE_URL) {
    throw buildConfigurationError()
  }

  const res = await fetchWithTimeout(`${API_BASE_URL}/api/observability/traces?limit=${limit}`, {
    headers: await getSupabaseAuthHeaders(),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error ${res.status}: ${text}`)
  }
  return res.json() as Promise<ObservabilityTracesResponse>
}
