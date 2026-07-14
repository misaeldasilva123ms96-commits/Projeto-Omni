import { beforeEach, describe, expect, it } from 'vitest'
import { readMigratedStorage, removeMigratedStorage, writeMigratedStorage } from './storageKeyMigration'

describe('storage key migration', () => {
  beforeEach(() => localStorage.clear())

  it('prefers canonical data when both keys exist', () => {
    localStorage.setItem('omni-key', 'canonical')
    localStorage.setItem('omini-key', 'legacy')

    expect(readMigratedStorage('omni-key', 'omini-key')).toBe('canonical')
  })

  it('copies legacy data without deleting it', () => {
    localStorage.setItem('omini-key', 'legacy')

    expect(readMigratedStorage('omni-key', 'omini-key')).toBe('legacy')
    expect(localStorage.getItem('omni-key')).toBe('legacy')
    expect(localStorage.getItem('omini-key')).toBe('legacy')
  })

  it('mirrors writes during the rollback-compatible transition', () => {
    writeMigratedStorage('omni-key', 'omini-key', 'current')

    expect(localStorage.getItem('omni-key')).toBe('current')
    expect(localStorage.getItem('omini-key')).toBe('current')
  })

  it('removes canonical and legacy values together', () => {
    writeMigratedStorage('omni-key', 'omini-key', 'current')
    removeMigratedStorage('omni-key', 'omini-key')

    expect(localStorage.getItem('omni-key')).toBeNull()
    expect(localStorage.getItem('omini-key')).toBeNull()
  })
})
