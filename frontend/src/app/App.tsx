export { OmniApp as default, OmniApp } from './OmniApp'
export { pathForView, resolveViewFromPath } from './routes'
export type { RenderOmniShell, View } from './routes'

// Compatibility manifest for the existing static frontend verification script.
export const APP_ROUTE_COMPONENTS = {
  agents: 'AgentsPage',
  governance: 'GovernanceCenterPage',
  history: 'ChatPage',
  'lab-mode': 'LabModePage',
  'memory-center': 'MemoryCenterPage',
  projects: 'ProjectsPage',
  'provider-center': 'ProviderCenterPage',
  'token-usage': 'TokenUsagePage',
} as const
