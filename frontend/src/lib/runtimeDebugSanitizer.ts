/**
 * Runtime debug payload sanitizer — Phase 1D (Roadmap Oficial v2.1).
 *
 * Never expose raw debug payloads in the frontend UI.
 * Use sanitizeRuntimeDebugPayload() before rendering any runtime metadata.
 */

/** Fields that are safe to expose in the UI. */
const ALLOWED_KEYS: ReadonlySet<string> = new Set([
  'runtime_mode',
  'runtime_lane',
  'degraded',
  'fallback_triggered',
  'provider_public_name',
  'provider_attempted',
  'provider_succeeded',
  'tool_invoked',
  'tool_status',
  'tool_public_name',
  'latency_ms',
  'request_id',
  'warnings_public',
  'error_public_code',
  'error_public_message',
  'public_summary',
]);

/** Key fragments that are NEVER safe to expose, regardless of exact name. */
const FORBIDDEN_FRAGMENTS: ReadonlyArray<string> = [
  'stack',
  'trace',
  'traceback',
  'env',
  'api_key',
  'token',
  'secret',
  'password',
  'command',
  'stdout',
  'stderr',
  'raw',
  'payload',
  'absolute',
  'memory_content',
  'provider_raw',
];

function isForbiddenKey(key: string): boolean {
  const lower = key.toLowerCase();
  return FORBIDDEN_FRAGMENTS.some((fragment) => lower.includes(fragment));
}

/**
 * Sanitize a runtime debug payload object.
 * Returns a new object containing only public-safe fields.
 * Nested objects are sanitized recursively.
 *
 * @example
 * const safePayload = sanitizeRuntimeDebugPayload(debugPayload);
 * // <pre>{JSON.stringify(safePayload, null, 2)}</pre>
 */
export function sanitizeRuntimeDebugPayload(
  payload: unknown,
  { strict = false }: { strict?: boolean } = {},
): Record<string, unknown> {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return {};
  }

  const input = payload as Record<string, unknown>;
  const result: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(input)) {
    // Forbidden key check
    if (isForbiddenKey(key)) {
      continue;
    }

    // Strict mode: only whitelisted keys
    if (strict && !ALLOWED_KEYS.has(key)) {
      continue;
    }

    // Recurse into nested objects
    if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      const nested = sanitizeRuntimeDebugPayload(value, { strict });
      if (Object.keys(nested).length > 0) {
        result[key] = nested;
      }
      continue;
    }

    // Arrays: filter to primitives only (no nested objects with potential secrets)
    if (Array.isArray(value)) {
      result[key] = (value as unknown[]).filter(
        (item) => item === null || typeof item !== 'object',
      );
      continue;
    }

    result[key] = value;
  }

  return result;
}

/**
 * Strict-mode sanitizer — only ALLOWED_KEYS are passed through.
 * Use this for fields rendered directly in the public UI.
 */
export function sanitizeRuntimeDebugPayloadStrict(
  payload: unknown,
): Record<string, unknown> {
  return sanitizeRuntimeDebugPayload(payload, { strict: true });
}

export { ALLOWED_KEYS, FORBIDDEN_FRAGMENTS };
