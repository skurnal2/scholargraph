"""LangGraph layer: Analyst -> (Detective <-> Critic per claim) -> Reporter.

Same flow as lessons/lesson8_hybrid_graph.py. The differences: the collection
names travel in the state (each run has its own), and there are no prints.
"""

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.code_index import search_code
from backend.llm import Claim, Verdict, extract_claims, judge
from backend.paper_index import search_paper
from backend.settings import MAX_ATTEMPTS

PAPER_TOPICS = [
    "optimizer and learning rate",
    "batch size, epochs, warmup and training schedule",
    "model architecture: layers, attention heads, hidden size, dropout",
    "loss function and regularization",
    "hyperparameters and implementation details",
]


class State(TypedDict):
    paper_collection: str
    code_collection: str
    paper_sections: list[dict]  # what the Analyst retrieved (for the UI)
    claims: list[Claim]
    current: int
    attempt: int
    found_query: str
    found_hits: list[dict]  # what the Detective retrieved (for the UI)
    found_code: str
    found_where: str
    verdict: Verdict | None
    results: Annotated[list[dict], operator.add]


def analyst(state: State) -> dict:
    found: dict[str, dict] = {}
    for topic in PAPER_TOPICS:
        for hit in search_paper(state["paper_collection"], topic, alpha=0.5, limit=3):
            key = f"{hit['section']}|{hit['text'][:60]}"
            entry = found.setdefault(key, {"section": hit["section"], "text": hit["text"], "score": 0.0, "topics": []})
            entry["score"] = max(entry["score"], hit["score"] or 0.0)
            entry["topics"].append(topic)

    paper_text = "\n\n".join(f"## {e['section']}\n{e['text']}" for e in found.values())
    sections = [
        {"section": e["section"], "score": round(e["score"], 3), "topics": e["topics"], "preview": e["text"][:240]}
        for e in sorted(found.values(), key=lambda e: -e["score"])
    ]
    return {"claims": extract_claims(paper_text), "paper_sections": sections}


def detective(state: State) -> dict:
    claim = state["claims"][state["current"]]
    limit = 3 if state["attempt"] == 0 else 6
    hits = search_code(state["code_collection"], claim.text, limit=limit)
    code = "\n\n".join(
        f"# ===== {h['file_path']} lines {h['start_line']}-{h['end_line']} ({h['type']} {h['name']}) =====\n{h['code']}"
        for h in hits
    )
    where = ", ".join(f"{h['file_path']}:{h['start_line']}" for h in hits)
    found_hits = [
        {k: h[k] for k in ("file_path", "start_line", "end_line", "name", "type")} | {"score": round(h["score"], 3)}
        for h in hits
    ]
    return {
        "found_query": claim.text,
        "found_hits": found_hits,
        "found_code": code,
        "found_where": where,
        "attempt": state["attempt"] + 1,
    }


def critic(state: State) -> dict:
    claim = state["claims"][state["current"]]
    return {"verdict": judge(claim.text, state["found_code"])}


def route_after_critic(state: State) -> str:
    if state["verdict"].status == "NOT_FOUND" and state["attempt"] < MAX_ATTEMPTS:
        return "detective"
    return "save_result"


def save_result(state: State) -> dict:
    return {
        "results": [{"claim": state["claims"][state["current"]], "verdict": state["verdict"], "where": state["found_where"]}],
        "current": state["current"] + 1,
        "attempt": 0,
    }


def route_after_analyst(state: State) -> str:
    return "detective" if state["claims"] else "reporter"


def route_after_save(state: State) -> str:
    return "detective" if state["current"] < len(state["claims"]) else "reporter"


def reporter(state: State) -> dict:
    return {}


builder = StateGraph(State)
builder.add_node("analyst", analyst)
builder.add_node("detective", detective)
builder.add_node("critic", critic)
builder.add_node("save_result", save_result)
builder.add_node("reporter", reporter)

builder.add_edge(START, "analyst")
builder.add_conditional_edges("analyst", route_after_analyst, ["detective", "reporter"])
builder.add_edge("detective", "critic")
builder.add_conditional_edges("critic", route_after_critic, ["detective", "save_result"])
builder.add_conditional_edges("save_result", route_after_save, ["detective", "reporter"])
builder.add_edge("reporter", END)
graph = builder.compile()


def start_state(paper_collection: str, code_collection: str) -> State:
    return {
        "paper_collection": paper_collection,
        "code_collection": code_collection,
        "paper_sections": [],
        "claims": [],
        "current": 0,
        "attempt": 0,
        "found_query": "",
        "found_hits": [],
        "found_code": "",
        "found_where": "",
        "verdict": None,
        "results": [],
    }
