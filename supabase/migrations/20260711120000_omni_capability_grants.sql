begin;

create table if not exists public.omni_capability_grants (
  id uuid primary key default gen_random_uuid(),
  supabase_sub uuid not null references auth.users (id) on delete cascade,
  capability text not null,
  active boolean not null default false,
  revoked_at timestamptz,
  expires_at timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by text not null default 'system',
  updated_by text not null default 'system',
  grant_reason text not null default '',
  grant_source text not null default '',
  review_ticket text not null default '',
  metadata jsonb not null default '{}'::jsonb,
  constraint omni_capability_grants_capability_check check (
    capability = 'historical_audit:read'
  ),
  constraint omni_capability_grants_revoked_state_check check (
    revoked_at is null or active = false
  ),
  constraint omni_capability_grants_metadata_object_check check (
    jsonb_typeof(metadata) = 'object'
  )
);

create unique index if not exists omni_capability_grants_one_effective_active_idx
  on public.omni_capability_grants (supabase_sub, capability)
  where active = true and revoked_at is null;

create index if not exists omni_capability_grants_lookup_idx
  on public.omni_capability_grants (supabase_sub, capability);

create index if not exists omni_capability_grants_capability_idx
  on public.omni_capability_grants (capability);

create index if not exists omni_capability_grants_expires_idx
  on public.omni_capability_grants (expires_at);

create index if not exists omni_capability_grants_updated_idx
  on public.omni_capability_grants (updated_at desc);

drop trigger if exists omni_capability_grants_set_updated_at on public.omni_capability_grants;
create trigger omni_capability_grants_set_updated_at
before update on public.omni_capability_grants
for each row execute procedure public.omni_set_updated_at();

alter table public.omni_capability_grants enable row level security;

comment on table public.omni_capability_grants is
  'Server-owned Omni capability grants. First approved capability: historical_audit:read. '
  'Browser anon/authenticated clients have no policies and must not read or mutate grants.';

comment on column public.omni_capability_grants.supabase_sub is
  'Authenticated Supabase auth.users.id used as the server-side capability lookup key.';

comment on column public.omni_capability_grants.metadata is
  'Bounded operational metadata only; never store secrets, JWTs, service-role keys, prompts, raw storage, SQL, stdout, stderr, stack traces, command arguments, or file contents.';

commit;
