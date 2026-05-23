/**
 * Authenticated operator telemetry (`GET /api/v1/operator/*`).
 * Each helper returns `null` when there is no session, JWT validation fails, or the request errors — callers fall back to `/internal/*`.
 * See `docs/frontend/operator-telemetry-adoption.md`.
 */
import type {
  OperatorMilestonesV1,
  OperatorRuntimeSignalsV1,
  OperatorStrategyChangesV1,
} from '../../types'
import { getJsonWithAuth, getSupabaseAuthHeaders } from './client'

export async function tryFetchOperatorRuntimeSignals(): Promise<OperatorRuntimeSignalsV1 | null> {
  try {
    const headers = await getSupabaseAuthHeaders()
    return await getJsonWithAuth<OperatorRuntimeSignalsV1>(
      '/api/v1/operator/runtime/signals',
      headers,
    )
  } catch {
    return null
  }
}

export async function tryFetchOperatorStrategyChanges(): Promise<OperatorStrategyChangesV1 | null> {
  try {
    const headers = await getSupabaseAuthHeaders()
    return await getJsonWithAuth<OperatorStrategyChangesV1>(
      '/api/v1/operator/strategy/changes',
      headers,
    )
  } catch {
    return null
  }
}

export async function tryFetchOperatorMilestones(): Promise<OperatorMilestonesV1 | null> {
  try {
    const headers = await getSupabaseAuthHeaders()
    return await getJsonWithAuth<OperatorMilestonesV1>('/api/v1/operator/milestones', headers)
  } catch {
    return null
  }
}
