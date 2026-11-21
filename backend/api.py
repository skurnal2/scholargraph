"""FastAPI app: /verify streams a whole verification run as Server-Sent Events.

Events (one JSON object per `data:` line):
  {"type": "status", "text": ...}            ingestion progress (download, clone, indexing)
  {"type": "meta", "paper": {...}, "repo": {...}}
  {"type": "step", "node": ..., "text": ..., "data": {...}}   one per LangGraph node
  {"type": "claims", "claims": [...]}        the Analyst's full claim list, right after it finishes
  {"type": "report", "results": [...]}       the final scorecard
  {"type": "error", "message": ...}          the run stopped
"""

import json
import logging
import shutil
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.code_index import build_code_index, chunk_repo, drop_code_collections, drop_code_index
from backend.graph import graph, start_state
from backend.paper_index import build_paper_index, drop_paper_collections, drop_paper_index, load_paper_chunks
from backend.settings import CODE_COLLECTION_PREFIX, FRONTEND_ORIGINS, PAPER_COLLECTION_PREFIX
from backend.sources import InputError, resolve_paper, resolve_repo

log = logging.getLogger("scholargraph")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Remove collections left behind by runs that were interrupted (server restart, crash).
    try:
        drop_code_collections(CODE_COLLECTION_PREFIX)
        drop_paper_collections(PAPER_COLLECTION_PREFIX)
    except Exception:  # databases may not be up yet; runs will report the problem
        log.warning("Could not clean up old collections at startup", exc_info=True)
    yield


app = FastAPI(title="ScholarGraph", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def describe(node: str, update: dict) -> str:
    if node == "analyst":
        return f"Analyst found {len(update['claims'])} claims"
    if node == "detective":
        return f"Detective searched: {update['found_where']}"
    if node == "critic":
        v = update["verdict"]
        return f"Critic: {v.status} - {v.reason}"
    if node == "save_result":
        r = update["results"][0]
        return f"Saved: {r['verdict'].status} | {r['claim'].text}"
    return f"{node} finished"


def details(node: str, update: dict) -> dict:
    """Structured data for each node, so the UI can show exactly what every agent did."""
    if node == "analyst":
        return {"sections": update["paper_sections"], "claim_count": len(update["claims"])}
    if node == "detective":
        return {"query": update["found_query"], "attempt": update["attempt"], "hits": update["found_hits"]}
    if node == "critic":
        v = update["verdict"]
        return {"status": v.status, "reason": v.reason, "paper_value": v.paper_value, "code_value": v.code_value}
    if node == "save_result":
        r = update["results"][0]
        return {"status": r["verdict"].status, "claim": r["claim"].text, "where": r["where"]}
    return {}


def run_verification(paper: str, repo: str):
    run_id = uuid.uuid4().hex[:10]
    paper_collection = f"{PAPER_COLLECTION_PREFIX}{run_id}"
    code_collection = f"{CODE_COLLECTION_PREFIX}{run_id}"
    workdir = Path(tempfile.mkdtemp(prefix="scholargraph-"))

    try:
        yield sse({"type": "status", "text": "Fetching the paper"})
        paper_src = resolve_paper(paper, workdir)

        yield sse({"type": "status", "text": "Cloning the repository" if repo.strip() not in ("", "sample") else "Loading the repository"})
        repo_src = resolve_repo(repo, workdir)

        yield sse({"type": "status", "text": "Splitting the paper into sections"})
        paper_chunks = load_paper_chunks(paper_src)
        if not paper_chunks:
            raise InputError("Couldn't extract any text from the paper (it may be a scanned PDF).")

        yield sse({"type": "status", "text": "Parsing the code into functions, classes and configs"})
        code_chunks, code_stats = chunk_repo(repo_src.path)
        if not code_chunks:
            raise InputError("No Python code or config files found in the repository.")

        yield sse({
            "type": "meta",
            "paper": {"label": paper_src.label, "title": paper_src.title, "url": paper_src.url, "chunks": len(paper_chunks)},
            "repo": {"label": repo_src.label, "url": repo_src.url, **code_stats},
        })

        yield sse({"type": "status", "text": f"Indexing {len(paper_chunks)} paper chunks into Weaviate"})
        build_paper_index(paper_chunks, paper_collection)

        yield sse({"type": "status", "text": f"Embedding {len(code_chunks)} code chunks into Qdrant"})
        build_code_index(code_chunks, code_collection)

        yield sse({"type": "status", "text": "Paper Analyst is extracting claims"})
        results = []
        stream = graph.stream(
            start_state(paper_collection, code_collection),
            config={"recursion_limit": 500},
            stream_mode="updates",
        )
        for chunk in stream:
            for node, update in chunk.items():
                update = update or {}
                if node == "save_result":
                    results += update["results"]
                yield sse({"type": "step", "node": node, "text": describe(node, update), "data": details(node, update)})
                if node == "analyst":
                    # Send the full claim list up front so the UI can show the whole queue.
                    yield sse({
                        "type": "claims",
                        "claims": [
                            {"text": c.text, "category": c.category, "section": c.section, "quote": c.quote}
                            for c in update["claims"]
                        ],
                    })

        yield sse({
            "type": "report",
            "results": [
                {
                    "status": r["verdict"].status,
                    "claim": r["claim"].text,
                    "paper": r["verdict"].paper_value,
                    "code": r["verdict"].code_value,
                    "where": r["where"],
                    "quote": r["claim"].quote,
                    "section": r["claim"].section,
                }
                for r in results
            ],
        })
    except InputError as exc:
        yield sse({"type": "error", "message": str(exc)})
    except Exception as exc:
        log.exception("Verification run %s failed", run_id)
        yield sse({"type": "error", "message": f"Something went wrong: {type(exc).__name__}: {exc}"})
    finally:
        # Each run owns its collections and temp folder, so concurrent runs never mix data.
        for cleanup in (lambda: drop_paper_index(paper_collection), lambda: drop_code_index(code_collection)):
            try:
                cleanup()
            except Exception:
                log.warning("Cleanup failed for run %s", run_id, exc_info=True)
        shutil.rmtree(workdir, ignore_errors=True)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/verify")
def verify(
    paper: str = Query("sample", description="arXiv ID or URL, or 'sample'"),
    repo: str = Query("sample", description="https://github.com/owner/repo, or 'sample'"),
):
    return StreamingResponse(
        run_verification(paper, repo),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
