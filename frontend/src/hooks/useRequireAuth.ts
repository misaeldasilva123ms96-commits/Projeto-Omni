import { useEffect, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'

export function useRequireAuth() {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true

    supabase.auth.getSession()
      .then(({ data, error }) => {
        if (!mounted) {
          return
        }

        if (error) {
          setSession(null)
        } else {
          setSession(data.session ?? null)
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false)
        }
      })

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      if (!mounted) {
        return
      }
      setSession(nextSession ?? null)
      setLoading(false)
    })

    return () => {
      mounted = false
      subscription.subscription.unsubscribe()
    }
  }, [])

  return { session, loading }
}
