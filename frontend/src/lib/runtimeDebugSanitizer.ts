const DANGEROUS_KEY_FRAGMENTS = [
  'stack',
  'traceback',
  'env',
  'api_key',
  'token',
  'jwt',
  'secret',
  'password',
  'authorization',
  'bearer',
  'command',
  'args',
  'argv',
  'stdout',
  'stderr',
  'raw',
  'raw_key',
  'raw_url',
  'payload',
  'execution_request',
  'memory_content',
  'memory_raw',
  'provider_raw',
  'raw_response',
  'tool_raw_result',
] as const

const SAFE_TOKEN_COUNT_KEYS = new Set([
  'tokens_in',
  'tokens_out',
  'input_tokens',
  'output_tokens',
])

const REDACTED = '[REDACTED]'

const UNIX_PATH_PATTERN = /(?<!\w)\/(?:home|root|tmp|var|usr|etc)(?:\/[^\s"'`{}[\],;:]+)+/g
const WINDOWS_PATH_PATTERN = /(?:[A-Z]:\\(?:Users|Windows|Program Files|Program Files \(x86\))(?:\\[^\s"'`{}[\],;:]+)+)/gi
const OPENAI_KEY_PATTERN = /\bsk-(?:proj-)?[A-Za-z0-9_-]{12,}\b/g
const BEARER_PATTERN = /\bbearer\s+[A-Za-z0-9._~+/=-]{12,}/gi
const JWT_PATTERN = /\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b/g
const SUPABASE_URL_PATTERN = /https:\/\/[a-z0-9-]+\.supabase\.co(?:\/[^\s"'`{}[\],;]*)?/gi
const EMAIL_PATTERN = /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi
const PHONE_PATTERN = /(?:\+?\d[\d\s().-]{7,}\d)/g

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function isDangerousKey(key: string): boolean {
  const normalized = key.trim().toLowerCase()
  if (SAFE_TOKEN_COUNT_KEYS.has(normalized)) {
    return false
  }
  return DANGEROUS_KEY_FRAGMENTS.some((fragment) => normalized.includes(fragment))
}

function redactString(value: string): string {
  return value
    .replace(UNIX_PATH_PATTERN, REDACTED)
    .replace(WINDOWS_PATH_PATTERN, REDACTED)
    .replace(OPENAI_KEY_PATTERN, REDACTED)
    .replace(BEARER_PATTERN, REDACTED)
    .replace(JWT_PATTERN, REDACTED)
    .replace(SUPABASE_URL_PATTERN, REDACTED)
    .replace(EMAIL_PATTERN, REDACTED)
    .replace(PHONE_PATTERN, REDACTED)
}

export function redactRuntimeDebugText(value: string): string {
  return redactString(value)
}

function sanitizeValue(input: unknown): unknown {
  if (Array.isArray(input)) {
    return input.map((item) => sanitizeValue(item))
  }

  if (isRecord(input)) {
    return Object.entries(input).reduce<Record<string, unknown>>((acc, [key, value]) => {
      if (isDangerousKey(key)) {
        acc[REDACTED] = REDACTED
        return acc
      }
      acc[key] = sanitizeValue(value)
      return acc
    }, {})
  }

  if (typeof input === 'string') {
    return redactString(input)
  }

  if (input === null || ['boolean', 'number', 'undefined'].includes(typeof input)) {
    return input
  }

  return redactString(String(input))
}

export function sanitizeRuntimeDebugPayload(input: unknown): Record<string, unknown> {
  if (!isRecord(input)) {
    return {}
  }

  const sanitized = sanitizeValue(input)
  return isRecord(sanitized) ? sanitized : {}
}

import type { GovernanceSummary } from '../types'

export function extractGovernanceSummary(
  metadata: { cognitiveRuntimeInspection?: Record<string, unknown> } | null,
): GovernanceSummary | null {
  if (!metadata) return null
  const raw = metadata.cognitiveRuntimeInspection?.governance
  if (!raw || typeof raw !== 'object') return null
  const record = raw as Record<string, unknown>
  const decision = ['allowed', 'blocked', 'requires_approval', 'unknown'].includes(String(record.decision))
    ? (record.decision as GovernanceSummary['decision'])
    : 'unknown'
  return {
    decision,
    category: String(record.category ?? ''),
    policy: String(record.policy ?? ''),
    reason: String(record.reason ?? ''),
    riskLevel: record.riskLevel as GovernanceSummary['riskLevel'],
  }
}
