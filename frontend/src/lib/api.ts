export async function sendOmniMessage(message: string, metadata?: unknown) {
  const base = import.meta.env.VITE_API_URL

  if (!base) {
    throw new Error('VITE_API_URL not configured')
  }

  const res = await fetch(`${base}/api/chat`, {
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
