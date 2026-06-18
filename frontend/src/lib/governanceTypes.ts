import { redactRuntimeDebugText } from './runtimeDebugSanitizer'

export type GovernanceDecision =
  | 'allowed'
  | 'blocked'
  | 'requires_approval'
  | 'unknown'

export type GovernanceRiskLevel =
  | 'low'
  | 'medium'
  | 'high'
  | 'critical'
  | 'unknown'

export type RuntimeGovernanceStatus = {
  decision: GovernanceDecision
  risk_level: GovernanceRiskLevel
  blocked: boolean | null
  reason: string | null
  policy: string | null
  tool_category: string | null
  requires_approval: boolean | null
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function optionalString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? redactRuntimeDebugText(value) : null
}

function optionalBoolean(value: unknown): boolean | null {
  return typeof value === 'boolean' ? value : null
}

export function normalizeGovernanceStatus(value: unknown): RuntimeGovernanceStatus | null {
  if (!isRecord(value)) return null

  const rawDecision = optionalString(value.decision)
  const decision: GovernanceDecision = (
    rawDecision === 'allowed'
    || rawDecision === 'blocked'
    || rawDecision === 'requires_approval'
  )
    ? rawDecision
    : 'unknown'

  const rawRiskLevel = optionalString(value.risk_level ?? value.riskLevel)
  const riskLevel: GovernanceRiskLevel = (
    rawRiskLevel === 'low'
    || rawRiskLevel === 'medium'
    || rawRiskLevel === 'high'
    || rawRiskLevel === 'critical'
  )
    ? rawRiskLevel
    : 'unknown'

  return {
    decision,
    risk_level: riskLevel,
    blocked: optionalBoolean(value.blocked),
    reason: optionalString(value.reason),
    policy: optionalString(value.policy),
    tool_category: optionalString(value.tool_category ?? value.category),
    requires_approval: optionalBoolean(value.requires_approval),
  }
}
