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

function getSupabaseClient() {
  return supabase;
}

function getSupabaseDiagnostics() {
  return {
    supabase_configured: Boolean(supabase),
    url_present: Boolean(supabaseUrl),
    anon_key_present: Boolean(supabaseKey),
    service_role_present: Boolean(readSupabaseEnv('SUPABASE_SERVICE_ROLE_KEY')),
  };
}

module.exports = {
  getSupabaseClient,
  getSupabaseDiagnostics,
  isSupabaseConfigured,
  supabase,
};
