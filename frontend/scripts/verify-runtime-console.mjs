import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { join } from 'node:path'

const root = fileURLToPath(new URL('..', import.meta.url))
const read = (path) => readFileSync(join(root, path), 'utf8')

const chatPage = read('src/pages/ChatPage.tsx')
const chatPanel = read('src/components/chat/ChatPanel.tsx')
const sidebar = read('src/components/layout/Sidebar.tsx')
const runtimePanel = read('src/components/status/RuntimePanel.tsx')
const store = read('src/state/runtimeConsoleStore.ts')
const chatApi = read('src/lib/api/chat.ts')
const layout = read('src/components/layout/Layout.tsx')
const main = read('src/main.tsx')

assert.match(chatApi, /POST \/api\/v1\/chat|CHAT_V1_PATH = '\/api\/v1\/chat'/, 'chat API must prefer /api/v1/chat')
assert.match(chatApi, /CHAT_LEGACY_PATH = '\/chat'/, 'chat API must preserve legacy /chat fallback')
assert.match(chatApi, /if \(!trimmed\)/, 'empty chat messages must be rejected by transport')

assert.match(chatPage, /createMessage\('user', prompt\)/, 'user message must render immediately')
assert.match(chatPage, /isLoading: true/, 'assistant loading state must render while sending')
assert.match(chatPage, /setConsoleRuntimeMetadata\(metadata\)/, 'runtime metadata must be stored after success')
assert.match(chatPage, /streamAssistantMessage/, 'chat response must be stream-ready via simulated token rendering')
assert.match(chatPage, /handleSidebarItemSelected/, 'sidebar selections must be handled by ChatPage')
assert.match(chatPage, /handleTopActionSelect/, 'top actions must update runtime mode')

assert.match(store, /selectSidebarItem/, 'runtime console store must expose sidebar selection')
assert.match(store, /selectTopAction/, 'runtime console store must expose top action selection')
assert.match(store, /selectBottomTab/, 'runtime console store must expose bottom tab selection')
assert.match(store, /resetConversation/, 'runtime console store must expose resetConversation')
assert.match(store, /setRuntimeMetadata/, 'runtime console store must expose runtime metadata setter')

assert.match(sidebar, /onSidebarItemSelected/, 'sidebar clicks must notify page-level wiring')
assert.match(sidebar, /selectSidebarItem\(item\.id\)/, 'sidebar clicks must update central state')

assert.match(chatPanel, /onTopActionSelect/, 'top action clicks must notify page-level mode wiring')
assert.match(chatPanel, /selectBottomTab\(tab\.id\)/, 'bottom tabs must update central state')
assert.match(chatPanel, /disabled=\{!canSend \|\| loading\}/, 'send button must expose disabled state while empty or sending')
assert.match(chatPanel, /setUiNotice/, 'safe placeholders must provide visible feedback')
assert.match(chatPanel, /Entrada por voz ainda não está implementada/, 'voice button must fail safely')
assert.match(chatPanel, /Este módulo ainda não possui backend dedicado/, 'unsupported modules must be explicit')

assert.match(runtimePanel, /selectTopAction\(item\.id\)/, 'runtime panel action chips must be clickable')
assert.match(runtimePanel, /setUiNotice/, 'runtime panel dropdown must provide visible feedback')
assert.match(runtimePanel, /Debug Mode/, 'runtime panel must expose debug mode')
assert.match(runtimePanel, /debugPayload/, 'runtime panel must expose raw debug payload')

assert.match(layout, /mobilePanel/, 'layout must expose responsive panel state')
assert.match(layout, /Runtime/, 'layout must expose runtime tab for mobile/tablet')
assert.match(layout, /Tools/, 'layout must expose tools tab for mobile/tablet')
assert.match(main, /ErrorBoundary/, 'app root must be protected by ErrorBoundary')

console.log('runtime console wiring checks passed')
