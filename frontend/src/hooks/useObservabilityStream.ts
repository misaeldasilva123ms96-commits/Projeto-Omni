import { useEffect, useState } from 'react'
import { API_BASE_URL } from '../lib/env'
import type {
  ObservabilityApiResponse,
  ObservabilityConnectionState,
  ObservabilitySnapshot,
} from '../types/observability'

export function useObservabilityStream(enabled: boolean) {
  const [snapshot, setSnapshot] = useState<ObservabilitySnapshot | null>(null)
  const [status, setStatus] = useState<ObservabilityConnectionState>('idle')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!enabled || !API_BASE_URL) {
      return
    }

    let cancelled = false
    let eventSource: EventSource | null = null

    const connect = () => {
      if (cancelled) {
        return
      }
      setStatus((current) => (current === 'idle' ? 'reconnecting' : current))
      eventSource = new EventSource(`${API_BASE_URL}/api/observability/stream`)

      eventSource.addEventListener('snapshot', (event) => {
        try {
          const payload = JSON.parse((event as MessageEvent).data) as ObservabilityApiResponse
          if (payload.snapshot) {
            setSnapshot(payload.snapshot)
          }
          if (payload.status === 'ok') {
            setStatus('live')
            setError(null)
          } else {
            setStatus('reconnecting')
            setError(payload.error ?? 'Observability reader returned an error.')
          }
        } catch {
          setStatus('reconnecting')
          setError('Failed to parse live observability payload.')
        }
      })

      eventSource.onerror = () => {
        if (cancelled) {
          return
        }
        setStatus('reconnecting')
        setError((current) => current ?? 'Live observability stream disconnected. Retrying...')
      }
    }

    connect()

    return () => {
      cancelled = true
      eventSource?.close()
    }
  }, [enabled])

  return { snapshot, status, error }
}
