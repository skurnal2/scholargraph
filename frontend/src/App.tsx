import { useCallback, useMemo, useState } from 'react'
import { AgentInspector } from './components/AgentInspector'
import { Background } from './components/Background'
import { DashboardHeader } from './components/DashboardHeader'
import { InputForm } from './components/InputForm'
import { Pipeline } from './components/Pipeline'
import { Scorecard, ScorecardPlaceholder } from './components/Scorecard'
import { Timeline } from './components/Timeline'
import { useElapsed } from './lib/hooks'
import { deriveProgress } from './lib/progress'
import { withViewTransition } from './lib/transition'
import type { AgentId, VerifyInput } from './lib/types'
import { useBackendCheck } from './lib/useBackendCheck'
import { useVerify } from './lib/useVerify'

const DEFAULT_INPUT: VerifyInput = { paper: 'sample', repo: 'sample' }

export default function App() {
  const run = useVerify()
  const backend = useBackendCheck()
  const [view, setView] = useState<'home' | 'dashboard'>('home')
  const [inspect, setInspect] = useState<AgentId | null>(null)
  const closeInspector = useCallback(() => setInspect(null), [])
  const progress = useMemo(
    () => deriveProgress(run.steps, run.status !== 'idle', run.claims),
    [run.steps, run.status, run.claims],
  )
  const seconds = useElapsed(run.startedAt, run.finishedAt)
  const live = run.status === 'running'

  const startRun = (input: VerifyInput) => {
    withViewTransition(() => {
      run.start(input)
      setView('dashboard')
    })
  }

  const goHome = () => {
    withViewTransition(() => {
      run.reset()
      setInspect(null)
      setView('home')
    })
  }

  if (view === 'home') {
    return (
      <>
        <Background />
        <main className="app app--home">
          <header className="hero">
            <p className="eyebrow">paper ⇄ code verification</p>
            <h1 className="title brand-transition" data-text="SCHOLARGRAPH">
              SCHOLARGRAPH
            </h1>
            <p className="tagline">
              <span className="tagline-text">&gt; does the code really do what the paper says?</span>
              <span className="caret" aria-hidden="true" />
            </p>
            <InputForm initial={run.input ?? DEFAULT_INPUT} onSubmit={startRun} />
            {backend === 'old' && (
              <div className="alert alert--warn" role="alert">
                <strong>Old backend detected.</strong> Port 8000 is running <code>lessons/api.py</code>, which ignores the
                paper and repo you enter and always checks the sample. Restart it with{' '}
                <code>uv run uvicorn backend.api:app --reload</code>
              </div>
            )}
            {backend === 'down' && (
              <div className="alert alert--warn" role="alert">
                <strong>Backend not reachable.</strong> Start it from the project root with{' '}
                <code>uv run uvicorn backend.api:app --reload</code>
              </div>
            )}
          </header>

          <div className="pipeline-transition">
            <Pipeline active={null} status="idle" looping={false} />
          </div>

          <section className="intro">
            <div className="intro-card" style={{ animationDelay: '0ms' }}>
              <span className="intro-step">01</span>
              <h3>Read the paper</h3>
              <p>Downloads the arXiv PDF, hybrid-searches the implementation sections, and Claude extracts every checkable claim.</p>
            </div>
            <div className="intro-card" style={{ animationDelay: '120ms' }}>
              <span className="intro-step">02</span>
              <h3>Hunt the code</h3>
              <p>Clones the repo, parses functions, classes and configs, and vector-searches the evidence while skipping tests.</p>
            </div>
            <div className="intro-card" style={{ animationDelay: '240ms' }}>
              <span className="intro-step">03</span>
              <h3>Judge &amp; retry</h3>
              <p>The critic compares claim and code, and loops back with a wider search when the evidence is weak.</p>
            </div>
          </section>

          <footer className="footer">LangGraph · LangChain · Claude Haiku 5.5 · Weaviate · Qdrant · FastAPI SSE</footer>
        </main>
      </>
    )
  }

  const placeholderMessage =
    run.status === 'error'
      ? 'The run stopped before a scorecard could be built.'
      : run.status === 'aborted'
        ? 'Run aborted. Partial results are in the live feed.'
        : progress.phase === 'indexing'
          ? 'Waiting for the paper and code to be indexed.'
          : 'The scorecard appears when the Reporter finishes.'

  return (
    <>
      <Background />
      <main className="app app--dashboard">
        <DashboardHeader
          status={run.status}
          seconds={seconds}
          meta={run.meta}
          input={run.input}
          onAbort={run.abort}
          onRerun={() => run.input && run.start(run.input)}
          onNew={goHome}
        />

        {run.error && (
          <div className="alert" role="alert">
            <strong>Run failed.</strong> {run.error}
          </div>
        )}

        <div className="pipeline-transition">
          <Pipeline
            active={progress.activeAgent}
            status={run.status}
            looping={progress.looping}
            counts={progress.counts}
            compact
            onSelect={setInspect}
            selected={inspect}
          />
        </div>

        <div className="board">
          <Timeline progress={progress} statuses={run.statuses} live={live} onInspectAnalyst={() => setInspect('analyst')} />
          {run.results ? (
            <Scorecard results={run.results} seconds={seconds} />
          ) : (
            <ScorecardPlaceholder message={placeholderMessage} live={live} />
          )}
        </div>
      </main>

      {inspect && (
        <AgentInspector
          agent={inspect}
          progress={progress}
          claims={run.claims}
          results={run.results}
          status={run.status}
          onSelect={setInspect}
          onClose={closeInspector}
        />
      )}
    </>
  )
}
