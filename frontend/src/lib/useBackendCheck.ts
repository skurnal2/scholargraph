import { useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL ?? '/api'

export type BackendState = 'checking' | 'ok' | 'old' | 'down'

/**
 * Detects which server is answering on the API port. The real backend
 * (backend.api) has /health; the old lessons/api.py server doesn't, and it
 * ignores the paper/repo inputs, which is easy to miss.
 */
export function useBackendCheck(): BackendState {
  const [state, setState] = useState<BackendState>('checking')

  useEffect(() => {
    let cancelled = false
    fetch(`${API_BASE}/health`)
      .then((res) => {
        if (cancelled) return
        if (res.ok) setState('ok')
        else if (res.status === 404) setState('old')
        else setState('down')
      })
      .catch(() => !cancelled && setState('down'))
    return () => {
      cancelled = true
    }
  }, [])

  return state
}
