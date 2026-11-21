import { useState, type FormEvent } from 'react'
import type { VerifyInput } from '../lib/types'

const PRESETS: { label: string; note: string; value: VerifyInput }[] = [
  {
    label: 'TinyFormer sample',
    note: '2 planted bugs · fast',
    value: { paper: 'sample', repo: 'sample' },
  },
  {
    label: 'Attention Is All You Need',
    note: 'arXiv 1706.03762',
    value: { paper: '1706.03762', repo: 'https://github.com/jadore801120/attention-is-all-you-need-pytorch' },
  },
]

const ARXIV_HINT = /(\d{4}\.\d{4,5})|([a-z-]+\/\d{7})|^sample$/i
const GITHUB_HINT = /^(https?:\/\/)?(www\.)?github\.com\/[\w.-]+\/[\w.-]+\/?$|^sample$/i

interface Props {
  initial: VerifyInput
  onSubmit: (input: VerifyInput) => void
}

/** Paper + repo inputs with one-click presets. The backend does the real validation. */
export function InputForm({ initial, onSubmit }: Props) {
  const [paper, setPaper] = useState(initial.paper)
  const [repo, setRepo] = useState(initial.repo)
  const [touched, setTouched] = useState(false)

  const paperOk = ARXIV_HINT.test(paper.trim())
  const repoOk = GITHUB_HINT.test(repo.trim())
  const valid = paperOk && repoOk

  const submit = (e: FormEvent) => {
    e.preventDefault()
    setTouched(true)
    if (valid) onSubmit({ paper: paper.trim(), repo: repo.trim() })
  }

  return (
    <form className="form" onSubmit={submit} noValidate>
      <div className="form-fields">
        <label className={`field ${touched && !paperOk ? 'is-invalid' : ''}`}>
          <span className="field-label">Paper</span>
          <input
            className="field-input"
            value={paper}
            onChange={(e) => setPaper(e.target.value)}
            placeholder="arXiv ID or URL, e.g. 1706.03762"
            spellCheck={false}
            autoComplete="off"
          />
          <span className="field-hint">arXiv ID / URL, or “sample”</span>
        </label>
        <label className={`field ${touched && !repoOk ? 'is-invalid' : ''}`}>
          <span className="field-label">Code</span>
          <input
            className="field-input"
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
            placeholder="https://github.com/owner/repo"
            spellCheck={false}
            autoComplete="off"
          />
          <span className="field-hint">public GitHub repo URL, or “sample”</span>
        </label>
      </div>

      <div className="presets">
        <span className="presets-label">Try</span>
        {PRESETS.map((p) => (
          <button
            type="button"
            key={p.label}
            className={`preset ${paper === p.value.paper && repo === p.value.repo ? 'is-on' : ''}`}
            onClick={() => {
              setPaper(p.value.paper)
              setRepo(p.value.repo)
            }}
          >
            <span className="preset-name">{p.label}</span>
            <span className="preset-note">{p.note}</span>
          </button>
        ))}
      </div>

      <div className="actions">
        <button className="cta" type="submit">
          <span className="cta-glow" aria-hidden="true" />
          <span className="cta-label">Verify</span>
        </button>
      </div>
      {touched && !valid && (
        <p className="form-error" role="alert">
          {!paperOk ? 'Enter an arXiv ID (like 1706.03762) or an arXiv URL. ' : ''}
          {!repoOk ? 'Enter a GitHub URL like https://github.com/owner/repo.' : ''}
        </p>
      )}
    </form>
  )
}
