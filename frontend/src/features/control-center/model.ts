import type { ProviderRecord } from '../settings/types'
import type { RuntimeSignalsResponse } from '../../types'

export type ProviderOperationalState = 'unconfigured' | 'healthy' | 'unhealthy' | 'unverified'

/**
 * A saved key does not establish connectivity; only a valid health result does.
 * This model deliberately never infers live provider execution from configuration.
 */
export function providerOperationalState(provider: ProviderRecord): ProviderOperationalState {
  if (!provider.configured) return 'unconfigured'
  if (provider.health_valid && provider.healthy === true) return 'healthy'
  if (provider.health_valid && provider.healthy === false) return 'unhealthy'
  return 'unverified'
}

export function recentRuntimeMode(signals: RuntimeSignalsResponse | null): string | null {
  const value = signals?.latest_run_summary?.runtime_mode
  return typeof value === 'string' && value.trim() ? value.trim() : null
}

export function safeCount(value: number | null | undefined): string {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0
    ? value.toLocaleString('pt-BR')
    : '—'
}

export const RUNTIME_LAYERS = [
  {
    id: 'frontend',
    title: 'Omni Cockpit',
    technology: 'React / Vite',
    path: 'frontend/',
    responsibility: 'Interface web, inspeção e operação. Carregamento da tela não comprova a saúde do backend.',
  },
  {
    id: 'rust',
    title: 'Rust API',
    technology: 'Rust / Axum',
    path: 'backend/rust/',
    responsibility: 'Fronteira HTTP, autenticação, sanitização das respostas e ponte de processos.',
  },
  {
    id: 'python',
    title: 'Python Brain',
    technology: 'Python',
    path: 'backend/python/brain/runtime/',
    responsibility: 'Orquestração, governança, classificação e avaliação das execuções.',
  },
  {
    id: 'node',
    title: 'QueryEngine',
    technology: 'Node.js',
    path: 'core/ · js-runner/ · platform/',
    responsibility: 'Execução governada de provedores, ferramentas e ações.',
  },
] as const

export type RuntimeLayerId = typeof RUNTIME_LAYERS[number]['id']
