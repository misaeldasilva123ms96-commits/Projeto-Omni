import { API_BASE_URL, API_CONFIGURATION_ERROR } from './env'
import type {
  ChatApiResponse,
  HealthResponse,
  MilestonesResponse,
  PrSummariesResponse,
  RuntimeSignalsResponse,
  StrategyStateResponse,
  SwarmLogResponse,
} from '../types'

const REQUEST_TIMEOUT_MS = 45_000

function buildConfigurationError() {
  return new Error(
    API_CONFIGURATION_ERROR
      || 'VITE_API_URL not configured for this environment',
  )
}

function normalizeChatResponse(payload: unknown): ChatApiResponse {
  if (typeof payload === 'string') {
    const response = payload.trim()
    if (!response) {
      throw new Error('Omni returned an empty response.')
    }
    return { response }
  }

  if (!payload || typeof payload !== 'object') {
    throw new Error('Omni returned an invalid response payload.')
  }

  const record = payload as Record<string, unknown>
  const response =
    typeof record.response === 'string'
      ? record.response
      : typeof record.message === 'string'
        ? record.message
        : ''

  if (!response.trim()) {
    throw new Error('Omni returned an empty response.')
  }

  return {
    response,
    session_id:
      typeof record.session_id === 'string' ? record.session_id : undefined,
    source: typeof record.source === 'string' ? record.source : undefined,
    matched_commands: Array.isArray(record.matched_commands)
      ? record.matched_commands.filter(
        (item): item is string => typeof item === 'string',
      )
      : [],
    matched_tools: Array.isArray(record.matched_tools)
      ? record.matched_tools.filter(
        (item): item is string => typeof item === 'string',
      )
      : [],
    stop_reason:
      typeof record.stop_reason === 'string' ? record.stop_reason : undefined,
    usage:
      record.usage && typeof record.usage === 'object'
        ? {
          input_tokens:
            typeof (record.usage as Record<string, unknown>).input_tokens === 'number'
              ? (record.usage as Record<string, number>).input_tokens
              : undefined,
          output_tokens:
            typeof (record.usage as Record<string, unknown>).output_tokens === 'number'
              ? (record.usage as Record<string, number>).output_tokens
              : undefined,
        }
        : undefined,
  }
}

async function parseResponseBody(res: Response) {
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

async function fetchWithTimeout(
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

export async function sendOmniMessage(message: string, metadata?: unknown) {
  if (!API_BASE_URL) {
    throw buildConfigurationError()
  }

  const res = await fetchWithTimeout(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message, metadata }),
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(
      text.trim()
        ? `Omni request failed (${res.status}): ${text}`
        : `Omni request failed with status ${res.status}.`,
    )
  }

  const payload = await parseResponseBody(res)
  return normalizeChatResponse(payload)
}

async function getJson<T>(path: string): Promise<T> {
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

export function fetchHealth() {
  return getJson<HealthResponse>('/health')
}

export function fetchRuntimeSignals() {
  return getJson<RuntimeSignalsResponse>('/internal/runtime-signals')
}

export function fetchSwarmLog() {
  return getJson<SwarmLogResponse>('/internal/swarm-log')
}

export function fetchStrategyState() {
  return getJson<StrategyStateResponse>('/internal/strategy-state')
}

export function fetchMilestones() {
  return getJson<MilestonesResponse>('/internal/milestones')
}

export function fetchPrSummaries() {
  return getJson<PrSummariesResponse>('/internal/pr-summaries')
}
