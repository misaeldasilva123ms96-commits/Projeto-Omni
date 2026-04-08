import { API_BASE_URL, API_CONFIGURATION_ERROR } from './env'

export async function sendOmniMessage(message: string, metadata?: unknown) {
  if (!API_BASE_URL) {
    throw new Error(
      API_CONFIGURATION_ERROR
        || 'VITE_API_URL not configured for this environment',
    )
  }

  const res = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message, metadata }),
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error ${res.status}: ${text}`)
  }

  return res.json()
}

async function getJson<T>(path: string): Promise<T> {
  if (!API_BASE_URL) {
    throw new Error(
      API_CONFIGURATION_ERROR
        || 'VITE_API_URL not configured for this environment',
    )
  }

  const res = await fetch(`${API_BASE_URL}${path}`)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export function fetchHealth() {
  return getJson('/health')
}

export function fetchRuntimeSignals() {
  return getJson('/internal/runtime-signals')
}

export function fetchSwarmLog() {
  return getJson('/internal/swarm-log')
}

export function fetchStrategyState() {
  return getJson('/internal/strategy-state')
}

export function fetchMilestones() {
  return getJson('/internal/milestones')
}

export function fetchPrSummaries() {
  return getJson('/internal/pr-summaries')
}
