# Omni Frontend on Cloudflare Pages

## Deployment shape

- Framework: Vite + React + TypeScript
- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `dist`
- Pages Functions: not required for the current frontend

The Omni frontend is a static Pages deployment. The cognitive runtime remains external and must be configured through a public API URL.

## Required Cloudflare Pages environment variables

- `VITE_OMNI_API_URL`
  - Public HTTPS URL of the external Omni backend
- `VITE_SUPABASE_URL`
  - Public Supabase project URL
- `VITE_SUPABASE_ANON_KEY`
  - Public Supabase anon key
- `VITE_PUBLIC_APP_URL`
  - Public browser URL of this deployment

## Recommended Cloudflare Pages settings

- Production branch: `main`
- Build system version: latest default
- Node version: `20`
- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `dist`

## Supabase configuration checklist

Use your real production domain and your preview domain values below.

### Site URL

- Production Site URL:
  - `https://your-production-domain.pages.dev`
  - If using a custom domain, prefer the custom domain here instead

### Redirect URLs

- Local development:
  - `http://localhost:5173/**`
- Cloudflare Pages previews:
  - `https://*.pages.dev/**`
- Production:
  - `https://your-production-domain.pages.dev/**`
  - `https://your-custom-domain.example.com/**`

If auth callbacks are later moved to a dedicated route, tighten these to the exact callback URL.

## Operational notes

- `_redirects` is included so client-side navigation falls back to `index.html`
- The backend API must be public and must not point to localhost in production
- The current frontend does not require Pages Functions or Workers for runtime execution
- Legacy env names are still read as fallback for compatibility:
  - `VITE_API_URL`
  - `VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY`
