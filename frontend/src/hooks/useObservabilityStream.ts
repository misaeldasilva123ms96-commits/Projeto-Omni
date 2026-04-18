import { useEffect, useState } from 'react'
import { observabilityApiEnvelopeToUi } from '../features/observability'
import { API_BASE_URL } from '../lib/env'
import { supabase } from '../lib/supabase'
import type { ObservabilityApiResponse, ObservabilityConnectionState } from '../types/observability'
import type { UiObservabilitySnapshot } from '../types/ui/observability'

export function useObservabilityStream(enabled: boolean) {
  const [snapshot, setSnapshot] = useState<UiObservabilitySnapshot | null>(null)
  const [status, setStatus] = useState<ObservabilityConnectionState>('idle')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!enabled || !API_BASE_URL) {
      return
    }

    let cancelled = false
    let eventSource: EventSource | null = null
    let activeToken = ''

    const closeStream = () => {
      eventSource?.close()
      eventSource = null
    }

    const openStream = (token: string) => {
      if (cancelled) {
        return
      }
      activeToken = token
      setStatus((current) => (current === 'idle' ? 'reconnecting' : current))
      closeStream()
      eventSource = new EventSource(
        `${API_BASE_URL}/api/observability/stream?token=${encodeURIComponent(token)}&interval=2`,
      )

      eventSource.addEventListener('snapshot', (event) => {
        try {
          const payload = JSON.parse((event as MessageEvent).data) as ObservabilityApiResponse
          const ui = observabilityApiEnvelopeToUi(payload)
          if (ui.snapshot) {
            setSnapshot(ui.snapshot)
          }
          if (ui.status === 'ok') {
            setStatus('live')
            setError(null)
          } else {
            setStatus('reconnecting')
            setError(ui.error ?? 'Observability reader returned an error.')
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

    const connect = async () => {
      const { data, error: sessionError } = await supabase.auth.getSession()
      if (cancelled) {
        return
      }
      if (sessionError) {
        setStatus('error')
        setError(sessionError.message)
        return
      }
      if (!data.session?.access_token) {
        setStatus('error')
        setError('No active session')
        return
      }

      openStream(data.session.access_token)
    }

    void connect()

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, session) => {
      if (cancelled) {
        return
      }
      const nextToken = session?.access_token ?? ''
      if (!nextToken) {
        closeStream()
        setStatus('error')
        setError('No active session')
        return
      }
      if (nextToken !== activeToken) {
        openStream(nextToken)
      }
    })

    return () => {
      cancelled = true
      closeStream()
      subscription.subscription.unsubscribe()
    }
  }, [enabled])

  return { snapshot, status, error }
}
