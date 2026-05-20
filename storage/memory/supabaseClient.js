let createClient = null;
let supabaseLoadError = null;

try {
  ({ createClient } = require('@supabase/supabase-js'));
} catch (error) {
  supabaseLoadError = error;
}

function readSupabaseEnv(name) {
  if (typeof process !== 'undefined' && process.env && process.env[name]) {
    return process.env[name];
  }
  return '';
}

// Prefer server-side names; fall back to Vite-prefixed vars when Node is spawned from the same shell as the UI.
const supabaseUrl =
  readSupabaseEnv('SUPABASE_URL')
  || readSupabaseEnv('VITE_SUPABASE_URL');
const supabaseKey =
  readSupabaseEnv('SUPABASE_ANON_KEY')
  || readSupabaseEnv('VITE_SUPABASE_ANON_KEY')
  || readSupabaseEnv('VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY');

let supabase = null;
let supabaseInitError = null;

if (createClient && supabaseUrl && supabaseKey) {
  try {
    supabase = createClient(supabaseUrl, supabaseKey, {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    });
  } catch (error) {
    supabaseInitError = error;
  }
}

function isSupabaseConfigured() {
  return Boolean(supabase);
}

function getSupabaseDiagnostics() {
  if (supabase) {
    return {
      backend: 'supabase',
      available: true,
      configured: true,
      package_available: true,
      reason: 'configured',
    };
  }

  if (!createClient) {
    return {
      backend: 'local-file',
      available: false,
      configured: false,
      package_available: false,
      reason: supabaseLoadError?.code === 'MODULE_NOT_FOUND' ? 'package_missing' : 'package_load_failed',
      package: '@supabase/supabase-js',
    };
  }

  if (!supabaseUrl || !supabaseKey) {
    return {
      backend: 'local-file',
      available: false,
      configured: false,
      package_available: true,
      reason: 'missing_env',
      required_env: ['SUPABASE_URL', 'SUPABASE_ANON_KEY'],
    };
  }

  return {
    backend: 'local-file',
    available: false,
    configured: false,
    package_available: true,
    reason: 'client_init_failed',
    error_code: supabaseInitError?.code || null,
  };
}

/**
 * Returns a new Supabase client instance (preferred over direct `supabase` export).
 * Future: direct `supabase` export will be removed once all importers migrate here.
 */
function getSupabaseClient() {
  return supabase;
}

/**
 * Safe diagnostics — never exposes key or URL values.
 */
function getSupabaseSafeDiagnostics() {
  return {
    supabase_configured: isSupabaseConfigured(),
    url_present: Boolean(supabaseUrl),
    anon_key_present: Boolean(supabaseKey),
    // supabaseKey and supabaseUrl are intentionally NOT returned here
  };
}

module.exports = {
  getSupabaseDiagnostics,
  getSupabaseSafeDiagnostics,
  isSupabaseConfigured,
  supabase,          // @deprecated — migrate callers to getSupabaseClient()
  getSupabaseClient, // preferred
  // REMOVED: supabaseKey  — never export raw credentials
  // REMOVED: supabaseUrl  — never export raw credentials
};
