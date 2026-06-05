import type { ChatMessage, ChatMode, ConversationSummary, RuntimeMetadata } from '../types'
import { supabase } from './supabase'

type AuthenticatedUser = {
  id: string
  email?: string | null
  user_metadata?: Record<string, unknown>
}

type SyncChatSessionInput = {
  externalSessionId: string
  mode: ChatMode
  title: string
  status: 'active' | 'idle' | 'completed' | 'failed' | 'degraded'
  summary?: string
  metadata?: RuntimeMetadata | null
  messages: ChatMessage[]
}

async function getAuthenticatedUser(): Promise<AuthenticatedUser | null> {
  const { data, error } = await supabase.auth.getUser()
  if (error) {
    throw error
  }

  return data.user
}

function buildProfilePayload(user: AuthenticatedUser) {
  const metadata = user.user_metadata ?? {}
  const displayName =
    typeof metadata.display_name === 'string'
      ? metadata.display_name
      : typeof metadata.name === 'string'
        ? metadata.name
        : null

  return {
    id: user.id,
    email: user.email ?? null,
    display_name: displayName,
    avatar_url:
      typeof metadata.avatar_url === 'string' ? metadata.avatar_url : null,
    metadata,
  }
}

function buildSettingsPayload(userId: string) {
  return {
    user_id: userId,
    interface_mode: 'chat',
    language:
      typeof navigator !== 'undefined' && navigator.language
        ? navigator.language
        : 'pt-BR',
    timezone:
      Intl.DateTimeFormat().resolvedOptions().timeZone || 'America/Sao_Paulo',
  }
}

function buildSessionPayload(
  userId: string,
  input: SyncChatSessionInput,
) {
  return {
    user_id: userId,
    external_session_id: input.externalSessionId,
    title: input.title,
    mode: input.mode,
    status: input.status,
    summary: input.summary ?? null,
    metadata: {
      ...(input.metadata ?? {}),
      message_count: input.messages.length,
    },
  }
}

function buildMessagePayloads(
  userId: string,
  sessionId: string,
  messages: ChatMessage[],
) {
  return messages.map((message) => ({
    external_message_id: message.id,
    session_id: sessionId,
    user_id: userId,
    role: message.role,
    content: message.content,
    metadata: {
      request_state: message.requestState ?? null,
      runtime_metadata: message.metadata ?? null,
    },
    created_at: message.createdAt,
  }))
}

export async function bootstrapOmniUser() {
  const user = await getAuthenticatedUser()
  if (!user) {
    return null
  }

  const { error: profileError } = await supabase
    .from('profiles')
    .upsert(buildProfilePayload(user), { onConflict: 'id' })

  if (profileError) {
    throw profileError
  }

  const { error: settingsError } = await supabase
    .from('user_settings')
    .upsert(buildSettingsPayload(user.id), { onConflict: 'user_id' })

  if (settingsError) {
    throw settingsError
  }

  return user
}

export async function syncChatSessionToSupabase(input: SyncChatSessionInput) {
  const user = await getAuthenticatedUser()
  if (!user || input.messages.length === 0) {
    return null
  }

  await bootstrapOmniUser()

  const { data: sessionRow, error: sessionError } = await supabase
    .from('chat_sessions')
    .upsert(buildSessionPayload(user.id, input), { onConflict: 'external_session_id' })
    .select('id')
    .single()

  if (sessionError) {
    throw sessionError
  }

  const messagePayloads = buildMessagePayloads(user.id, sessionRow.id, input.messages)
  const { error: messageError } = await supabase
    .from('chat_messages')
    .upsert(messagePayloads, { onConflict: 'external_message_id' })

  if (messageError) {
    throw messageError
  }

  return sessionRow.id as string
}

export async function fetchChatSessions(): Promise<ConversationSummary[]> {
  try {
    const user = await getAuthenticatedUser()
    if (!user) return []

    const { data, error } = await supabase
      .from('chat_sessions')
      .select('external_session_id, title, mode, status, metadata, updated_at')
      .eq('user_id', user.id)
      .order('updated_at', { ascending: false })
      .limit(50)

    if (error) throw error
    if (!data || data.length === 0) return []

    return data.map((row: Record<string, unknown>) => {
      const meta = (row.metadata as Record<string, unknown>) ?? {}
      return {
        id: String(row.external_session_id ?? ''),
        title: String(row.title ?? ''),
        updatedAt: String(row.updated_at ?? new Date().toISOString()),
        messageCount: typeof meta.message_count === 'number' ? meta.message_count : 0,
        mode: (['chat', 'pesquisa', 'codigo', 'agente'].includes(String(row.mode)) ? String(row.mode) : 'chat') as ConversationSummary['mode'],
      }
    })
  } catch {
    return []
  }
}

export async function fetchChatMessages(
  externalSessionId: string,
): Promise<ChatMessage[]> {
  try {
    const user = await getAuthenticatedUser()
    if (!user) return []

    const { data: sessionRow, error: sessionError } = await supabase
      .from('chat_sessions')
      .select('id')
      .eq('external_session_id', externalSessionId)
      .eq('user_id', user.id)
      .single()

    if (sessionError || !sessionRow) return []

    const { data: messages, error: messagesError } = await supabase
      .from('chat_messages')
      .select('external_message_id, role, content, metadata, created_at')
      .eq('session_id', sessionRow.id)
      .order('created_at', { ascending: true })

    if (messagesError) throw messagesError
    if (!messages || messages.length === 0) return []

    return messages.map((row: Record<string, unknown>) => {
      const meta = (row.metadata as Record<string, unknown>) ?? {}
      return {
        id: String(row.external_message_id ?? crypto.randomUUID()),
        role: (['user', 'assistant', 'system'].includes(String(row.role)) ? String(row.role) : 'user') as ChatMessage['role'],
        content: String(row.content ?? ''),
        createdAt: String(row.created_at ?? new Date().toISOString()),
        requestState: (meta.request_state as ChatMessage['requestState']) ?? undefined,
        metadata: meta.runtime_metadata as RuntimeMetadata | undefined,
      }
    })
  } catch {
    return []
  }
}
