const { createClient } = require('@supabase/supabase-js');

function readSupabaseEnv(name) {
  if (typeof process !== 'undefined' && process.env && process.env[name]) {
    return process.env[name];
  }
  return '';
}

const supabaseUrl = readSupabaseEnv('VITE_SUPABASE_URL');
const supabaseKey = readSupabaseEnv('VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY');

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
