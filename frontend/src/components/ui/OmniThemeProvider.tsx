import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

type OmniTheme = 'light' | 'dark'

type OmniThemeContext = {
  theme: OmniTheme
  toggleTheme: () => void
  setTheme: (theme: OmniTheme) => void
}

const STORAGE_KEY = 'omni-theme'

const OmniThemeCtx = createContext<OmniThemeContext | null>(null)

function getInitialTheme(): OmniTheme {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') {
    return stored
  }
  if (window.matchMedia('(prefers-color-scheme: light)').matches) {
    return 'light'
  }
  return 'dark'
}

function applyTheme(theme: OmniTheme) {
  document.documentElement.dataset.omniTheme = theme
  document.documentElement.style.colorScheme = theme
}

export function OmniThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<OmniTheme>(getInitialTheme)

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  const setTheme = useCallback((next: OmniTheme) => {
    setThemeState(next)
    localStorage.setItem(STORAGE_KEY, next)
  }, [])

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => {
      const next = prev === 'dark' ? 'light' : 'dark'
      localStorage.setItem(STORAGE_KEY, next)
      return next
    })
  }, [])

  return (
    <OmniThemeCtx.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </OmniThemeCtx.Provider>
  )
}

export function useOmniTheme(): OmniThemeContext {
  const ctx = useContext(OmniThemeCtx)
  if (!ctx) {
    throw new Error('useOmniTheme must be used within OmniThemeProvider')
  }
  return ctx
}
