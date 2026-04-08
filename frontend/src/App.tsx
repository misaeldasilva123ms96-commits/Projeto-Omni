import { useState } from 'react'
import { API_BASE_URL } from './lib/env'
import { AppHeader } from './components/AppHeader'
import { ChatPage } from './pages/ChatPage'
import { DashboardPage } from './pages/DashboardPage'

type View = 'chat' | 'dashboard'

export default function App() {
  const [view, setView] = useState<View>('chat')

  return (
    <main className="app-shell">
      <div className="app-frame">
        <AppHeader
          activeView={view}
          apiBaseUrl={API_BASE_URL}
          onChangeView={setView}
        />
        {view === 'chat' ? <ChatPage /> : <DashboardPage />}
      </div>
    </main>
  )
}
