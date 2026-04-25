import { Component, type ErrorInfo, type ReactNode } from 'react'

type ErrorBoundaryProps = {
  children: ReactNode
}

type ErrorBoundaryState = {
  error: Error | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = {
    error: null,
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[omni:error-boundary]', error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <main className="min-h-screen bg-cosmic-gradient px-6 py-10 text-slate-50">
          <section className="mx-auto max-w-2xl rounded-[28px] border border-rose-300/25 bg-rose-950/20 p-6 shadow-[0_24px_70px_rgba(0,0,0,0.36)] backdrop-blur-xl">
            <p className="mb-2 text-xs uppercase tracking-[0.3em] text-rose-200/80">Runtime UI boundary</p>
            <h1 className="mb-3 text-2xl font-semibold">A interface encontrou um erro seguro.</h1>
            <p className="text-sm leading-6 text-slate-200/80">
              O runtime visual foi interrompido para evitar uma tela quebrada. Recarregue a página ou confira o console
              para o stack técnico.
            </p>
            <pre className="mt-4 max-h-48 overflow-auto rounded-2xl border border-white/10 bg-black/30 p-3 text-xs text-rose-100/80">
              {this.state.error.message}
            </pre>
          </section>
        </main>
      )
    }

    return this.props.children
  }
}
