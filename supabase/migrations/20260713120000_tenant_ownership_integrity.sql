begin;

-- Composite candidate keys let child rows prove that the referenced parent
-- belongs to the same tenant, rather than relying on application ordering.
alter table public.chat_sessions
  add constraint chat_sessions_id_user_unique unique (id, user_id);
alter table public.documents
  add constraint documents_id_user_unique unique (id, user_id);

alter table public.chat_messages
  drop constraint if exists chat_messages_session_id_fkey;
alter table public.chat_messages
  add constraint chat_messages_session_owner_fkey
  foreign key (session_id, user_id)
  references public.chat_sessions (id, user_id)
  on delete cascade;

alter table public.memory_entries
  drop constraint if exists memory_entries_session_id_fkey;
alter table public.memory_entries
  add constraint memory_entries_session_owner_fkey
  foreign key (session_id, user_id)
  references public.chat_sessions (id, user_id)
  on delete set null (session_id);

alter table public.documents
  drop constraint if exists documents_session_id_fkey;
alter table public.documents
  add constraint documents_session_owner_fkey
  foreign key (session_id, user_id)
  references public.chat_sessions (id, user_id)
  on delete set null (session_id);

alter table public.document_chunks
  drop constraint if exists document_chunks_document_id_fkey;
alter table public.document_chunks
  add constraint document_chunks_document_owner_fkey
  foreign key (document_id, user_id)
  references public.documents (id, user_id)
  on delete cascade;

create index if not exists chat_messages_session_user_idx
  on public.chat_messages (session_id, user_id);
create index if not exists memory_entries_session_user_idx
  on public.memory_entries (session_id, user_id);
create index if not exists documents_session_user_idx
  on public.documents (session_id, user_id);
create index if not exists document_chunks_document_user_idx
  on public.document_chunks (document_id, user_id);

drop policy if exists chat_messages_update_own on public.chat_messages;
create policy chat_messages_update_own on public.chat_messages
for update to authenticated
using ((select auth.uid()) = user_id)
with check (
  (select auth.uid()) = user_id
  and exists (
    select 1 from public.chat_sessions s
    where s.id = session_id and s.user_id = (select auth.uid())
  )
);

drop policy if exists memory_entries_insert_own on public.memory_entries;
create policy memory_entries_insert_own on public.memory_entries
for insert to authenticated
with check (
  (select auth.uid()) = user_id
  and (session_id is null or exists (
    select 1 from public.chat_sessions s
    where s.id = session_id and s.user_id = (select auth.uid())
  ))
);
drop policy if exists memory_entries_update_own on public.memory_entries;
create policy memory_entries_update_own on public.memory_entries
for update to authenticated
using ((select auth.uid()) = user_id)
with check (
  (select auth.uid()) = user_id
  and (session_id is null or exists (
    select 1 from public.chat_sessions s
    where s.id = session_id and s.user_id = (select auth.uid())
  ))
);

drop policy if exists documents_insert_own on public.documents;
create policy documents_insert_own on public.documents
for insert to authenticated
with check (
  (select auth.uid()) = user_id
  and (session_id is null or exists (
    select 1 from public.chat_sessions s
    where s.id = session_id and s.user_id = (select auth.uid())
  ))
);
drop policy if exists documents_update_own on public.documents;
create policy documents_update_own on public.documents
for update to authenticated
using ((select auth.uid()) = user_id)
with check (
  (select auth.uid()) = user_id
  and (session_id is null or exists (
    select 1 from public.chat_sessions s
    where s.id = session_id and s.user_id = (select auth.uid())
  ))
);

drop policy if exists document_chunks_update_own on public.document_chunks;
create policy document_chunks_update_own on public.document_chunks
for update to authenticated
using ((select auth.uid()) = user_id)
with check (
  (select auth.uid()) = user_id
  and exists (
    select 1 from public.documents d
    where d.id = document_id and d.user_id = (select auth.uid())
  )
);

-- Authenticated audit events must always be attributable to their caller.
drop policy if exists audit_events_insert_own on public.audit_events;
create policy audit_events_insert_own on public.audit_events
for insert to authenticated
with check ((select auth.uid()) = user_id);

commit;
