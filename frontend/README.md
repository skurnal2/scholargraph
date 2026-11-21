# ScholarGraph frontend

React + TypeScript (Vite) dashboard for the ScholarGraph backend. It opens the
`/verify` Server-Sent Events stream and shows each LangGraph agent step live,
then renders the final scorecard.

## Run

Qdrant and Weaviate must be running (`docker compose up -d`), and the FastAPI
backend must be running on port 8000 (from the project root):

```bash
uv run uvicorn backend.api:app --reload
```

Then, in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, enter an arXiv ID/URL and a public GitHub repo URL
(or pick a preset), and click **Verify**.

In dev, the browser calls `/api/...` and Vite forwards it to `http://localhost:8000`
(see `vite.config.ts`), so no CORS setup is needed. Point it elsewhere with
`API_URL=http://host:port npm run dev`, or set `VITE_API_URL` at build time.

## Structure

| File | Purpose |
|---|---|
| `src/App.tsx` | Home view (big logo + form) and dashboard view; switches between them with a View Transition |
| `src/components/InputForm.tsx` | Paper and repo inputs, presets, light validation |
| `src/components/DashboardHeader.tsx` | Compact top bar: logo, what's being checked, run status and controls |
| `src/lib/useVerify.ts` | Opens the SSE stream, collects status/meta/steps/report/error events, closes the stream so the browser doesn't auto-reconnect and start a second run |
| `src/lib/progress.ts` | Turns the raw step lines into claims, attempts and the active agent |
| `src/components/Pipeline.tsx` | The four agents with the active one glowing and the retry loop |
| `src/components/Timeline.tsx` | Live feed of claims, searches and critic verdicts |
| `src/components/Scorecard.tsx` | Agreement ring, counters and claim-by-claim breakdown with citations |
| `src/index.css` | Neon theme and all animations (respects `prefers-reduced-motion`) |
