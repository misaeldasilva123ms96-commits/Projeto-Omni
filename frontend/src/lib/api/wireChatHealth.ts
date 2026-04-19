/**
 * Pure wire → health classification (also asserted by Node E2E contract tests).
 * Keep in sync with `tests/e2e/chat-contract.e2e.ts` expectations.
 */

export type ChatWireHealth = 'ok' | 'degraded'

export function extractExecutionTier(
  inspection: Record<string, unknown> | null | undefined,
): string | undefined {
  if (!inspection || typeof inspection !== 'object' || Array.isArray(inspection)) {
    return undefined
  }
  const tier = inspection.execution_tier
  return typeof tier === 'string' && tier.trim() ? tier.trim() : undefined
}

export function classifyChatWireHealth(record: {
  response: string
  stop_reason?: string
  cognitive_runtime_inspection?: Record<string, unknown> | null
}): ChatWireHealth {
  const text = (record.response || '').trim()
  if (text.startsWith('[degraded:')) {
    return 'degraded'
  }
  const tier = extractExecutionTier(record.cognitive_runtime_inspection ?? undefined)
  if (tier === 'technical_fallback') {
    return 'degraded'
  }
  const sr = (record.stop_reason || '').trim()
  if (sr && sr !== 'python_completed' && sr !== 'mock_completed') {
    return 'degraded'
  }
  return 'ok'
}
