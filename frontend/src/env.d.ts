/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_OMNI_API_URL?: string
  readonly VITE_API_URL?: string
  readonly VITE_PUBLIC_APP_URL?: string
  readonly VITE_OMNI_EXPERIMENTAL_PUTER_FREE?: string
  readonly VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE?: string
  readonly VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_MOCK?: string
  readonly VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL?: string
  readonly VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_DEV_TOGGLE?: string
  readonly VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT?: string
  readonly VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_INTERNAL?: string
  readonly VITE_OMNI_EXPERIMENTAL_PUTER_FREE_PILOT_ALLOWLISTED?: string
  readonly VITE_OMNI_EXPERIMENTAL_PUTER_FREE_CHAT_MOCKED_WIRING?: string
  readonly VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE?: string
  readonly VITE_SUPABASE_URL?: string
  readonly VITE_SUPABASE_ANON_KEY?: string
  readonly VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
