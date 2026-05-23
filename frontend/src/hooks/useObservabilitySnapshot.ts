import { useEffect, useState } from 'react'
import { fetchObservabilitySnapshot, observabilityApiEnvelopeToUi } from '../features/observability'
import type { UiObservabilitySnapshot } from '../types/ui/observability'

export function useObservabilitySnapshot(enabled: boolean) {
  const [snapshot, setSnapshot] = useState<UiObservabilitySnapshot | null>(null)
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
        const ui = observabilityApiEnvelopeToUi(payload)
        setSnapshot(ui.snapshot)
        if (ui.status !== 'ok' && ui.error) {
          setError(ui.error)
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
