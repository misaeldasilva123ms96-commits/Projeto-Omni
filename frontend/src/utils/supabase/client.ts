import { createClient, type SupabaseClient } from '@supabase/supabase-js'

let browserClient: SupabaseClient | null = null

function getSupabaseUrl(): string {
  return import.meta.env.VITE_SUPABASE_URL?.trim() || ''
}

function getSupabasePublishableKey(): string {
  return import.meta.env.VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY?.trim() || ''
}

export function createBrowserSupabaseClient(): SupabaseClient {
  const supabaseUrl = getSupabaseUrl()
  const supabasePublishableKey = getSupabasePublishableKey()

  if (!supabaseUrl || !supabasePublishableKey) {
    throw new Error(
      'Missing Supabase environment variables: VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY',
    )
  }

  return createClient(supabaseUrl, supabasePublishableKey, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  })
}

export function getBrowserSupabaseClient(): SupabaseClient {
  if (!browserClient) {
    browserClient = createBrowserSupabaseClient()
  }

  return browserClient
}
