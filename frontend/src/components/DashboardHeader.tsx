import type { RunMeta, RunStatus, VerifyInput } from '../lib/types'

interface Props {
  status: RunStatus
  seconds: number
  meta: RunMeta | null
  input: VerifyInput | null
  onAbort: () => void
  onRerun: () => void
  onNew: () => void
}

const STATUS_TEXT: Record<RunStatus, string> = {
  idle: 'ready',
  running: 'scanning',
  done: 'complete',
  error: 'failed',
  aborted: 'aborted',
}

/** Compact top bar used once a run starts: logo top-left, what's being checked, controls on the right. */
export function DashboardHeader({ status, seconds, meta, input, onAbort, onRerun, onNew }: Props) {
  const paperTitle = meta?.paper.title ?? input?.paper ?? ''
  const repoLabel = meta?.repo.label ?? input?.repo ?? ''

  return (
    <header className="topbar">
      <button className="brand" onClick={onNew} title="New verification">
        <span className="brand-mark" aria-hidden="true" />
        <span className="brand-text">SCHOLARGRAPH</span>
      </button>

      <div className="topbar-subject">
        <div className="subject">
          <span className="subject-label">paper</span>
          {meta?.paper.url ? (
            <a className="subject-value" href={meta.paper.url} target="_blank" rel="noreferrer">
              {paperTitle}
            </a>
          ) : (
            <span className="subject-value">{paperTitle}</span>
          )}
          {meta && <span className="subject-note">{meta.paper.chunks} chunks</span>}
        </div>
        <div className="subject">
          <span className="subject-label">code</span>
          {meta?.repo.url ? (
            <a className="subject-value" href={meta.repo.url} target="_blank" rel="noreferrer">
              {repoLabel}
            </a>
          ) : (
            <span className="subject-value">{repoLabel}</span>
          )}
          {meta && (
            <span className="subject-note">
              {meta.repo.python_files} .py · {meta.repo.chunks} chunks
            </span>
          )}
        </div>
      </div>

      <div className="topbar-controls">
        <span className={`run-state run-state--${status}`}>
          <span className="run-state-dot" aria-hidden="true" />
          {STATUS_TEXT[status]} · {seconds}s
        </span>
        {status === 'running' ? (
          <button className="ghost ghost--danger" onClick={onAbort}>
            Abort
          </button>
        ) : (
          <>
            <button className="ghost" onClick={onRerun}>
              Run again
            </button>
            <button className="ghost ghost--accent" onClick={onNew}>
              New
            </button>
          </>
        )}
      </div>
    </header>
  )
}
