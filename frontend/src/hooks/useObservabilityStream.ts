import { useEffect, useState } from 'react'
import { observabilityApiEnvelopeToUi } from '../features/observability'
import { API_BASE_URL } from '../lib/env'
import { supabase } from '../lib/supabase'
import type { ObservabilityApiResponse, ObservabilityConnectionState } from '../types/observability'
import type { UiObservabilitySnapshot } from '../types/ui/observability'
import { redactRuntimeDebugText } from '../lib/runtimeDebugSanitizer'
import {
  buildObservabilityStreamUrl,
  requestObservabilityStreamTicket,
} from '../lib/api/observability'

const STREAM_RECONNECT_DELAY_MS = 1_000

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
    let reconnectTimer: number | null = null
    let connecting = false

    const closeStream = () => {
      eventSource?.close()
      eventSource = null
    }

    const clearReconnectTimer = () => {
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer)
        reconnectTimer = null
      }
    }

    const scheduleReconnect = (token: string) => {
      if (cancelled || reconnectTimer !== null || token !== activeToken) {
        return
      }
      reconnectTimer = window.setTimeout(() => {
        reconnectTimer = null
        void openStream(token)
      }, STREAM_RECONNECT_DELAY_MS)
    }

    const openStream = async (token: string) => {
      if (cancelled) {
        return
      }
      activeToken = token
      if (connecting) {
        return
      }
      connecting = true
      clearReconnectTimer()
      setStatus((current) => (current === 'idle' ? 'reconnecting' : current))
      closeStream()

      try {
        const ticket = await requestObservabilityStreamTicket({
          Authorization: `Bearer ${token}`,
        })
        if (cancelled || token !== activeToken) {
          return
        }

        eventSource = new EventSource(buildObservabilityStreamUrl(ticket.ticket))
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
          closeStream()
          setStatus('reconnecting')
          setError((current) => current ?? 'Live observability stream disconnected. Retrying...')
          scheduleReconnect(token)
        }
      } catch (reason) {
        if (!cancelled && token === activeToken) {
          setStatus('reconnecting')
          setError(reason instanceof Error
            ? redactRuntimeDebugText(reason.message)
            : 'Failed to authorize live observability stream.')
          scheduleReconnect(token)
        }
      } finally {
        connecting = false
        if (!cancelled && activeToken && token !== activeToken) {
          void openStream(activeToken)
        }
      }
    }

    const connect = async () => {
      const { data, error: sessionError } = await supabase.auth.getSession()
      if (cancelled) {
        return
      }
      if (sessionError) {
        setStatus('error')
        setError(redactRuntimeDebugText(sessionError.message))
        return
      }
      if (!data.session?.access_token) {
        setStatus('error')
        setError('No active session')
        return
      }

      void openStream(data.session.access_token)
    }

    void connect()

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, session) => {
      if (cancelled) {
        return
      }
      const nextToken = session?.access_token ?? ''
      if (!nextToken) {
        clearReconnectTimer()
        closeStream()
        activeToken = ''
        setStatus('error')
        setError('No active session')
        return
      }
      if (nextToken !== activeToken) {
        void openStream(nextToken)
      }
    })

    return () => {
      cancelled = true
      clearReconnectTimer()
      closeStream()
      subscription.subscription.unsubscribe()
    }
  }, [enabled])

  return { snapshot, status, error }
}
