import { useEffect, useState } from 'react'
import { isPuterFreeModeFlagEnabled } from './freeModePuterBrowserAdapter'
import {
  createPuterAuthConsentResult,
  isPuterRuntimeLoadedForAuth,
  requestPuterAuthConsent,
  type PuterAuthConsentResult,
} from './puterAuthConsent'
import { isPuterDevSurfaceFlagEnabled } from './PuterDevManualSurface'

export const PUTER_AUTH_CONSENT_DEV_SURFACE_VERSION = 'puter_auth_consent_dev_surface_v1'

export type PuterAuthConsentDevSurfaceProps = {
  devSurfaceEnabled?: boolean
  experimentalFeatureEnabled?: boolean
  onAuthConsentResult?: (result: PuterAuthConsentResult) => void
  runtime?: unknown
  timeoutMs?: number
}

export function PuterAuthConsentDevSurface({
  devSurfaceEnabled = isPuterDevSurfaceFlagEnabled(),
  experimentalFeatureEnabled = isPuterFreeModeFlagEnabled(),
  onAuthConsentResult,
  runtime = globalThis,
  timeoutMs,
}: PuterAuthConsentDevSurfaceProps) {
  const [state, setState] = useState<PuterAuthConsentResult>(createPuterAuthConsentResult())
  const [runtimeLoaded, setRuntimeLoaded] = useState(() => isPuterRuntimeLoadedForAuth(runtime))
  const pending = state.status === 'consent_or_auth_pending'

  useEffect(() => {
    if (!devSurfaceEnabled || !experimentalFeatureEnabled || runtimeLoaded) {
      return
    }

    const intervalId = setInterval(() => {
      setRuntimeLoaded(isPuterRuntimeLoadedForAuth(runtime))
    }, 500)

    return () => clearInterval(intervalId)
  }, [devSurfaceEnabled, experimentalFeatureEnabled, runtime, runtimeLoaded])

  if (!devSurfaceEnabled || !experimentalFeatureEnabled) {
    return null
  }

  async function handleAuthConsentClick() {
    const latestRuntimeLoaded = isPuterRuntimeLoadedForAuth(runtime)
    setRuntimeLoaded(latestRuntimeLoaded)
    setState(createPuterAuthConsentResult('consent_or_auth_pending', {
      puter_runtime_loaded: latestRuntimeLoaded,
      auth_attempted: true,
      auth_failed_reason: 'consent_or_auth_pending',
    }))
    const result = await requestPuterAuthConsent({ runtime, timeoutMs })
    setState(result)
    onAuthConsentResult?.(result)
  }

  return (
    <section
      aria-label="Puter auth consent dev surface"
      data-puter-auth-consent-dev-surface={PUTER_AUTH_CONSENT_DEV_SURFACE_VERSION}
    >
      <p>Development-only Puter auth and consent</p>
      <button
        type="button"
        onClick={handleAuthConsentClick}
        disabled={!runtimeLoaded || pending}
      >
        Connect / Sign in with Puter
      </button>
      <output aria-label="Puter auth consent result">
        {state.status}
      </output>
    </section>
  )
}
