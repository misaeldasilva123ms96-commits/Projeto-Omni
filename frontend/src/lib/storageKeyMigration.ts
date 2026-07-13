export function readMigratedStorage(canonicalKey: string, legacyKey: string): string | null {
  const canonicalValue = localStorage.getItem(canonicalKey)
  if (canonicalValue !== null) return canonicalValue

  const legacyValue = localStorage.getItem(legacyKey)
  if (legacyValue === null) return null

  try {
    localStorage.setItem(canonicalKey, legacyValue)
  } catch {
    // Reading legacy data must remain available even when storage is read-only.
  }
  return legacyValue
}

export function writeMigratedStorage(canonicalKey: string, legacyKey: string, value: string): void {
  localStorage.setItem(canonicalKey, value)
  try {
    // Temporary mirror keeps rollback compatibility during the naming migration.
    localStorage.setItem(legacyKey, value)
  } catch {
    // The canonical write already succeeded.
  }
}

export function removeMigratedStorage(canonicalKey: string, legacyKey: string): void {
  localStorage.removeItem(canonicalKey)
  try {
    localStorage.removeItem(legacyKey)
  } catch {
    // The canonical removal already succeeded.
  }
}
