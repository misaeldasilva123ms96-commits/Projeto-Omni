import { getJsonWithAuth, getSupabaseAuthHeaders } from '../../lib/api/client'

export type GovernedRun = {
  runId: string
  status: 'running' | 'paused' | 'awaiting_approval' | 'completed' | 'failed' | 'unknown'
  updatedAt: string | null
}

type RunsWire = { status?: string; runs?: unknown }
const STATES = new Set<GovernedRun['status']>([
  'running', 'paused', 'awaiting_approval', 'completed', 'failed',
])

/** Return an allowlisted, bounded projection, never arbitrary run metadata. */
export function projectGovernedRuns(input: unknown): GovernedRun[] {
  if (!Array.isArray(input)) return []
  return input.slice(0, 50).flatMap((entry): GovernedRun[] => {
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) return []
    const item = entry as Record<string, unknown>
    const runId = typeof item.run_id === 'string' && /^[\w.:-]{1,96}$/.test(item.run_id)
      ? item.run_id : null
    if (!runId) return []
    const status = STATES.has(item.status as GovernedRun['status'])
      ? item.status as GovernedRun['status'] : 'unknown'
    const updatedAt = typeof item.updated_at === 'string'
      && /^\d{4}-\d\d-\d\dT/.test(item.updated_at)
      && Number.isFinite(Date.parse(item.updated_at))
      ? new Date(item.updated_at).toISOString() : null
    return [{ runId, status, updatedAt }]
  })
}

/**
 * Requires the Rust run_control:read capability and operator-scoped rows.
 * Never calls pause/resume/approve or stores metadata from the CLI response.
 */
export async function fetchGovernedRuns(): Promise<GovernedRun[]> {
  const authHeaders = await getSupabaseAuthHeaders()
  const response = await getJsonWithAuth<RunsWire>('/api/control/runs', authHeaders)
  if (response?.status !== 'ok') throw new Error('Run registry unavailable.')
  return projectGovernedRuns(response.runs)
}
