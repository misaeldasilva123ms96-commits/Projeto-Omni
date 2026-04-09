import { useState } from 'react'
import { ChatPage } from './pages/ChatPage'
import { DashboardPage } from './pages/DashboardPage'
import type { ChatMode } from './types'

type View = 'chat' | 'dashboard'

export default function App() {
  const [view, setView] = useState<View>('chat')
  const [mode, setMode] = useState<ChatMode>('chat')

  return (
    <>
      {view === 'chat' ? (
        <ChatPage
          mode={mode}
          onChangeMode={setMode}
          onChangeView={setView}
          view={view}
        />
      ) : (
        <DashboardPage
          mode={mode}
          onChangeMode={setMode}
          onChangeView={setView}
          view={view}
        />
      )}
    </>
  )
}
