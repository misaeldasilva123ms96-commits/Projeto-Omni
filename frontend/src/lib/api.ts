import { API_BASE_URL, API_CONFIGURATION_ERROR } from './env'

export async function sendOmniMessage(message: string, metadata?: unknown) {
  if (!API_BASE_URL) {
    throw new Error(
      API_CONFIGURATION_ERROR
        || 'VITE_API_URL not configured for this environment',
    )
  }

  const res = await fetch(`${API_BASE_URL}/api/chat`, {
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
