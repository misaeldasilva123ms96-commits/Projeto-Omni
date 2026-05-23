export const PUTER_SCRIPT_LOADER_VERSION = 'puter_script_loader_v1'
export const PUTER_SCRIPT_ID = 'omni-puter-dev-script'
export const PUTER_SCRIPT_SRC = 'https://js.puter.com/v2/'

export type PuterScriptLoaderStatus = 'idle' | 'loading' | 'loaded' | 'unavailable' | 'failed'

export type PuterScriptLoaderResult = {
  loader_version: typeof PUTER_SCRIPT_LOADER_VERSION
  status: PuterScriptLoaderStatus
  reason: string
  script_src: typeof PUTER_SCRIPT_SRC
}

export type PuterScriptLoaderInput = {
  devSurfaceEnabled?: boolean
  experimentalFeatureEnabled?: boolean
  runtime?: unknown
  timeoutMs?: number
}

type PuterWindow = Window & {
  puter?: {
    ai?: {
      chat?: unknown
    }
  }
}

export function createPuterScriptLoaderResult(
  status: PuterScriptLoaderStatus = 'idle',
  reason = 'not_started',
): PuterScriptLoaderResult {
  return {
    loader_version: PUTER_SCRIPT_LOADER_VERSION,
    status,
    reason: safeReason(reason),
    script_src: PUTER_SCRIPT_SRC,
  }
}

export async function loadPuterScriptRuntime({
  devSurfaceEnabled,
  experimentalFeatureEnabled,
  runtime,
  timeoutMs = 10000,
}: PuterScriptLoaderInput): Promise<PuterScriptLoaderResult> {
  if (experimentalFeatureEnabled !== true || devSurfaceEnabled !== true) {
    return createPuterScriptLoaderResult('unavailable', 'feature_disabled')
  }

  const browserWindow = getBrowserWindow(runtime)
  if (!browserWindow?.document) {
    return createPuterScriptLoaderResult('unavailable', 'non_browser_runtime')
  }

  if (hasPuterChat(browserWindow)) {
    return createPuterScriptLoaderResult('loaded', 'puter_available')
  }

  const existingScript = findPuterScript(browserWindow.document)
  if (existingScript) {
    if (existingScript.src !== PUTER_SCRIPT_SRC) {
      return createPuterScriptLoaderResult('failed', 'script_src_mismatch')
    }
    if (existingScript.dataset.omniPuterStatus === 'loaded') {
      return createPuterScriptLoaderResult('unavailable', 'puter_unavailable_after_load')
    }
    return waitForPuterScript(browserWindow, existingScript, timeoutMs)
  }

  const script = browserWindow.document.createElement('script')
  script.id = PUTER_SCRIPT_ID
  script.src = PUTER_SCRIPT_SRC
  script.async = true
  script.dataset.omniPuterStatus = 'loading'
  browserWindow.document.head.appendChild(script)

  return waitForPuterScript(browserWindow, script, timeoutMs)
}

function waitForPuterScript(
  browserWindow: PuterWindow,
  script: HTMLScriptElement,
  timeoutMs: number,
): Promise<PuterScriptLoaderResult> {
  script.dataset.omniPuterStatus = 'loading'

  return new Promise((resolve) => {
    let settled = false
    const timeout = browserWindow.setTimeout(() => {
      finish('failed', 'script_load_timeout')
    }, timeoutMs)

    function finish(status: PuterScriptLoaderStatus, reason: string) {
      if (settled) {
        return
      }
      settled = true
      browserWindow.clearTimeout(timeout)
      script.removeEventListener('load', handleLoad)
      script.removeEventListener('error', handleError)
      script.dataset.omniPuterStatus = status
      resolve(createPuterScriptLoaderResult(status, reason))
    }

    function handleLoad() {
      if (hasPuterChat(browserWindow)) {
        finish('loaded', 'puter_available')
        return
      }
      finish('unavailable', 'puter_unavailable_after_load')
    }

    function handleError() {
      finish('failed', 'script_load_failed')
    }

    script.addEventListener('load', handleLoad)
    script.addEventListener('error', handleError)
  })
}

function getBrowserWindow(runtime: unknown): PuterWindow | null {
  if (!runtime || typeof runtime !== 'object') {
    return null
  }

  if ('document' in runtime && 'setTimeout' in runtime && 'clearTimeout' in runtime) {
    return runtime as PuterWindow
  }

  if ('window' in runtime) {
    const candidate = (runtime as { window?: unknown }).window
    if (candidate && typeof candidate === 'object' && 'document' in candidate) {
      return candidate as PuterWindow
    }
  }

  return null
}

function findPuterScript(document: Document): HTMLScriptElement | null {
  const idMatch = document.getElementById(PUTER_SCRIPT_ID)
  if (idMatch instanceof HTMLScriptElement) {
    return idMatch
  }

  return Array.from(document.scripts).find((script) => script.src === PUTER_SCRIPT_SRC) ?? null
}

function hasPuterChat(browserWindow: PuterWindow): boolean {
  return typeof browserWindow.puter?.ai?.chat === 'function'
}

function safeReason(value: string): string {
  const normalized = String(value || '').trim().toLowerCase()
  return /^[a-z0-9_]+$/.test(normalized) ? normalized : 'puter_loader_denied'
}
