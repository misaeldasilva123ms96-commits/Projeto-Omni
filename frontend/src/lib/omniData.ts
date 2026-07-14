import type { Agent, AgentStatus, ChatMessage, ChatMode, ConversationSummary, GovernanceDecision, MemoryEntry, MemoryType, Project, ProjectStatus, RuntimeMetadata, TokenUsageSummary } from '../types'
import { redactRuntimeDebugText } from './runtimeDebugSanitizer'
import { normalizeAutonomyTimelineItem, type AutonomyTimelineItem } from './runtimeTypes'
import { supabase } from './supabase'
import { readMigratedStorage, writeMigratedStorage } from './storageKeyMigration'

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

export async function fetchProjects(): Promise<Project[]> {
  try {
    const user = await getAuthenticatedUser()
    if (!user) return localStorageProjects()

    const { data, error } = await supabase
      .from('projects')
      .select('id, name, description, status, mode, metadata, created_at, updated_at')
      .eq('user_id', user.id)
      .order('updated_at', { ascending: false })
      .limit(50)

    if (error) throw error
    if (!data || data.length === 0) return localStorageProjects()

    const projects: Project[] = data.map((row: Record<string, unknown>) => {
      const meta = (row.metadata as Record<string, unknown>) ?? {}
      return {
        id: String(row.id ?? ''),
        name: String(row.name ?? ''),
        description: String(row.description ?? ''),
        status: (['active', 'archived'].includes(String(row.status)) ? String(row.status) : 'active') as ProjectStatus,
        mode: (['chat', 'pesquisa', 'codigo', 'agente'].includes(String(row.mode)) ? String(row.mode) : 'chat') as ChatMode,
        sessionCount: typeof meta.session_count === 'number' ? meta.session_count : 0,
        createdAt: String(row.created_at ?? new Date().toISOString()),
        updatedAt: String(row.updated_at ?? new Date().toISOString()),
      }
    })

    return projects
  } catch {
    return localStorageProjects()
  }
}

export async function createProject(
  input: { name: string; description?: string; mode?: ChatMode },
): Promise<Project | null> {
  try {
    const user = await getAuthenticatedUser()
    if (!user) return localStorageCreateProject(input)

    const { data, error } = await supabase
      .from('projects')
      .insert({
        user_id: user.id,
        name: input.name,
        description: input.description ?? '',
        status: 'active',
        mode: input.mode ?? 'chat',
        metadata: { session_count: 0 },
      })
      .select('id, name, description, status, mode, metadata, created_at, updated_at')
      .single()

    if (error) throw error
    if (!data) return null

    const meta = (data.metadata as Record<string, unknown>) ?? {}
    return {
      id: String(data.id),
      name: String(data.name),
      description: String(data.description ?? ''),
      status: 'active',
      mode: (['chat', 'pesquisa', 'codigo', 'agente'].includes(String(data.mode)) ? String(data.mode) : 'chat') as ChatMode,
      sessionCount: typeof meta.session_count === 'number' ? meta.session_count : 0,
      createdAt: String(data.created_at ?? new Date().toISOString()),
      updatedAt: String(data.updated_at ?? new Date().toISOString()),
    }
  } catch {
    return localStorageCreateProject(input)
  }
}

export async function updateProject(
  id: string,
  input: { name?: string; description?: string; status?: ProjectStatus; mode?: ChatMode },
): Promise<Project | null> {
  try {
    const user = await getAuthenticatedUser()
    if (!user) return localStorageUpdateProject(id, input)

    const payload: Record<string, unknown> = {}
    if (input.name !== undefined) payload.name = input.name
    if (input.description !== undefined) payload.description = input.description
    if (input.status !== undefined) payload.status = input.status
    if (input.mode !== undefined) payload.mode = input.mode

    const { data, error } = await supabase
      .from('projects')
      .update(payload)
      .eq('id', id)
      .eq('user_id', user.id)
      .select('id, name, description, status, mode, metadata, created_at, updated_at')
      .single()

    if (error) throw error
    if (!data) return null

    const meta = (data.metadata as Record<string, unknown>) ?? {}
    return {
      id: String(data.id),
      name: String(data.name),
      description: String(data.description ?? ''),
      status: (['active', 'archived'].includes(String(data.status)) ? String(data.status) : 'active') as ProjectStatus,
      mode: (['chat', 'pesquisa', 'codigo', 'agente'].includes(String(data.mode)) ? String(data.mode) : 'chat') as ChatMode,
      sessionCount: typeof meta.session_count === 'number' ? meta.session_count : 0,
      createdAt: String(data.created_at ?? new Date().toISOString()),
      updatedAt: String(data.updated_at ?? new Date().toISOString()),
    }
  } catch {
    return localStorageUpdateProject(id, input)
  }
}

export async function deleteProject(id: string): Promise<boolean> {
  try {
    const user = await getAuthenticatedUser()
    if (!user) return localStorageDeleteProject(id)

    const { error } = await supabase
      .from('projects')
      .delete()
      .eq('id', id)
      .eq('user_id', user.id)

    if (error) throw error
    localStorageRemoveProject(id)
    return true
  } catch {
    return localStorageDeleteProject(id)
  }
}

const PROJECTS_STORAGE_KEY = 'omni-projects-v1'
const LEGACY_PROJECTS_STORAGE_KEY = 'omini-projects-v1'

function localStorageProjects(): Project[] {
  try {
    const raw = readMigratedStorage(PROJECTS_STORAGE_KEY, LEGACY_PROJECTS_STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed
  } catch {
    return []
  }
}

function localStorageCreateProject(input: { name: string; description?: string; mode?: ChatMode }): Project | null {
  try {
    const projects = localStorageProjects()
    const project: Project = {
      id: crypto.randomUUID(),
      name: input.name,
      description: input.description ?? '',
      status: 'active',
      mode: input.mode ?? 'chat',
      sessionCount: 0,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    projects.unshift(project)
    writeMigratedStorage(PROJECTS_STORAGE_KEY, LEGACY_PROJECTS_STORAGE_KEY, JSON.stringify(projects))
    return project
  } catch {
    return null
  }
}

function localStorageUpdateProject(
  id: string,
  input: { name?: string; description?: string; status?: ProjectStatus; mode?: ChatMode },
): Project | null {
  try {
    const projects = localStorageProjects()
    const index = projects.findIndex((p: Project) => p.id === id)
    if (index === -1) return null
    const project = { ...projects[index] }
    if (input.name !== undefined) project.name = input.name
    if (input.description !== undefined) project.description = input.description
    if (input.status !== undefined) project.status = input.status
    if (input.mode !== undefined) project.mode = input.mode
    project.updatedAt = new Date().toISOString()
    projects[index] = project
    writeMigratedStorage(PROJECTS_STORAGE_KEY, LEGACY_PROJECTS_STORAGE_KEY, JSON.stringify(projects))
    return project
  } catch {
    return null
  }
}

function localStorageDeleteProject(id: string): boolean {
  try {
    const projects = localStorageProjects()
    const filtered = projects.filter((p: Project) => p.id !== id)
    if (filtered.length === projects.length) return false
    writeMigratedStorage(PROJECTS_STORAGE_KEY, LEGACY_PROJECTS_STORAGE_KEY, JSON.stringify(filtered))
    return true
  } catch {
    return false
  }
}

export async function fetchTokenUsage(): Promise<TokenUsageSummary> {
  const empty: TokenUsageSummary = {
    totalInputTokens: 0,
    totalOutputTokens: 0,
    totalTokens: 0,
    totalRequests: 0,
    avgTokensPerRequest: 0,
    byDate: [],
  }

  try {
    const conversations = await fetchChatSessions()
    if (conversations.length === 0) return empty

    const dailyMap = new Map<string, { input: number; output: number; count: number }>()

    for (const conv of conversations) {
      const messages = await fetchChatMessages(conv.id)
      for (const msg of messages) {
        const usage = msg.metadata?.usage
        if (!usage) continue

        const input = usage.input_tokens ?? 0
        const output = usage.output_tokens ?? 0
        if (input === 0 && output === 0) continue

        const day = msg.createdAt.slice(0, 10)
        const entry = dailyMap.get(day) ?? { input: 0, output: 0, count: 0 }
        entry.input += input
        entry.output += output
        entry.count += 1
        dailyMap.set(day, entry)
      }
    }

    const byDate: TokenUsageSummary['byDate'] = []
    let totalInputTokens = 0
    let totalOutputTokens = 0
    let totalRequests = 0

    for (const [date, vals] of dailyMap) {
      const totalTokens = vals.input + vals.output
      byDate.push({
        date,
        inputTokens: vals.input,
        outputTokens: vals.output,
        totalTokens,
        requestCount: vals.count,
      })
      totalInputTokens += vals.input
      totalOutputTokens += vals.output
      totalRequests += vals.count
    }

    byDate.sort((a, b) => a.date.localeCompare(b.date))

    const totalTokens = totalInputTokens + totalOutputTokens

    return {
      totalInputTokens,
      totalOutputTokens,
      totalTokens,
      totalRequests,
      avgTokensPerRequest: totalRequests > 0 ? Math.round(totalTokens / totalRequests) : 0,
      byDate,
    }
  } catch {
    return empty
  }
}

export async function fetchGovernanceDecisions(): Promise<GovernanceDecision[]> {
  try {
    const conversations = await fetchChatSessions()
    const decisions: GovernanceDecision[] = []

    for (const conv of conversations) {
      const messages = await fetchChatMessages(conv.id)
      for (const msg of messages) {
        const inspection = msg.metadata?.cognitiveRuntimeInspection
        if (!inspection || typeof inspection !== 'object') continue

        const raw = (inspection as Record<string, unknown>).governance as Record<string, unknown> | undefined
        if (!raw || typeof raw !== 'object') continue

        const decision = String(raw.decision ?? '')
        if (!['allowed', 'blocked', 'requires_approval', 'unknown'].includes(decision)) continue

        const riskLevelRaw = String(raw.riskLevel ?? '')
        const riskLevel = ['low', 'medium', 'high', 'critical'].includes(riskLevelRaw)
          ? (riskLevelRaw as GovernanceDecision['riskLevel'])
          : undefined

        decisions.push({
          id: `${conv.id}-${msg.id}`,
          sessionId: conv.id,
          decision: decision as GovernanceDecision['decision'],
          category: redactRuntimeDebugText(String(raw.category ?? '')),
          policy: redactRuntimeDebugText(String(raw.policy ?? '')),
          reason: redactRuntimeDebugText(String(raw.reason ?? '')),
          riskLevel,
          timestamp: msg.createdAt,
        })
      }
    }

    decisions.sort((a, b) => b.timestamp.localeCompare(a.timestamp))
    return decisions
  } catch {
    return []
  }
}

export async function fetchAutonomyTimeline(): Promise<AutonomyTimelineItem[]> {
  try {
    const conversations = await fetchChatSessions()
    const items: AutonomyTimelineItem[] = []

    for (const conv of conversations) {
      const messages = await fetchChatMessages(conv.id)
      for (const msg of messages) {
        const inspection = msg.metadata?.cognitiveRuntimeInspection
        if (!inspection || typeof inspection !== 'object') continue

        const raw = (inspection as Record<string, unknown>).autonomy_evaluation as Record<string, unknown> | undefined
        if (!raw || typeof raw !== 'object') continue

        const item = normalizeAutonomyTimelineItem(raw, msg.id, conv.id, msg.createdAt)
        if (item) items.push(item)
      }
    }

    items.sort((a, b) => b.timestamp.localeCompare(a.timestamp))
    return items
  } catch {
    return []
  }
}

const AGENTS_STORAGE_KEY = 'omni-agents-v1'
const LEGACY_AGENTS_STORAGE_KEY = 'omini-agents-v1'

function localStorageAgents(): Agent[] {
  try {
    const raw = readMigratedStorage(AGENTS_STORAGE_KEY, LEGACY_AGENTS_STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed
  } catch {
    return []
  }
}

function saveLocalStorageAgents(agents: Agent[]) {
  try {
    writeMigratedStorage(AGENTS_STORAGE_KEY, LEGACY_AGENTS_STORAGE_KEY, JSON.stringify(agents))
  } catch {
    // ignore
  }
}

export async function fetchAgents(): Promise<Agent[]> {
  return localStorageAgents()
}

export async function createAgent(
  input: { name: string; description?: string; model: string; provider: string; tools?: string[] },
): Promise<Agent | null> {
  try {
    const agents = localStorageAgents()
    const agent: Agent = {
      id: crypto.randomUUID(),
      name: input.name,
      description: input.description ?? '',
      model: input.model,
      provider: input.provider,
      tools: input.tools ?? [],
      status: 'active',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    agents.unshift(agent)
    saveLocalStorageAgents(agents)
    return agent
  } catch {
    return null
  }
}

export async function updateAgent(
  id: string,
  input: { name?: string; description?: string; model?: string; provider?: string; tools?: string[]; status?: AgentStatus },
): Promise<Agent | null> {
  try {
    const agents = localStorageAgents()
    const index = agents.findIndex((a) => a.id === id)
    if (index === -1) return null
    const agent = { ...agents[index] }
    if (input.name !== undefined) agent.name = input.name
    if (input.description !== undefined) agent.description = input.description
    if (input.model !== undefined) agent.model = input.model
    if (input.provider !== undefined) agent.provider = input.provider
    if (input.tools !== undefined) agent.tools = input.tools
    if (input.status !== undefined) agent.status = input.status
    agent.updatedAt = new Date().toISOString()
    agents[index] = agent
    saveLocalStorageAgents(agents)
    return agent
  } catch {
    return null
  }
}

export async function deleteAgent(id: string): Promise<boolean> {
  try {
    const agents = localStorageAgents()
    const filtered = agents.filter((a) => a.id !== id)
    if (filtered.length === agents.length) return false
    saveLocalStorageAgents(filtered)
    return true
  } catch {
    return false
  }
}

const MEMORY_STORAGE_KEY = 'omni-memory-v1'
const LEGACY_MEMORY_STORAGE_KEY = 'omini-memory-v1'

function localStorageMemoryEntries(): MemoryEntry[] {
  try {
    const raw = readMigratedStorage(MEMORY_STORAGE_KEY, LEGACY_MEMORY_STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed
  } catch {
    return []
  }
}

function saveLocalStorageMemoryEntries(entries: MemoryEntry[]) {
  try {
    writeMigratedStorage(MEMORY_STORAGE_KEY, LEGACY_MEMORY_STORAGE_KEY, JSON.stringify(entries))
  } catch {
    // ignore
  }
}

export async function fetchMemoryEntries(): Promise<MemoryEntry[]> {
  try {
    const user = await getAuthenticatedUser()
    if (!user) return localStorageMemoryEntries()

    const { data, error } = await supabase
      .from('memory_entries')
      .select('id, memory_type, title, summary, content, source, importance, tags, is_pinned, session_id, created_at, updated_at')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false })
      .limit(50)

    if (error) throw error
    if (!data || data.length === 0) return localStorageMemoryEntries()

    return data.map((row: Record<string, unknown>) => {
      const content = row.content as Record<string, unknown> ?? {}
      const tags = row.tags as string[] ?? []
      const rawType = String(row.memory_type ?? 'working')
      const memoryType = (['working', 'episodic', 'semantic', 'procedural'].includes(rawType) ? rawType : 'working') as MemoryType
      return {
        id: String(row.id ?? ''),
        memoryType,
        title: String(row.title ?? ''),
        summary: String(row.summary ?? ''),
        content,
        source: String(row.source ?? ''),
        importance: typeof row.importance === 'number' ? row.importance : 0,
        tags,
        isPinned: row.is_pinned === true,
        sessionId: row.session_id ? String(row.session_id) : null,
        createdAt: String(row.created_at ?? new Date().toISOString()),
        updatedAt: String(row.updated_at ?? new Date().toISOString()),
      }
    })
  } catch {
    return localStorageMemoryEntries()
  }
}

export async function createMemoryEntry(
  input: {
    memoryType: MemoryType
    title: string
    summary?: string
    content?: Record<string, unknown>
    source?: string
    importance?: number
    tags?: string[]
    isPinned?: boolean
    sessionId?: string | null
  },
): Promise<MemoryEntry | null> {
  try {
    const user = await getAuthenticatedUser()
    if (user) {
      const { data, error } = await supabase
        .from('memory_entries')
        .insert({
          user_id: user.id,
          memory_type: input.memoryType,
          title: input.title,
          summary: input.summary ?? '',
          content: input.content ?? {},
          source: input.source ?? '',
          importance: input.importance ?? 0,
          tags: input.tags ?? [],
          is_pinned: input.isPinned ?? false,
          session_id: input.sessionId ?? null,
        })
        .select('id, memory_type, title, summary, content, source, importance, tags, is_pinned, session_id, created_at, updated_at')
        .single()

      if (!error && data) {
        return mapMemoryRow(data as Record<string, unknown>)
      }
    }

    const entries = localStorageMemoryEntries()
    const entry: MemoryEntry = {
      id: crypto.randomUUID(),
      memoryType: input.memoryType,
      title: input.title,
      summary: input.summary ?? '',
      content: input.content ?? {},
      source: input.source ?? '',
      importance: input.importance ?? 0,
      tags: input.tags ?? [],
      isPinned: input.isPinned ?? false,
      sessionId: input.sessionId ?? null,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    entries.unshift(entry)
    saveLocalStorageMemoryEntries(entries)
    return entry
  } catch {
    return localStorageCreateMemoryEntry(input)
  }
}

function localStorageCreateMemoryEntry(
  input: {
    memoryType: MemoryType
    title: string
    summary?: string
    content?: Record<string, unknown>
    source?: string
    importance?: number
    tags?: string[]
    isPinned?: boolean
    sessionId?: string | null
  },
): MemoryEntry | null {
  try {
    const entries = localStorageMemoryEntries()
    const entry: MemoryEntry = {
      id: crypto.randomUUID(),
      memoryType: input.memoryType,
      title: input.title,
      summary: input.summary ?? '',
      content: input.content ?? {},
      source: input.source ?? '',
      importance: input.importance ?? 0,
      tags: input.tags ?? [],
      isPinned: input.isPinned ?? false,
      sessionId: input.sessionId ?? null,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    entries.unshift(entry)
    saveLocalStorageMemoryEntries(entries)
    return entry
  } catch {
    return null
  }
}

export async function updateMemoryEntry(
  id: string,
  input: {
    title?: string
    summary?: string
    content?: Record<string, unknown>
    source?: string
    importance?: number
    tags?: string[]
    isPinned?: boolean
  },
): Promise<MemoryEntry | null> {
  try {
    const user = await getAuthenticatedUser()
    if (user) {
      const payload: Record<string, unknown> = {}
      if (input.title !== undefined) payload.title = input.title
      if (input.summary !== undefined) payload.summary = input.summary
      if (input.content !== undefined) payload.content = input.content
      if (input.source !== undefined) payload.source = input.source
      if (input.importance !== undefined) payload.importance = input.importance
      if (input.tags !== undefined) payload.tags = input.tags
      if (input.isPinned !== undefined) payload.is_pinned = input.isPinned

      const { data, error } = await supabase
        .from('memory_entries')
        .update(payload)
        .eq('id', id)
        .eq('user_id', user.id)
        .select('id, memory_type, title, summary, content, source, importance, tags, is_pinned, session_id, created_at, updated_at')
        .single()

      if (!error && data) {
        return mapMemoryRow(data as Record<string, unknown>)
      }
    }

    const entries = localStorageMemoryEntries()
    const index = entries.findIndex((e) => e.id === id)
    if (index === -1) return null
    const entry = { ...entries[index] }
    if (input.title !== undefined) entry.title = input.title
    if (input.summary !== undefined) entry.summary = input.summary
    if (input.content !== undefined) entry.content = input.content
    if (input.source !== undefined) entry.source = input.source
    if (input.importance !== undefined) entry.importance = input.importance
    if (input.tags !== undefined) entry.tags = input.tags
    if (input.isPinned !== undefined) entry.isPinned = input.isPinned
    entry.updatedAt = new Date().toISOString()
    entries[index] = entry
    saveLocalStorageMemoryEntries(entries)
    return entry
  } catch {
    return null
  }
}

export async function deleteMemoryEntry(id: string): Promise<boolean> {
  try {
    const user = await getAuthenticatedUser()
    if (user) {
      const { error } = await supabase
        .from('memory_entries')
        .delete()
        .eq('id', id)
        .eq('user_id', user.id)

      if (!error) {
        localStorageRemoveMemoryEntry(id)
        return true
      }
    }

    const entries = localStorageMemoryEntries()
    const filtered = entries.filter((e) => e.id !== id)
    if (filtered.length === entries.length) return false
    saveLocalStorageMemoryEntries(filtered)
    return true
  } catch {
    return false
  }
}

function localStorageRemoveMemoryEntry(id: string) {
  try {
    const entries = localStorageMemoryEntries()
    const filtered = entries.filter((e) => e.id !== id)
    saveLocalStorageMemoryEntries(filtered)
  } catch {
    // ignore
  }
}

function mapMemoryRow(row: Record<string, unknown>): MemoryEntry {
  const content = row.content as Record<string, unknown> ?? {}
  const tags = row.tags as string[] ?? []
  const rawType = String(row.memory_type ?? 'working')
  const memoryType = (['working', 'episodic', 'semantic', 'procedural'].includes(rawType) ? rawType : 'working') as MemoryType
  return {
    id: String(row.id ?? ''),
    memoryType,
    title: String(row.title ?? ''),
    summary: String(row.summary ?? ''),
    content,
    source: String(row.source ?? ''),
    importance: typeof row.importance === 'number' ? row.importance : 0,
    tags,
    isPinned: row.is_pinned === true,
    sessionId: row.session_id ? String(row.session_id) : null,
    createdAt: String(row.created_at ?? new Date().toISOString()),
    updatedAt: String(row.updated_at ?? new Date().toISOString()),
  }
}

function localStorageRemoveProject(id: string) {
  try {
    const projects = localStorageProjects()
    const filtered = projects.filter((p: Project) => p.id !== id)
    writeMigratedStorage(PROJECTS_STORAGE_KEY, LEGACY_PROJECTS_STORAGE_KEY, JSON.stringify(filtered))
  } catch {
    // ignore
  }
}
