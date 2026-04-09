# Omni Supabase Schema

This repository now includes a production-oriented Supabase foundation migration for Omni at:

- `supabase/migrations/20260409_omni_schema_foundation.sql`

The schema covers:

- identity: `profiles`, `user_settings`
- conversation: `chat_sessions`, `chat_messages`
- memory: `memory_entries`
- documents: `documents`, `document_chunks`
- audit: `audit_events`
- runtime compatibility: `runtime_memory_embeddings`
- storage: private bucket `omni-documents`

Important compatibility note:

- The current Node runtime writes semantic memory into `runtime_memory_embeddings` using a string session identifier. The migration therefore uses `session_external_id text` instead of a foreign key to `chat_sessions.id`.
- The current Node runtime still reads `VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY`. Frontend already uses `VITE_SUPABASE_ANON_KEY`, but the runtime-side Supabase client should be updated in a follow-up change to align on the canonical key name.

Recommended application path:

1. Review the SQL migration.
2. Apply it in Supabase SQL editor or via Supabase CLI migrations.
3. Verify RLS and storage policies with a real authenticated user.
4. Follow up by aligning runtime-side env usage and wiring frontend flows to the new tables.
