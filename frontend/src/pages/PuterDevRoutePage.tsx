import {
  isPuterFreeModeFlagEnabled,
} from '../lib/puter/freeModePuterBrowserAdapter'
import {
  PuterDevManualSurface,
  isPuterDevSurfaceFlagEnabled,
} from '../lib/puter/PuterDevManualSurface'

export const PUTER_DEV_ROUTE_PATH = '/dev/puter'
export const PUTER_DEV_ROUTE_VERSION = 'puter_dev_route_v1'

type PuterDevRoutePageProps = {
  accessSnapshotEnvelope?: unknown
  devSurfaceEnabled?: boolean
  experimentalFeatureEnabled?: boolean
  runtime?: unknown
}

export function canShowPuterDevRoute(
  experimentalFeatureEnabled = isPuterFreeModeFlagEnabled(),
  devSurfaceEnabled = isPuterDevSurfaceFlagEnabled(),
): boolean {
  return experimentalFeatureEnabled === true && devSurfaceEnabled === true
}

export function buildPuterDevRouteBoundaryEnvelope(overrides: Record<string, unknown> = {}) {
  return {
    ok: true,
    access_snapshot: {
      snapshot_version: 'public_access_snapshot_v1',
      plan_mode: 'free',
      provider_mode: 'experimental_free',
      subject_id: 'dev-session',
      usage_date: '2026-05-23',
      tokens_in: 100,
      tokens_out: 25,
      tokens_total: 125,
      daily_token_limit: 15000,
      quota_remaining: 14875,
      quota_exceeded: false,
      input_allowed: true,
      output_allowed: true,
      quota_allowed: true,
      routing_allowed: true,
      fallback_allowed: false,
      selected_provider_family: 'experimental_free_provider',
      selected_adapter_id: 'experimental_free_adapter',
      adapter_display_name: 'Experimental Free Provider',
      adapter_capabilities: {
        supports_streaming: false,
        supports_tools: false,
        supports_files: false,
        supports_long_context: false,
        supports_sensitive_tools: false,
        is_experimental: true,
        is_user_key_required: false,
        is_managed: false,
        is_internal: false,
      },
      decision_reason: 'routing_allowed',
    },
    denied: false,
    reason: 'ok',
    snapshot_version: 'public_access_snapshot_v1',
    boundary_version: 'access_snapshot_boundary_v1',
    ...overrides,
  }
}

export function PuterDevRoutePage({
  accessSnapshotEnvelope = buildPuterDevRouteBoundaryEnvelope(),
  devSurfaceEnabled = isPuterDevSurfaceFlagEnabled(),
  experimentalFeatureEnabled = isPuterFreeModeFlagEnabled(),
  runtime = globalThis,
}: PuterDevRoutePageProps) {
  if (!canShowPuterDevRoute(experimentalFeatureEnabled, devSurfaceEnabled)) {
    return null
  }

  return (
    <main aria-label="Puter dev route" data-puter-dev-route-version={PUTER_DEV_ROUTE_VERSION}>
      <section>
        <p>Development-only Puter manual validation</p>
        <PuterDevManualSurface
          accessSnapshotEnvelope={accessSnapshotEnvelope}
          defaultPrompt="Hello from the local Puter dev route."
          devSurfaceEnabled={devSurfaceEnabled}
          experimentalFeatureEnabled={experimentalFeatureEnabled}
          runtime={runtime}
        />
      </section>
    </main>
  )
}
