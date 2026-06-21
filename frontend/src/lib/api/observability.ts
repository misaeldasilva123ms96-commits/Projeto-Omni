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
import { redactRuntimeDebugText } from '../runtimeDebugSanitizer'

export type ObservabilityStreamTicketResponse = {
  ticket: string
  expires_in_seconds: number
}

export function buildObservabilityStreamUrl(ticket: string) {
  if (!API_BASE_URL) {
    throw buildConfigurationError()
  }
  const query = new URLSearchParams({
    ticket,
    interval: '2',
  })
  return `${API_BASE_URL}/api/observability/stream?${query.toString()}`
}

export async function requestObservabilityStreamTicket(
  authHeaders: Record<string, string>,
): Promise<ObservabilityStreamTicketResponse> {
  if (!API_BASE_URL) {
    throw buildConfigurationError()
  }

  const res = await fetchWithTimeout(`${API_BASE_URL}/api/observability/stream-ticket`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      ...authHeaders,
    },
  })
  if (!res.ok) {
    throw new Error(`Observability stream ticket request failed (${res.status}).`)
  }

  const payload = await res.json() as Partial<ObservabilityStreamTicketResponse>
  if (
    typeof payload.ticket !== 'string'
    || payload.ticket.length < 16
    || payload.ticket.length > 256
    || !/^[A-Za-z0-9_-]+$/.test(payload.ticket)
    || typeof payload.expires_in_seconds !== 'number'
    || !Number.isFinite(payload.expires_in_seconds)
    || payload.expires_in_seconds <= 0
  ) {
    throw new Error('Observability stream ticket response was invalid.')
  }

  return {
    ticket: payload.ticket,
    expires_in_seconds: payload.expires_in_seconds,
  }
}

export async function fetchObservabilitySnapshot() {
  if (!API_BASE_URL) {
    throw buildConfigurationError()
  }

  const res = await fetchWithTimeout(`${API_BASE_URL}/api/observability/snapshot`, {
    headers: await getSupabaseAuthHeaders(),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(redactRuntimeDebugText(`API error ${res.status}: ${text}`))
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
    throw new Error(redactRuntimeDebugText(`API error ${res.status}: ${text}`))
  }
  return res.json() as Promise<ObservabilityTracesResponse>
}
