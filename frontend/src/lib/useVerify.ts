import { useCallback, useEffect, useRef, useState } from 'react'
import { parseStep } from './progress'
import type { ClaimInfo, ResultRow, RunMeta, RunStatus, ServerEvent, Step, VerifyInput } from './types'

const API_BASE = import.meta.env.VITE_API_URL ?? '/api'

/**
 * Opens the /verify Server-Sent Events stream and collects what it sends.
 *
 * Important: EventSource reconnects automatically when the server closes the
 * stream. That would start a whole new (paid) verification run, so we close
 * it ourselves on the final report, on an error event, and on any network error.
 */
export function useVerify() {
  const [steps, setSteps] = useState<Step[]>([])
  const [statuses, setStatuses] = useState<string[]>([])
  const [meta, setMeta] = useState<RunMeta | null>(null)
  const [claims, setClaims] = useState<ClaimInfo[] | null>(null)
  const [results, setResults] = useState<ResultRow[] | null>(null)
  const [status, setStatus] = useState<RunStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const [input, setInput] = useState<VerifyInput | null>(null)
  const [startedAt, setStartedAt] = useState<number | null>(null)
  const [finishedAt, setFinishedAt] = useState<number | null>(null)
  const sourceRef = useRef<EventSource | null>(null)
  const finishedRef = useRef(false)

  const close = useCallback(() => {
    sourceRef.current?.close()
    sourceRef.current = null
  }, [])

  const finish = useCallback(
    (next: RunStatus, message: string | null = null) => {
      finishedRef.current = true
      close()
      setStatus(next)
      setError(message)
      setFinishedAt(Date.now())
    },
    [close],
  )

  const reset = useCallback(() => {
    close()
    finishedRef.current = true
    setSteps([])
    setStatuses([])
    setMeta(null)
    setClaims(null)
    setResults(null)
    setError(null)
    setStatus('idle')
    setStartedAt(null)
    setFinishedAt(null)
  }, [close])

  const start = useCallback(
    (next: VerifyInput) => {
      close()
      finishedRef.current = false
      setInput(next)
      setSteps([])
      setStatuses([])
      setMeta(null)
      setClaims(null)
      setResults(null)
      setError(null)
      setStatus('running')
      setStartedAt(Date.now())
      setFinishedAt(null)

      const params = new URLSearchParams({ paper: next.paper.trim(), repo: next.repo.trim() })
      const source = new EventSource(`${API_BASE}/verify?${params}`)
      sourceRef.current = source

      source.onmessage = (event) => {
        let message: ServerEvent
        try {
          message = JSON.parse(event.data) as ServerEvent
        } catch {
          return
        }
        switch (message.type) {
          case 'status':
            setStatuses((prev) => [...prev, message.text])
            break
          case 'meta':
            setMeta({ paper: message.paper, repo: message.repo })
            break
          case 'step':
            setSteps((prev) => [...prev, { ...parseStep(message.text, prev.length), data: message.data }])
            break
          case 'claims':
            setClaims(message.claims)
            break
          case 'report':
            setResults(message.results)
            finish('done')
            break
          case 'error':
            finish('error', message.message)
            break
        }
      }

      source.onerror = () => {
        if (finishedRef.current) return
        finish('error', 'Lost the connection to the backend. Is the FastAPI server running on port 8000?')
      }
    },
    [close, finish],
  )

  const abort = useCallback(() => finish('aborted'), [finish])

  useEffect(() => close, [close])

  return { steps, statuses, meta, claims, results, status, error, input, startedAt, finishedAt, start, abort, reset }
}
