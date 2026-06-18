import { describe, expect, it } from 'vitest'
import { pathForView, resolveViewFromPath, VIEW_PATHS, type View } from './routes'

describe('Omni app routes', () => {
  it.each(Object.entries(VIEW_PATHS).filter(([view]) => view !== 'puter-dev'))(
    'resolves %s from %s',
    (view, path) => {
      expect(resolveViewFromPath(path, false)).toBe(view)
    },
  )

  it('keeps the Puter development route guarded', () => {
    expect(resolveViewFromPath(VIEW_PATHS['puter-dev'], false)).toBe('chat')
    expect(resolveViewFromPath(VIEW_PATHS['puter-dev'], true)).toBe('puter-dev')
  })

  it('falls back unknown paths to chat', () => {
    expect(resolveViewFromPath('/unknown', false)).toBe('chat')
  })

  it('returns the canonical path for each view', () => {
    for (const [view, path] of Object.entries(VIEW_PATHS)) {
      expect(pathForView(view as View)).toBe(path)
    }
  })
})
