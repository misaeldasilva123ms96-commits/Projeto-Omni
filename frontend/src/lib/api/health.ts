/**
 * Liveness — `GET /health`
 */
import type { HealthResponse } from '../../types'
import { getJson } from './client'

export function fetchHealth() {
  return getJson<HealthResponse>('/health')
}
