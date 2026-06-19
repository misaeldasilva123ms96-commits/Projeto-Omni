import {
  hasObservabilityContext,
  parseObservabilityContext,
  serializeObservabilityContext,
  type ObservabilityContext,
} from './observabilityContext'

const CONTEXT_HISTORY_STORAGE_KEY = 'omni.observability.context-history.v1'
const ALLOWED_CONTEXT_PATHS = new Set([
  '/observability',
  '/provider-center',
  '/governance',
])

export const CONTEXT_HISTORY_MAX_ENTRIES = 5

export type ObservabilityContextHistoryEntry = {
  path: string
  context: ObservabilityContext
}

function sessionStorageOrNull(): Storage | null {
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}

function normalizeEntry(value: unknown): ObservabilityContextHistoryEntry | null {
  if (!value || typeof value !== 'object') return null
  const record = value as Record<string, unknown>
  if (typeof record.path !== 'string' || !ALLOWED_CONTEXT_PATHS.has(record.path)) {
    return null
  }
  if (!record.context || typeof record.context !== 'object') return null

  const context = parseObservabilityContext(
    serializeObservabilityContext(record.context as ObservabilityContext),
  )
  if (!hasObservabilityContext(context)) return null
  return { path: record.path, context }
}

function entryKey(entry: ObservabilityContextHistoryEntry): string {
  return `${entry.path}${serializeObservabilityContext(entry.context)}`
}

export function loadObservabilityContextHistory(
  storage: Storage | null = sessionStorageOrNull(),
): ObservabilityContextHistoryEntry[] {
  if (!storage) return []
  try {
    const raw = storage.getItem(CONTEXT_HISTORY_STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      storage.removeItem(CONTEXT_HISTORY_STORAGE_KEY)
      return []
    }
    const entries = parsed
      .map(normalizeEntry)
      .filter((entry): entry is ObservabilityContextHistoryEntry => Boolean(entry))
      .slice(0, CONTEXT_HISTORY_MAX_ENTRIES)
    storage.setItem(CONTEXT_HISTORY_STORAGE_KEY, JSON.stringify(entries))
    return entries
  } catch {
    try {
      storage.removeItem(CONTEXT_HISTORY_STORAGE_KEY)
    } catch {
      // Storage can be blocked by browser policy.
    }
    return []
  }
}

export function saveObservabilityContextHistory(
  path: string,
  context: ObservabilityContext,
  storage: Storage | null = sessionStorageOrNull(),
): ObservabilityContextHistoryEntry[] {
  if (!storage) return []
  const entry = normalizeEntry({ path, context })
  if (!entry) return loadObservabilityContextHistory(storage)

  const next = [
    entry,
    ...loadObservabilityContextHistory(storage).filter(
      (candidate) => entryKey(candidate) !== entryKey(entry),
    ),
  ].slice(0, CONTEXT_HISTORY_MAX_ENTRIES)

  try {
    storage.setItem(CONTEXT_HISTORY_STORAGE_KEY, JSON.stringify(next))
    return next
  } catch {
    return []
  }
}

export function clearObservabilityContextHistory(
  storage: Storage | null = sessionStorageOrNull(),
): void {
  if (!storage) return
  try {
    storage.removeItem(CONTEXT_HISTORY_STORAGE_KEY)
  } catch {
    // Storage can be blocked by browser policy.
  }
}
