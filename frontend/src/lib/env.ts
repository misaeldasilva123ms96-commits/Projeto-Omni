const rawApiUrl = import.meta.env.VITE_API_URL?.trim()

const isDev = import.meta.env.DEV
const fallbackDevUrl = 'http://localhost:3001'

function normalizeBaseUrl(url: string) {
  return url.replace(/\/+$/, '')
}

export const API_BASE_URL = rawApiUrl
  ? normalizeBaseUrl(rawApiUrl)
  : isDev
    ? fallbackDevUrl
    : ''

export const API_CONFIGURATION_ERROR = !isDev && !API_BASE_URL
  ? 'A API publica do Omni nao foi configurada para esta implantacao.'
  : ''

if (isDev) {
  console.info('[env] API_BASE_URL =', API_BASE_URL || '(missing)')
}

if (!isDev && !API_BASE_URL) {
  console.error('[env] Missing VITE_API_URL in production build')
}

export function canUseApi() {
  return Boolean(API_BASE_URL)
}
