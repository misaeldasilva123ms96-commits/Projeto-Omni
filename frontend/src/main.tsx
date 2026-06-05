import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './app/App'
import { ErrorBoundary } from './components/ErrorBoundary'
import { OmniThemeProvider } from './components/ui/OmniThemeProvider'
import './styles.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <OmniThemeProvider>
        <App />
      </OmniThemeProvider>
    </ErrorBoundary>
  </React.StrictMode>,
)
