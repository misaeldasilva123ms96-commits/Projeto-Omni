begin;

-- One row per tool invocation outcome for analytics (Omni) and ops dashboards.
create table if not exists public.runtime_tool_events (
  id uuid primary key default gen_random_uuid(),
  occurred_at timestamptz not null default timezone('utc', now()),
  session_id text not null default '',
  task_id text not null default '',
  run_id text not null default '',
  tool_name text not null,
  success boolean not null,
  error_code text,
  latency_ms integer,
  provider text,
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists runtime_tool_events_occurred_idx
  on public.runtime_tool_events (occurred_at desc);

create index if not exists runtime_tool_events_tool_occurred_idx
  on public.runtime_tool_events (tool_name, occurred_at desc);

create index if not exists runtime_tool_events_session_occurred_idx
  on public.runtime_tool_events (session_id, occurred_at desc);

alter table public.runtime_tool_events enable row level security;

comment on table public.runtime_tool_events is
  'Omni runtime tool outcomes. Inserts: backend with SUPABASE_SERVICE_ROLE_KEY (RLS bypass). '
  'Reads: Omni Postgres connection (prefer dedicated read-only DB user; superuser bypasses RLS). '
  'PostgREST anon/authenticated: no policies => deny.';

-- Optional (run manually after creating a login role for Omni BI):
--   create role omni_analytics_reader login password '...';
--   grant usage on schema public to omni_analytics_reader;
--   grant select on public.runtime_tool_events to omni_analytics_reader;
--   create policy runtime_tool_events_omni_reader_select
--     on public.runtime_tool_events for select to omni_analytics_reader using (true);

commit;
