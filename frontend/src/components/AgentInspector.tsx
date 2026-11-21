import { useEffect } from 'react'
import type { Progress } from '../lib/progress'
import type { AgentId, ClaimInfo, ResultRow, RunStatus } from '../lib/types'
import { AgentIcon } from './Icons'
import { StatusBadge } from './Timeline'

const TITLES: Record<AgentId, { name: string; role: string }> = {
  analyst: { name: 'Paper Analyst', role: 'Hybrid-searches the paper (Weaviate) and asks Claude to extract checkable claims.' },
  detective: { name: 'Code Detective', role: 'Vector-searches the code (Qdrant), skipping test files, for each claim.' },
  critic: { name: 'Critic', role: 'Claude compares each claim with the retrieved code and returns a typed verdict.' },
  reporter: { name: 'Reporter', role: 'Collects every verdict into the final scorecard.' },
}

const ORDER: AgentId[] = ['analyst', 'detective', 'critic', 'reporter']

function ScoreBar({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(1, score)) * 100
  return (
    <span className="scorebar" title={`score ${score.toFixed(3)}`}>
      <span className="scorebar-fill" style={{ width: `${pct}%` }} />
      <span className="scorebar-num">{score.toFixed(2)}</span>
    </span>
  )
}

function AnalystView({ progress, claims }: { progress: Progress; claims: ClaimInfo[] | null }) {
  const sections = progress.analystSections
  return (
    <>
      <h4 className="insp-h">Sections retrieved{sections ? ` (${sections.length})` : ''}</h4>
      {!sections && <p className="insp-empty">{progress.total === null ? 'Still reading the paper…' : 'Section details need the new backend (backend.api).'}</p>}
      <ul className="insp-list">
        {sections?.map((s, i) => (
          <li className="insp-item" key={i}>
            <div className="insp-row">
              <span className="insp-strong">{s.section}</span>
              <ScoreBar score={s.score} />
            </div>
            <p className="insp-preview">{s.preview}…</p>
            <div className="insp-tags">
              {s.topics.map((t) => (
                <span className="insp-tag" key={t}>{t}</span>
              ))}
            </div>
          </li>
        ))}
      </ul>

      <h4 className="insp-h">Claims extracted{claims ? ` (${claims.length})` : progress.total !== null ? ` (${progress.total})` : ''}</h4>
      {!claims && <p className="insp-empty">{progress.total === null ? 'Waiting for Claude…' : 'The claim list needs the new backend (backend.api).'}</p>}
      <ol className="insp-list insp-list--numbered">
        {claims?.map((c, i) => (
          <li className="insp-item" key={i}>
            <div className="insp-row">
              <span className="insp-strong">{c.text}</span>
              <span className="insp-tag insp-tag--violet">{c.category}</span>
            </div>
            <p className="insp-quote">“{c.quote}” <cite>§ {c.section}</cite></p>
          </li>
        ))}
      </ol>
    </>
  )
}

function DetectiveView({ progress }: { progress: Progress }) {
  const runs = progress.runs.filter((r) => r.attempts.length > 0)
  return (
    <>
      <h4 className="insp-h">Searches ({progress.counts.searches})</h4>
      {runs.length === 0 && <p className="insp-empty">No searches yet.</p>}
      <ol className="insp-list">
        {runs.map((run) => (
          <li className="insp-item" key={run.index}>
            <div className="insp-row">
              <span className="insp-index">{String(run.index).padStart(2, '0')}</span>
              <span className="insp-strong">{run.claim}</span>
            </div>
            {run.attempts.map((a, i) => (
              <div className="insp-attempt" key={i}>
                <span className="insp-tag insp-tag--cyan">search {i + 1} · top {a.hits?.length ?? a.searched.length}</span>
                {a.hits ? (
                  <ul className="insp-hits">
                    {a.hits.map((h, j) => (
                      <li key={j}>
                        <code className="chip">{h.file_path}:{h.start_line}-{h.end_line}</code>
                        <span className="insp-hit-name">{h.type} {h.name}</span>
                        <ScoreBar score={h.score} />
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="chips">
                    {a.searched.map((f) => (
                      <code className="chip" key={f}>{f}</code>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </li>
        ))}
      </ol>
    </>
  )
}

function CriticView({ progress }: { progress: Progress }) {
  const judged = progress.runs.filter((r) => r.attempts.some((a) => a.verdict))
  return (
    <>
      <h4 className="insp-h">
        Verdicts ({progress.counts.verdicts}){progress.counts.retries ? ` · ${progress.counts.retries} sent back for a wider search` : ''}
      </h4>
      {judged.length === 0 && <p className="insp-empty">No verdicts yet.</p>}
      <ol className="insp-list">
        {judged.map((run) => (
          <li className="insp-item" key={run.index}>
            <div className="insp-row">
              <span className="insp-index">{String(run.index).padStart(2, '0')}</span>
              <span className="insp-strong">{run.claim}</span>
            </div>
            {run.attempts
              .filter((a) => a.verdict)
              .map((a, i) => (
                <div className="insp-attempt" key={i}>
                  <div className="insp-row">
                    <StatusBadge status={a.verdict} />
                    {a.verdict === 'NOT_FOUND' && i < run.attempts.length - 1 && <span className="insp-tag insp-tag--magenta">→ retry</span>}
                  </div>
                  <p className="insp-reason">{a.reason}</p>
                  {(a.paperValue || a.codeValue) && (
                    <div className="insp-compare">
                      <span>paper: {a.paperValue}</span>
                      <span>code: {a.codeValue}</span>
                    </div>
                  )}
                </div>
              ))}
          </li>
        ))}
      </ol>
    </>
  )
}

function ReporterView({ results, status }: { results: ResultRow[] | null; status: RunStatus }) {
  if (!results) return <p className="insp-empty">{status === 'running' ? 'The Reporter runs after every claim is checked.' : 'No report for this run.'}</p>
  const issues = results.filter((r) => r.status !== 'MATCH')
  return (
    <>
      <h4 className="insp-h">Summary</h4>
      <p className="insp-reason">
        {results.length} claims checked · {results.length - issues.length} match · {issues.length} need attention.
      </p>
      <h4 className="insp-h">Issues</h4>
      {issues.length === 0 && <p className="insp-empty">None. Every claim matched the code.</p>}
      <ol className="insp-list">
        {issues.map((r, i) => (
          <li className="insp-item" key={i}>
            <div className="insp-row">
              <StatusBadge status={r.status} />
              <span className="insp-strong">{r.claim}</span>
            </div>
            <div className="insp-compare">
              <span>paper: {r.paper}</span>
              <span>code: {r.code}</span>
            </div>
          </li>
        ))}
      </ol>
    </>
  )
}

interface Props {
  agent: AgentId
  progress: Progress
  claims: ClaimInfo[] | null
  results: ResultRow[] | null
  status: RunStatus
  onSelect: (agent: AgentId) => void
  onClose: () => void
}

/** Slide-in drawer showing everything one agent has done in this run. */
export function AgentInspector({ agent, progress, claims, results, status, onSelect, onClose }: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const live = status === 'running' && progress.activeAgent === agent

  return (
    <div className="inspector-layer" role="dialog" aria-modal="true" aria-label={`${TITLES[agent].name} details`}>
      <button className="inspector-backdrop" aria-label="Close" onClick={onClose} />
      <aside className="inspector">
        <header className="inspector-head">
          <span className={`inspector-icon ${live ? 'is-live' : ''}`}>
            <AgentIcon agent={agent} />
          </span>
          <div className="inspector-titles">
            <h3>{TITLES[agent].name}</h3>
            <p>{TITLES[agent].role}</p>
          </div>
          <button className="inspector-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        <nav className="inspector-tabs" aria-label="Agents">
          {ORDER.map((id) => (
            <button key={id} className={`inspector-tab ${id === agent ? 'is-on' : ''}`} onClick={() => onSelect(id)}>
              {TITLES[id].name}
            </button>
          ))}
        </nav>

        <div className="inspector-body" key={agent}>
          {agent === 'analyst' && <AnalystView progress={progress} claims={claims} />}
          {agent === 'detective' && <DetectiveView progress={progress} />}
          {agent === 'critic' && <CriticView progress={progress} />}
          {agent === 'reporter' && <ReporterView results={results} status={status} />}
        </div>
      </aside>
    </div>
  )
}
