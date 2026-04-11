import { createClient } from '@supabase/supabase-js'
import { SUPABASE_ANON_KEY, SUPABASE_CONFIGURATION_ERROR, SUPABASE_URL } from './env'

if (SUPABASE_CONFIGURATION_ERROR) {
  throw new Error(SUPABASE_CONFIGURATION_ERROR)
}

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
