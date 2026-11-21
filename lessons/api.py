import json                                          # NEW
import time                                          # NEW

from fastapi import FastAPI
from fastapi.responses import StreamingResponse      # NEW
from code_index import build_index
from lesson8_hybrid_graph import graph, start_state
from paper_index import build_paper_index

app = FastAPI()


@app.get("/")
def home():
    return {"message": "ScholarGraph API is running"}


@app.get("/hello/{name}")
def hello(name: str):
    return {"message": f"Hello, {name}!"}


def fake_steps():                                    # NEW
    steps = [
        "Analyst is reading the paper",
        "Detective is searching the code",
        "Critic is judging the evidence",
        "Reporter is writing the report",
    ]
    for step in steps:
        yield f"data: {json.dumps({'step': step})}\n\n"
        time.sleep(1)


@app.get("/stream-demo")                             # NEW
def stream_demo():
    return StreamingResponse(fake_steps(), media_type="text/event-stream")

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


def run_steps():
    yield f"data: {json.dumps({'type': 'step', 'text': 'Indexing the code and the paper...'})}\n\n"
    build_index()
    build_paper_index()

    results = []
    for chunk in graph.stream(start_state(), config={"recursion_limit": 100}, stream_mode="updates"):
        for node, update in chunk.items():
            update = update or {}
            if node == "save_result":
                results += update["results"]
            yield f"data: {json.dumps({'type': 'step', 'text': describe(node, update)})}\n\n"

    report = [
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
    ]
    yield f"data: {json.dumps({'type': 'report', 'results': report})}\n\n"


@app.get("/verify")
def verify():
    return StreamingResponse(run_steps(), media_type="text/event-stream")