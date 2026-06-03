import { useState } from 'react'
import {
  checkPuterAuthStatus,
  getInitialPuterAuthStatusOutput,
  type PuterAuthStatusOutput,
} from './puterAuthStatus'

export const PUTER_AUTH_STATUS_DEV_SURFACE_VERSION = 'puter_auth_status_dev_surface_v1'

export type PuterAuthStatusDevSurfaceProps = {
  puterRuntimeLoaded: boolean
}

export function PuterAuthStatusDevSurface({
  puterRuntimeLoaded,
}: PuterAuthStatusDevSurfaceProps) {
  const [result, setResult] = useState<PuterAuthStatusOutput>(getInitialPuterAuthStatusOutput())
  const [checking, setChecking] = useState(false)
  const [checkedOnce, setCheckedOnce] = useState(false)

  async function handleCheckStatus() {
    if (!puterRuntimeLoaded || checking) {
      return
    }

    setChecking(true)
    try {
      const output = await checkPuterAuthStatus()
      setResult(output)
      setCheckedOnce(true)
    } finally {
      setChecking(false)
    }
  }

  return (
    <section
      aria-label="Puter auth status dev surface"
      data-puter-auth-status-dev-surface={PUTER_AUTH_STATUS_DEV_SURFACE_VERSION}
    >
      <p>Development-only Puter auth status check</p>
      <button
        type="button"
        onClick={handleCheckStatus}
        disabled={!puterRuntimeLoaded || checking}
      >
        {checking ? 'Checking Puter auth status' : 'Check Puter auth status'}
      </button>
      {!puterRuntimeLoaded && (
        <p>Load Puter runtime first before checking auth status.</p>
      )}
      <output aria-label="Puter auth status result">
        {checkedOnce ? result.status : 'not_invoked'}
      </output>
      {checkedOnce && (
        <dl aria-label="Puter auth status safe details">
          <dt>is_signed_in</dt>
          <dd>{String(result.is_signed_in)}</dd>
          <dt>user_present</dt>
          <dd>{String(result.user_present)}</dd>
          <dt>user_message</dt>
          <dd>{result.user_message}</dd>
          {result.sanitized_user && (
            <>
              <dt>sanitized_user</dt>
              <dd>
                username_present={String(result.sanitized_user.username_present)};
                email_present={String(result.sanitized_user.email_present)};
                id_present={String(result.sanitized_user.id_present)}
              </dd>
            </>
          )}
          <dt>runtime_truth</dt>
          <dd>
            raw_auth_payload_exposed={String(result.runtime_truth.raw_auth_payload_exposed)};
            provider_attempted={String(result.runtime_truth.provider_attempted)};
            provider_succeeded={String(result.runtime_truth.provider_succeeded)};
            raw_provider_payload_exposed={String(result.runtime_truth.raw_provider_payload_exposed)}
          </dd>
        </dl>
      )}
    </section>
  )
}
