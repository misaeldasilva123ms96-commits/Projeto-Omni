const { createClient } = require('@supabase/supabase-js');

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

const supabase = supabaseUrl && supabaseKey
  ? createClient(supabaseUrl, supabaseKey, {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    })
  : null;

function isSupabaseConfigured() {
  return Boolean(supabase);
}

module.exports = {
  isSupabaseConfigured,
  supabase,
  supabaseKey,
  supabaseUrl,
};
