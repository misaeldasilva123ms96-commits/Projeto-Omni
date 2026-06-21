const DANGEROUS_KEY_FRAGMENTS = [
  'stack',
  'traceback',
  'env',
  'api_key',
  'apikey',
  'token',
  'ticket',
  'jwt',
  'secret',
  'password',
  'passphrase',
  'private_key',
  'access_key',
  'refresh_token',
  'authorization',
  'bearer',
  'cookie',
  'set-cookie',
  'set_cookie',
  'headers',
  'x-api-key',
  'x_api_key',
  'x-auth-token',
  'x_auth_token',
  'command',
  'args',
  'argv',
  'shell',
  'stdout',
  'stderr',
  'dotenv',
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
const TRUNCATED = '[TRUNCATED]'
const MAX_STRING_LENGTH = 2_000
const MAX_DEPTH = 12
const MAX_ARRAY_ITEMS = 100
const MAX_OBJECT_PROPERTIES = 100
const MAX_NODES = 1_000

const UNIX_PATH_PATTERN = /(?<!\w)\/(?:home|root|tmp|var|usr|etc)(?:\/[^\s"'`{}[\],;:]+)+/g
const WINDOWS_PATH_PATTERN = /(?:[A-Z]:\\(?:Users|Windows|Program Files|Program Files \(x86\))(?:\\[^\s"'`{}[\],;:]+)+)/gi
const OPENAI_KEY_PATTERN = /\bsk-(?:proj-)?[A-Za-z0-9_-]{12,}\b/g
const OPENAI_UNDERSCORE_KEY_PATTERN = /\bsk_proj_[A-Za-z0-9_-]{12,}\b/g
const BEARER_PATTERN = /\bbearer\s+[A-Za-z0-9._~+/=-]{12,}/gi
const JWT_PATTERN = /\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b/g
const GITHUB_TOKEN_PATTERN = /\b(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b/g
const GITLAB_TOKEN_PATTERN = /\bglpat-[A-Za-z0-9_-]{12,}\b/g
const SLACK_TOKEN_PATTERN = /\bxox[bp]-[A-Za-z0-9-]{12,}\b/g
const AWS_ACCESS_KEY_PATTERN = /\bAKIA[A-Z0-9]{16}\b/g
const OBSERVABILITY_STREAM_TICKET_PATTERN = /\bost_[a-f0-9]{64}\b/gi
const PEM_BLOCK_PATTERN = /-----BEGIN [A-Z0-9 ]+-----[\s\S]*?(?:-----END [A-Z0-9 ]+-----|$)/g
const ENV_SECRET_PATTERN = /\b(?:SUPABASE_SERVICE_ROLE|OPENAI_API_KEY|ANTHROPIC_API_KEY|OPENROUTER_API_KEY)\s*=\s*[^\s,;]+/gi
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
  const redacted = value
    .replace(UNIX_PATH_PATTERN, REDACTED)
    .replace(WINDOWS_PATH_PATTERN, REDACTED)
    .replace(OPENAI_KEY_PATTERN, REDACTED)
    .replace(OPENAI_UNDERSCORE_KEY_PATTERN, REDACTED)
    .replace(BEARER_PATTERN, REDACTED)
    .replace(JWT_PATTERN, REDACTED)
    .replace(GITHUB_TOKEN_PATTERN, REDACTED)
    .replace(GITLAB_TOKEN_PATTERN, REDACTED)
    .replace(SLACK_TOKEN_PATTERN, REDACTED)
    .replace(AWS_ACCESS_KEY_PATTERN, REDACTED)
    .replace(OBSERVABILITY_STREAM_TICKET_PATTERN, REDACTED)
    .replace(PEM_BLOCK_PATTERN, REDACTED)
    .replace(ENV_SECRET_PATTERN, REDACTED)
    .replace(SUPABASE_URL_PATTERN, REDACTED)
    .replace(EMAIL_PATTERN, REDACTED)
    .replace(PHONE_PATTERN, REDACTED)
  return redacted.length > MAX_STRING_LENGTH
    ? `${redacted.slice(0, MAX_STRING_LENGTH)}… ${TRUNCATED}`
    : redacted
}

export function redactRuntimeDebugText(value: string): string {
  return redactString(value)
}

type SanitizeState = {
  seen: WeakSet<object>
  nodes: number
}

function sanitizeValue(input: unknown, state: SanitizeState, depth = 0): unknown {
  state.nodes += 1
  if (state.nodes > MAX_NODES || depth > MAX_DEPTH) return TRUNCATED

  if (Array.isArray(input)) {
    if (state.seen.has(input)) return REDACTED
    state.seen.add(input)
    const result: unknown[] = []
    const count = Math.min(input.length, MAX_ARRAY_ITEMS)
    for (let index = 0; index < count; index += 1) {
      try {
        const descriptor = Object.getOwnPropertyDescriptor(input, String(index))
        result.push(
          descriptor && 'value' in descriptor
            ? sanitizeValue(descriptor.value, state, depth + 1)
            : REDACTED,
        )
      } catch {
        result.push(REDACTED)
      }
    }
    if (input.length > count) result.push(TRUNCATED)
    return result
  }

  if (isRecord(input)) {
    if (state.seen.has(input)) return REDACTED
    state.seen.add(input)
    const output: Record<string, unknown> = Object.create(null)
    let keys: string[]
    try {
      keys = Object.keys(input).slice(0, MAX_OBJECT_PROPERTIES)
    } catch {
      return { [REDACTED]: REDACTED }
    }
    for (const key of keys) {
      if (isDangerousKey(key)) {
        output[REDACTED] = REDACTED
        continue
      }
      const safeKey = redactString(key)
      if (safeKey !== key || safeKey === REDACTED) {
        output[REDACTED] = REDACTED
        continue
      }
      try {
        const descriptor = Object.getOwnPropertyDescriptor(input, key)
        output[key] = descriptor && 'value' in descriptor
          ? sanitizeValue(descriptor.value, state, depth + 1)
          : REDACTED
      } catch {
        output[key] = REDACTED
      }
    }
    if (keys.length === MAX_OBJECT_PROPERTIES) output[TRUNCATED] = TRUNCATED
    return output
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

  let sanitized: unknown
  try {
    sanitized = sanitizeValue(input, { seen: new WeakSet(), nodes: 0 })
  } catch {
    return { [REDACTED]: REDACTED }
  }
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
    category: redactRuntimeDebugText(String(record.category ?? '')),
    policy: redactRuntimeDebugText(String(record.policy ?? '')),
    reason: redactRuntimeDebugText(String(record.reason ?? '')),
    riskLevel: ['low', 'medium', 'high', 'critical'].includes(String(record.riskLevel))
      ? record.riskLevel as GovernanceSummary['riskLevel']
      : undefined,
  }
}
