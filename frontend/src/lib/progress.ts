import type { AgentId, ClaimInfo, CodeHit, PaperSectionHit, Step, StepKind, VerdictStatus } from './types'

/** Turn one raw "step" line from the backend into a typed step. */
export function parseStep(text: string, id: number): Step {
  let kind: StepKind = 'index'
  if (text.startsWith('Analyst')) kind = 'analyst'
  else if (text.startsWith('Detective')) kind = 'detective'
  else if (text.startsWith('Critic')) kind = 'critic'
  else if (text.startsWith('Saved')) kind = 'saved'
  else if (text.toLowerCase().startsWith('reporter')) kind = 'reporter'
  return { id, kind, text }
}

const STATUSES: VerdictStatus[] = ['NOT_FOUND', 'MISMATCH', 'MATCH']

function readStatus(text: string): VerdictStatus | undefined {
  return STATUSES.find((s) => text.startsWith(s))
}

export interface Attempt {
  searched: string[]
  query?: string
  hits?: CodeHit[]
  verdict?: VerdictStatus
  reason?: string
  paperValue?: string
  codeValue?: string
}

export interface ClaimRun {
  index: number
  claim?: string
  info?: ClaimInfo
  status?: VerdictStatus
  attempts: Attempt[]
  done: boolean
}

export type Phase = 'idle' | 'indexing' | 'checking' | 'reporting' | 'done'

export interface AgentCounts {
  claims: number | null
  searches: number
  verdicts: number
  retries: number
  issues: number
}

export interface Progress {
  phase: Phase
  total: number | null
  completed: number
  runs: ClaimRun[]
  /** Index into `runs` of the claim being checked right now, or -1. */
  currentIndex: number
  activeAgent: AgentId | null
  /** True right after the critic said NOT_FOUND and sent the detective back. */
  looping: boolean
  counts: AgentCounts
  /** Paper sections the Analyst retrieved (newer backends only). */
  analystSections: PaperSectionHit[] | null
}

/**
 * Rebuild the live picture of the run from the streamed steps (and the claim
 * list, once the Analyst has sent it). Each SSE step arrives when a node
 * FINISHES, so the "active" agent is the node that runs next.
 */
export function deriveProgress(steps: Step[], started: boolean, claims: ClaimInfo[] | null): Progress {
  const p: Progress = {
    phase: started ? 'indexing' : 'idle',
    total: null,
    completed: 0,
    runs: [],
    currentIndex: -1,
    activeAgent: started ? 'analyst' : null,
    looping: false,
    counts: { claims: null, searches: 0, verdicts: 0, retries: 0, issues: 0 },
    analystSections: null,
  }

  // With the claim list we can show the whole queue before anything is checked.
  if (claims) {
    p.runs = claims.map((info, i) => ({ index: i + 1, claim: info.text, info, attempts: [], done: false }))
  }

  /** The claim currently being checked: the first unfinished one. */
  const current = (): ClaimRun => {
    let run = p.runs.find((r) => !r.done)
    if (!run) {
      run = { index: p.runs.length + 1, attempts: [], done: false }
      p.runs.push(run)
    }
    return run
  }

  for (const step of steps) {
    switch (step.kind) {
      case 'analyst': {
        const n = Number(step.text.match(/(\d+)/)?.[1] ?? 0)
        p.total = n
        p.counts.claims = n
        p.analystSections = step.data?.sections ?? null
        p.phase = n > 0 ? 'checking' : 'reporting'
        p.activeAgent = n > 0 ? 'detective' : 'reporter'
        break
      }
      case 'detective': {
        const list = step.text.replace(/^Detective searched:\s*/, '')
        const run = current()
        if (run.attempts.length > 0) p.counts.retries += 1
        run.attempts.push({
          searched: list.split(',').map((s) => s.trim()).filter(Boolean),
          query: step.data?.query,
          hits: step.data?.hits,
        })
        p.counts.searches += 1
        p.activeAgent = 'critic'
        p.looping = false
        break
      }
      case 'critic': {
        const body = step.text.replace(/^Critic:\s*/, '')
        const verdict = readStatus(body)
        const run = current()
        const attempt = run.attempts[run.attempts.length - 1]
        if (attempt) {
          attempt.verdict = verdict
          attempt.reason = step.data?.reason ?? body.replace(/^[A-Z_]+\s*-\s*/, '')
          attempt.paperValue = step.data?.paper_value
          attempt.codeValue = step.data?.code_value
        }
        p.counts.verdicts += 1
        p.looping = verdict === 'NOT_FOUND'
        p.activeAgent = 'detective'
        break
      }
      case 'saved': {
        const body = step.text.replace(/^Saved:\s*/, '')
        const [statusPart, ...claimParts] = body.split('|')
        const run = current()
        run.status = readStatus(statusPart.trim())
        run.claim = run.claim ?? claimParts.join('|').trim()
        run.done = true
        if (run.status !== 'MATCH') p.counts.issues += 1
        p.completed += 1
        p.looping = false
        if (p.total !== null && p.completed >= p.total) {
          p.phase = 'reporting'
          p.activeAgent = 'reporter'
        } else {
          p.activeAgent = 'detective'
        }
        break
      }
      case 'reporter': {
        p.phase = 'done'
        p.activeAgent = null
        break
      }
      default:
        break
    }
  }

  if (p.phase === 'checking') {
    p.currentIndex = p.runs.findIndex((r) => !r.done)
  }
  return p
}
