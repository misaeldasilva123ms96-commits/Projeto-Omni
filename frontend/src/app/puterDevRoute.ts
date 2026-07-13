export const PUTER_DEV_ROUTE_PATH = '/dev/puter'

function flagEnabled(value: unknown): boolean {
  return typeof value === 'string' && ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase())
}

export function canShowPuterDevRoute(
  experimentalFeatureEnabled = flagEnabled(import.meta.env.VITE_OMNI_EXPERIMENTAL_PUTER_FREE),
  devSurfaceEnabled = flagEnabled(import.meta.env.VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE),
): boolean {
  return experimentalFeatureEnabled === true && devSurfaceEnabled === true
}
