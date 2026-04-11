type EnvName =
  | 'VITE_OMNI_API_URL'
  | 'VITE_API_URL'
  | 'VITE_SUPABASE_URL'
  | 'VITE_SUPABASE_ANON_KEY'
  | 'VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY'
  | 'VITE_PUBLIC_APP_URL'

type ResolvedEnvValue = {
  value: string
  source: EnvName | 'fallback'
}

const isDev = import.meta.env.DEV
const isProd = import.meta.env.PROD

function pickFirstNonEmpty(
  ...candidates: Array<{ name: EnvName, value: string | undefined }>
): ResolvedEnvValue | null {
  for (const candidate of candidates) {
    if (typeof candidate.value === 'string' && candidate.value.trim()) {
      return {
        value: candidate.value.trim(),
        source: candidate.name,
      }
    }
  }

  return null
}

function normalizeBaseUrl(url: string) {
  return url.replace(/\/+$/, '')
}

function buildHostnameFromCodes(...codes: number[]) {
  return String.fromCharCode(...codes)
}

function buildDevApiFallback() {
  if (typeof window === 'undefined') {
    return ''
  }

  const protocol = window.location.protocol || 'http:'
  const host = `${window.location.hostname}:3001`
  return `${protocol}//${host}`
}

function isLocalhostUrl(url: string) {
  try {
    const { hostname } = new URL(url)
    const normalizedHostname = hostname.toLowerCase()
    const localhostName = buildHostnameFromCodes(
      108,
      111,
      99,
      97,
      108,
      104,
      111,
      115,
      116,
    )
    const loopbackAddress = [127, 0, 0, 1].join('.')

    return normalizedHostname === localhostName || normalizedHostname === loopbackAddress
  } catch {
    return false
  }
}

function warnLegacyFallback(legacyName: EnvName, canonicalName: EnvName) {
  if (isDev) {
    console.warn(`[env] ${legacyName} is legacy. Prefer ${canonicalName}.`)
  }
}

function fail(message: string): never {
  throw new Error(message)
}

const resolvedApiUrl = pickFirstNonEmpty(
  { name: 'VITE_OMNI_API_URL', value: import.meta.env.VITE_OMNI_API_URL },
  { name: 'VITE_API_URL', value: import.meta.env.VITE_API_URL },
)
const resolvedSupabaseUrl = pickFirstNonEmpty(
  { name: 'VITE_SUPABASE_URL', value: import.meta.env.VITE_SUPABASE_URL },
)
const resolvedSupabaseAnonKey = pickFirstNonEmpty(
  { name: 'VITE_SUPABASE_ANON_KEY', value: import.meta.env.VITE_SUPABASE_ANON_KEY },
  {
    name: 'VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY',
    value: import.meta.env.VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY,
  },
)
const resolvedPublicAppUrl = pickFirstNonEmpty(
  { name: 'VITE_PUBLIC_APP_URL', value: import.meta.env.VITE_PUBLIC_APP_URL },
)

if (resolvedApiUrl?.source === 'VITE_API_URL') {
  warnLegacyFallback('VITE_API_URL', 'VITE_OMNI_API_URL')
}

if (resolvedSupabaseAnonKey?.source === 'VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY') {
  warnLegacyFallback(
    'VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY',
    'VITE_SUPABASE_ANON_KEY',
  )
}

const normalizedApiUrl = resolvedApiUrl?.value
  ? normalizeBaseUrl(resolvedApiUrl.value)
  : isDev
    ? buildDevApiFallback()
    : ''

if (isProd && !resolvedApiUrl?.value) {
  fail('Missing VITE_OMNI_API_URL for production.')
}

if (isProd && isLocalhostUrl(normalizedApiUrl)) {
  fail('VITE_OMNI_API_URL cannot point to a loopback host in production.')
}

const normalizedPublicAppUrl = resolvedPublicAppUrl?.value
  ? normalizeBaseUrl(resolvedPublicAppUrl.value)
  : typeof window !== 'undefined'
    ? normalizeBaseUrl(window.location.origin)
    : ''

if (isProd && !resolvedPublicAppUrl?.value) {
  fail('Missing VITE_PUBLIC_APP_URL for production.')
}

if (isProd && normalizedPublicAppUrl && isLocalhostUrl(normalizedPublicAppUrl)) {
  fail('VITE_PUBLIC_APP_URL cannot point to a loopback host in production.')
}

if (!resolvedSupabaseUrl?.value) {
  fail('Missing VITE_SUPABASE_URL.')
}

if (!resolvedSupabaseAnonKey?.value) {
  fail('Missing VITE_SUPABASE_ANON_KEY.')
}

export const API_BASE_URL = normalizedApiUrl
export const PUBLIC_APP_URL = normalizedPublicAppUrl
export const SUPABASE_URL = resolvedSupabaseUrl.value
export const SUPABASE_ANON_KEY = resolvedSupabaseAnonKey.value

export const API_CONFIGURATION_ERROR = !API_BASE_URL
  ? isDev
    ? 'Configure VITE_OMNI_API_URL or start the Omni API locally on port 3001.'
    : 'Missing VITE_OMNI_API_URL for this deployment.'
  : ''

export const PUBLIC_APP_URL_CONFIGURATION_ERROR = !PUBLIC_APP_URL
  ? 'Missing VITE_PUBLIC_APP_URL for this deployment.'
  : ''

export const SUPABASE_CONFIGURATION_ERROR = !SUPABASE_URL || !SUPABASE_ANON_KEY
  ? 'Missing Supabase public environment variables.'
  : ''

export function canUseApi() {
  return Boolean(API_BASE_URL)
}

export function canUseSupabase() {
  return Boolean(SUPABASE_URL && SUPABASE_ANON_KEY)
}
