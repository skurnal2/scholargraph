import { useEffect, useRef } from 'react'
import type { ClaimRun, Progress } from '../lib/progress'
import type { VerdictStatus } from '../lib/types'
import { AnalystCard } from './AnalystCard'
import { Loader } from './Loader'

export function StatusBadge({ status }: { status?: VerdictStatus }) {
  if (!status) return <span className="badge badge--pending">checking</span>
  const label = status === 'NOT_FOUND' ? 'not found' : status.toLowerCase()
  return <span className={`badge badge--${status.toLowerCase()}`}>{label}</span>
}

type CardState = 'done' | 'current' | 'queued' | 'stopped'

function Dots() {
  return (
    <span className="loader-dots" aria-hidden="true">
      <span>.</span>
      <span>.</span>
      <span>.</span>
    </span>
  )
}

function RunCard({ run, total, state }: { run: ClaimRun; total: number | null; state: CardState }) {
  const badge =
    state === 'done' ? (
      <StatusBadge status={run.status} />
    ) : state === 'current' ? (
      <StatusBadge />
    ) : (
      <span className={`badge badge--${state}`}>{state}</span>
    )

  return (
    <li className={`run is-${state} run--${run.status?.toLowerCase() ?? 'pending'}`} data-run={run.index}>
      <div className="run-head">
        <span className="run-index">
          {String(run.index).padStart(2, '0')}
          {total ? <span className="run-total">/{total}</span> : null}
        </span>
        <div className="run-title">
          <span className="run-claim">{run.claim ?? 'Locating evidence for the next claim'}</span>
          {run.info && (
            <span className="run-meta">
              <span className="run-category">{run.info.category}</span>
              <span className="run-section">§ {run.info.section}</span>
            </span>
          )}
        </div>
        {badge}
      </div>

      {run.attempts.length > 0 && (
        <ol className="attempts">
          {run.attempts.map((attempt, i) => (
            <li className="attempt" key={i}>
              <div className="attempt-line">
                <span className="attempt-tag attempt-tag--detective">search {i + 1}</span>
                <span className="chips">
                  {attempt.searched.map((file) => (
                    <code className="chip" key={file}>{file}</code>
                  ))}
                </span>
              </div>
              {attempt.verdict ? (
                <div className="attempt-line">
                  <span className={`attempt-tag attempt-tag--${attempt.verdict.toLowerCase()}`}>critic</span>
                  <span className="attempt-reason">{attempt.reason}</span>
                </div>
              ) : (
                state === 'current' && (
                  <div className="attempt-line">
                    <span className="attempt-tag attempt-tag--thinking">critic</span>
                    <span className="thinking">
                      judging the evidence
                      <Dots />
                    </span>
                  </div>
                )
              )}
            </li>
          ))}
        </ol>
      )}

      {state === 'current' && run.attempts.length === 0 && (
        <div className="attempt-line attempt-line--solo">
          <span className="attempt-tag attempt-tag--detective">detective</span>
          <span className="thinking thinking--cyan">
            searching the code
            <Dots />
          </span>
        </div>
      )}
      {state === 'current' && <span className="run-scan" aria-hidden="true" />}
    </li>
  )
}

interface Props {
  progress: Progress
  statuses: string[]
  live: boolean
  onInspectAnalyst?: () => void
}

/** Live feed: the whole claim queue, with the claim being checked highlighted. */
export function Timeline({ progress, statuses, live, onInspectAnalyst }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const { total, completed, runs, phase, currentIndex } = progress
  const current = currentIndex >= 0 ? runs[currentIndex] : undefined
  const scrollKey = `${currentIndex}:${current?.attempts.length ?? 0}:${phase}`

  // Keep the claim being checked in view (or the end of the list when finishing).
  useEffect(() => {
    const box = scrollRef.current
    if (!box) return
    const target = current ? box.querySelector<HTMLElement>(`[data-run="${current.index}"]`) : null
    const top = target ? target.offsetTop - box.clientHeight / 3 : box.scrollHeight
    box.scrollTo({ top: Math.max(0, top), behavior: 'smooth' })
  }, [scrollKey, current])

  const percent = total ? Math.round((completed / total) * 100) : 0
  // Older backends don't send the claim list: show a placeholder between claims.
  const waitingForNext = live && phase === 'checking' && currentIndex === -1

  const stateOf = (run: ClaimRun, i: number): CardState => {
    if (run.done) return 'done'
    if (!live) return 'stopped'
    return i === currentIndex ? 'current' : 'queued'
  }

  return (
    <section className="panel timeline" aria-label="Live agent activity">
      <header className="panel-head">
        <h2 className="panel-title">Live feed</h2>
        {total !== null && (
          <span className="panel-meta">
            {completed}/{total} claims · {percent}%
          </span>
        )}
      </header>

      {total !== null && (
        <div className="progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}>
          <div className={`progress-fill ${live ? 'is-live' : ''}`} style={{ width: `${percent}%` }} />
        </div>
      )}

      <div className="panel-scroll" ref={scrollRef}>
        {phase === 'indexing' ? (
          <Loader statuses={statuses} active={live} />
        ) : (
          <ol className="runs">
            {total !== null && (
              <AnalystCard sections={progress.analystSections} claimCount={total} onInspect={onInspectAnalyst} />
            )}
            {total === 0 && <li className="empty">The Analyst found no checkable implementation claims in this paper.</li>}
            {runs.map((run, i) => (
              <RunCard key={run.index} run={run} total={total} state={stateOf(run, i)} />
            ))}
            {waitingForNext && (
              <RunCard key="next" run={{ index: runs.length + 1, attempts: [], done: false }} total={total} state="current" />
            )}
            {phase === 'reporting' && live && (
              <li className="run is-current run--pending">
                <div className="run-head">
                  <span className="run-claim">Reporter is assembling the scorecard</span>
                  <span className="badge badge--pending">writing</span>
                </div>
                <span className="run-scan" aria-hidden="true" />
              </li>
            )}
          </ol>
        )}
      </div>
    </section>
  )
}
