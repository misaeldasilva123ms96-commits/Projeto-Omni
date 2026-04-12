import { useEffect, useState } from 'react'
import { fetchObservabilitySnapshot } from '../lib/api'
import type { ObservabilitySnapshot } from '../types/observability'

export function useObservabilitySnapshot(enabled: boolean) {
  const [snapshot, setSnapshot] = useState<ObservabilitySnapshot | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!enabled) {
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    fetchObservabilitySnapshot()
      .then((payload) => {
        if (cancelled) {
          return
        }
        setSnapshot(payload.snapshot)
        if (payload.status !== 'ok' && payload.error) {
          setError(payload.error)
        }
      })
      .catch((reason) => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : 'Failed to load observability snapshot.')
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [enabled])

  return { snapshot, loading, error, setSnapshot }
}
