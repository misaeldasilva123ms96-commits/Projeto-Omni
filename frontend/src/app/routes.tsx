import type { ReactNode } from 'react'
import type { OmniShellProps } from '../components/shell/OmniShell'
import { PUTER_DEV_ROUTE_PATH, canShowPuterDevRoute } from '../pages/PuterDevRoutePage'

export type View =
  | 'chat'
  | 'dashboard'
  | 'history'
  | 'observability'
  | 'projects'
  | 'provider-center'
  | 'token-usage'
  | 'agents'
  | 'governance'
  | 'memory-center'
  | 'lab-mode'
  | 'settings'
  | 'puter-dev'

export type RenderOmniShell = (
  content: ReactNode,
  options?: Omit<OmniShellProps, 'children'>,
) => ReactNode

export const VIEW_PATHS: Record<View, string> = {
  chat: '/',
  dashboard: '/dashboard',
  history: '/history',
  observability: '/observability',
  projects: '/projects',
  'provider-center': '/provider-center',
  'token-usage': '/token-usage',
  agents: '/agents',
  governance: '/governance',
  'memory-center': '/memory-center',
  'lab-mode': '/lab-mode',
  settings: '/settings',
  'puter-dev': PUTER_DEV_ROUTE_PATH,
}

const PATH_VIEWS = new Map(
  Object.entries(VIEW_PATHS).map(([view, path]) => [path, view as View]),
)

export function resolveViewFromPath(
  pathname: string,
  puterDevRouteVisible = canShowPuterDevRoute(),
): View {
  const resolved = PATH_VIEWS.get(pathname)
  if (resolved === 'puter-dev' && !puterDevRouteVisible) {
    return 'chat'
  }
  return resolved ?? 'chat'
}

export function pathForView(view: View) {
  return VIEW_PATHS[view]
}
