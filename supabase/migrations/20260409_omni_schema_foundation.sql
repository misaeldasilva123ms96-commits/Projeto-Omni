begin;

create extension if not exists pgcrypto;

create or replace function public.omni_set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text,
  display_name text,
  avatar_url text,
  bio text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.user_settings (
  user_id uuid primary key references auth.users (id) on delete cascade,
  theme text,
  interface_mode text,
  preferred_model text,
  language text,
  timezone text,
  metadata jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.chat_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  external_session_id text unique,
  title text,
  mode text,
  status text,
  summary text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  archived_at timestamptz,
  constraint chat_sessions_mode_check check (
    mode is null or mode in ('chat', 'pesquisa', 'codigo', 'agente')
  ),
  constraint chat_sessions_status_check check (
    status is null or status in ('active', 'idle', 'completed', 'failed', 'archived')
  )
);

create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.chat_sessions (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  external_message_id text unique,
  role text not null,
  content text not null,
  content_json jsonb,
  metadata jsonb not null default '{}'::jsonb,
  token_count integer,
  created_at timestamptz not null default timezone('utc', now()),
  constraint chat_messages_role_check check (
    role in ('user', 'assistant', 'system', 'tool')
  )
);

create table if not exists public.memory_entries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  session_id uuid references public.chat_sessions (id) on delete set null,
  memory_type text not null,
  title text,
  summary text,
  content jsonb not null default '{}'::jsonb,
  source text,
  importance numeric,
  tags text[],
  is_pinned boolean not null default false,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint memory_entries_importance_check check (
    importance is null or (importance >= 0 and importance <= 1)
  )
);

create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  session_id uuid references public.chat_sessions (id) on delete set null,
  title text not null,
  original_filename text,
  mime_type text,
  storage_path text not null unique,
  size_bytes bigint,
  status text,
  summary text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint documents_status_check check (
    status is null or status in ('uploaded', 'processing', 'ready', 'failed', 'archived')
  )
);

create table if not exists public.document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  chunk_index integer not null,
  content text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  constraint document_chunks_document_chunk_unique unique (document_id, chunk_index)
);

create table if not exists public.audit_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users (id) on delete set null,
  event_type text not null,
  entity_type text,
  entity_id uuid,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.runtime_memory_embeddings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users (id) on delete set null,
  session_id text not null,
  path text not null default '',
  preview text not null default '',
  source text not null default 'runtime',
  embedding_text text not null default '',
  embedding double precision[],
  embedding_model text,
  embedding_dimensions integer,
  session_relevance double precision not null default 0,
  transcript_ref text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists profiles_email_idx
  on public.profiles (email);

create index if not exists chat_sessions_user_created_idx
  on public.chat_sessions (user_id, created_at desc);

create index if not exists chat_sessions_archived_idx
  on public.chat_sessions (archived_at);

create index if not exists chat_sessions_external_session_idx
  on public.chat_sessions (external_session_id);

create index if not exists chat_messages_session_created_idx
  on public.chat_messages (session_id, created_at);

create index if not exists chat_messages_user_created_idx
  on public.chat_messages (user_id, created_at);

create index if not exists chat_messages_external_message_idx
  on public.chat_messages (external_message_id);

create index if not exists memory_entries_user_created_idx
  on public.memory_entries (user_id, created_at desc);

create index if not exists memory_entries_session_idx
  on public.memory_entries (session_id);

create index if not exists memory_entries_type_idx
  on public.memory_entries (memory_type);

create index if not exists memory_entries_tags_gin_idx
  on public.memory_entries using gin (tags);

create index if not exists documents_user_created_idx
  on public.documents (user_id, created_at desc);

create index if not exists documents_session_idx
  on public.documents (session_id);

create index if not exists document_chunks_user_idx
  on public.document_chunks (user_id);

create index if not exists document_chunks_document_idx
  on public.document_chunks (document_id);

create index if not exists audit_events_user_created_idx
  on public.audit_events (user_id, created_at desc);

create index if not exists audit_events_type_created_idx
  on public.audit_events (event_type, created_at desc);

create index if not exists runtime_memory_embeddings_session_updated_idx
  on public.runtime_memory_embeddings (session_id, updated_at desc);

create index if not exists runtime_memory_embeddings_user_updated_idx
  on public.runtime_memory_embeddings (user_id, updated_at desc);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email, display_name, avatar_url, metadata)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'display_name', new.raw_user_meta_data ->> 'name'),
    new.raw_user_meta_data ->> 'avatar_url',
    coalesce(new.raw_user_meta_data, '{}'::jsonb)
  )
  on conflict (id) do update
  set
    email = excluded.email,
    display_name = coalesce(excluded.display_name, public.profiles.display_name),
    avatar_url = coalesce(excluded.avatar_url, public.profiles.avatar_url),
    metadata = public.profiles.metadata || excluded.metadata,
    updated_at = timezone('utc', now());

  insert into public.user_settings (user_id)
  values (new.id)
  on conflict (user_id) do nothing;

  return new;
end;
$$;

drop trigger if exists on_auth_user_created_omni on auth.users;
create trigger on_auth_user_created_omni
after insert on auth.users
for each row execute procedure public.handle_new_user();

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at
before update on public.profiles
for each row execute procedure public.omni_set_updated_at();

drop trigger if exists user_settings_set_updated_at on public.user_settings;
create trigger user_settings_set_updated_at
before update on public.user_settings
for each row execute procedure public.omni_set_updated_at();

drop trigger if exists chat_sessions_set_updated_at on public.chat_sessions;
create trigger chat_sessions_set_updated_at
before update on public.chat_sessions
for each row execute procedure public.omni_set_updated_at();

drop trigger if exists memory_entries_set_updated_at on public.memory_entries;
create trigger memory_entries_set_updated_at
before update on public.memory_entries
for each row execute procedure public.omni_set_updated_at();

drop trigger if exists documents_set_updated_at on public.documents;
create trigger documents_set_updated_at
before update on public.documents
for each row execute procedure public.omni_set_updated_at();

drop trigger if exists runtime_memory_embeddings_set_updated_at on public.runtime_memory_embeddings;
create trigger runtime_memory_embeddings_set_updated_at
before update on public.runtime_memory_embeddings
for each row execute procedure public.omni_set_updated_at();

alter table public.profiles enable row level security;
alter table public.user_settings enable row level security;
alter table public.chat_sessions enable row level security;
alter table public.chat_messages enable row level security;
alter table public.memory_entries enable row level security;
alter table public.documents enable row level security;
alter table public.document_chunks enable row level security;
alter table public.audit_events enable row level security;
alter table public.runtime_memory_embeddings enable row level security;

drop policy if exists profiles_select_own on public.profiles;
create policy profiles_select_own
on public.profiles
for select
to authenticated
using (auth.uid() = id);

drop policy if exists profiles_insert_own on public.profiles;
create policy profiles_insert_own
on public.profiles
for insert
to authenticated
with check (auth.uid() = id);

drop policy if exists profiles_update_own on public.profiles;
create policy profiles_update_own
on public.profiles
for update
to authenticated
using (auth.uid() = id)
with check (auth.uid() = id);

drop policy if exists profiles_delete_own on public.profiles;
create policy profiles_delete_own
on public.profiles
for delete
to authenticated
using (auth.uid() = id);

drop policy if exists user_settings_select_own on public.user_settings;
create policy user_settings_select_own
on public.user_settings
for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists user_settings_insert_own on public.user_settings;
create policy user_settings_insert_own
on public.user_settings
for insert
to authenticated
with check (auth.uid() = user_id);

drop policy if exists user_settings_update_own on public.user_settings;
create policy user_settings_update_own
on public.user_settings
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists user_settings_delete_own on public.user_settings;
create policy user_settings_delete_own
on public.user_settings
for delete
to authenticated
using (auth.uid() = user_id);

drop policy if exists chat_sessions_select_own on public.chat_sessions;
create policy chat_sessions_select_own
on public.chat_sessions
for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists chat_sessions_insert_own on public.chat_sessions;
create policy chat_sessions_insert_own
on public.chat_sessions
for insert
to authenticated
with check (auth.uid() = user_id);

drop policy if exists chat_sessions_update_own on public.chat_sessions;
create policy chat_sessions_update_own
on public.chat_sessions
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists chat_sessions_delete_own on public.chat_sessions;
create policy chat_sessions_delete_own
on public.chat_sessions
for delete
to authenticated
using (auth.uid() = user_id);

drop policy if exists chat_messages_select_own on public.chat_messages;
create policy chat_messages_select_own
on public.chat_messages
for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists chat_messages_insert_own on public.chat_messages;
create policy chat_messages_insert_own
on public.chat_messages
for insert
to authenticated
with check (
  auth.uid() = user_id
  and exists (
    select 1
    from public.chat_sessions s
    where s.id = session_id
      and s.user_id = auth.uid()
  )
);

drop policy if exists chat_messages_update_own on public.chat_messages;
create policy chat_messages_update_own
on public.chat_messages
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists chat_messages_delete_own on public.chat_messages;
create policy chat_messages_delete_own
on public.chat_messages
for delete
to authenticated
using (auth.uid() = user_id);

drop policy if exists memory_entries_select_own on public.memory_entries;
create policy memory_entries_select_own
on public.memory_entries
for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists memory_entries_insert_own on public.memory_entries;
create policy memory_entries_insert_own
on public.memory_entries
for insert
to authenticated
with check (auth.uid() = user_id);

drop policy if exists memory_entries_update_own on public.memory_entries;
create policy memory_entries_update_own
on public.memory_entries
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists memory_entries_delete_own on public.memory_entries;
create policy memory_entries_delete_own
on public.memory_entries
for delete
to authenticated
using (auth.uid() = user_id);

drop policy if exists documents_select_own on public.documents;
create policy documents_select_own
on public.documents
for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists documents_insert_own on public.documents;
create policy documents_insert_own
on public.documents
for insert
to authenticated
with check (auth.uid() = user_id);

drop policy if exists documents_update_own on public.documents;
create policy documents_update_own
on public.documents
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists documents_delete_own on public.documents;
create policy documents_delete_own
on public.documents
for delete
to authenticated
using (auth.uid() = user_id);

drop policy if exists document_chunks_select_own on public.document_chunks;
create policy document_chunks_select_own
on public.document_chunks
for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists document_chunks_insert_own on public.document_chunks;
create policy document_chunks_insert_own
on public.document_chunks
for insert
to authenticated
with check (
  auth.uid() = user_id
  and exists (
    select 1
    from public.documents d
    where d.id = document_id
      and d.user_id = auth.uid()
  )
);

drop policy if exists document_chunks_update_own on public.document_chunks;
create policy document_chunks_update_own
on public.document_chunks
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists document_chunks_delete_own on public.document_chunks;
create policy document_chunks_delete_own
on public.document_chunks
for delete
to authenticated
using (auth.uid() = user_id);

drop policy if exists audit_events_select_own on public.audit_events;
create policy audit_events_select_own
on public.audit_events
for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists audit_events_insert_own on public.audit_events;
create policy audit_events_insert_own
on public.audit_events
for insert
to authenticated
with check (auth.uid() = user_id or user_id is null);

drop policy if exists audit_events_update_own on public.audit_events;
create policy audit_events_update_own
on public.audit_events
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists audit_events_delete_own on public.audit_events;
create policy audit_events_delete_own
on public.audit_events
for delete
to authenticated
using (auth.uid() = user_id);

drop policy if exists runtime_memory_embeddings_select_own on public.runtime_memory_embeddings;
create policy runtime_memory_embeddings_select_own
on public.runtime_memory_embeddings
for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists runtime_memory_embeddings_insert_own on public.runtime_memory_embeddings;
create policy runtime_memory_embeddings_insert_own
on public.runtime_memory_embeddings
for insert
to authenticated
with check (auth.uid() = user_id);

drop policy if exists runtime_memory_embeddings_update_own on public.runtime_memory_embeddings;
create policy runtime_memory_embeddings_update_own
on public.runtime_memory_embeddings
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists runtime_memory_embeddings_delete_own on public.runtime_memory_embeddings;
create policy runtime_memory_embeddings_delete_own
on public.runtime_memory_embeddings
for delete
to authenticated
using (auth.uid() = user_id);

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'omni-documents',
  'omni-documents',
  false,
  52428800,
  array[
    'application/pdf',
    'text/plain',
    'text/markdown',
    'application/json',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ]
)
on conflict (id) do update
set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists omni_documents_read_own on storage.objects;
create policy omni_documents_read_own
on storage.objects
for select
to authenticated
using (
  bucket_id = 'omni-documents'
  and owner = auth.uid()
);

drop policy if exists omni_documents_insert_own on storage.objects;
create policy omni_documents_insert_own
on storage.objects
for insert
to authenticated
with check (
  bucket_id = 'omni-documents'
  and owner = auth.uid()
  and name like auth.uid()::text || '/%'
);

drop policy if exists omni_documents_update_own on storage.objects;
create policy omni_documents_update_own
on storage.objects
for update
to authenticated
using (
  bucket_id = 'omni-documents'
  and owner = auth.uid()
)
with check (
  bucket_id = 'omni-documents'
  and owner = auth.uid()
  and name like auth.uid()::text || '/%'
);

drop policy if exists omni_documents_delete_own on storage.objects;
create policy omni_documents_delete_own
on storage.objects
for delete
to authenticated
using (
  bucket_id = 'omni-documents'
  and owner = auth.uid()
);

commit;
