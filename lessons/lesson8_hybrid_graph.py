import operator
from pathlib import Path
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from code_index import build_index, search_code
from paper_index import build_paper_index, search_paper
from tools import Claim, Verdict, extract_claims, judge

MAX_ATTEMPTS = 2

PAPER_TOPICS = [
    "optimizer and learning rate",
    "batch size, epochs and training schedule",
    "model architecture: layers, attention heads, hidden size, dropout",
    "loss function",
]

class State(TypedDict):
    claims: list[Claim]
    current: int
    attempt: int
    found_code: str
    found_where: str
    verdict: Verdict | None
    results: Annotated[list[dict], operator.add]


def analyst(state: State) -> dict:
    sections = {}
    for topic in PAPER_TOPICS:
        for hit in search_paper(topic, alpha=0.5, limit=2):
            sections[hit["section"]] = hit["text"]
    print(f"Analyst retrieved sections: {list(sections)}")

    paper_text = "\n\n".join(f"## {name}\n{text}" for name, text in sections.items())
    claims = extract_claims(paper_text)
    print(f"Analyst found {len(claims)} claims\n")
    return {"claims": claims}


def detective(state: State) -> dict:
    claim = state["claims"][state["current"]]
    limit = 3 if state["attempt"] == 0 else 6
    hits = search_code(claim.text, limit=limit)
    code = "\n\n".join(
        f"# ===== {h['file_path']} lines {h['start_line']}-{h['end_line']} =====\n{h['code']}"
        for h in hits
    )
    where = ", ".join(f"{h['file_path']}:{h['start_line']}" for h in hits)
    return {"found_code": code, "found_where": where, "attempt": state["attempt"] + 1}


def critic(state: State) -> dict:
    claim = state["claims"][state["current"]]
    return {"verdict": judge(claim.text, state["found_code"])}


def route_after_critic(state: State) -> str:
    if state["verdict"].status == "NOT_FOUND" and state["attempt"] < MAX_ATTEMPTS:
        return "detective"
    return "save_result"


def save_result(state: State) -> dict:
    claim = state["claims"][state["current"]]
    verdict = state["verdict"]
    print(f"[{state['current'] + 1}/{len(state['claims'])}] {verdict.status:<9} {claim.text}   (searches: {state['attempt']})")
    return {
        "results": [{"claim": claim, "verdict": verdict, "where": state["found_where"]}],
        "current": state["current"] + 1,
        "attempt": 0,
    }


def route_after_save(state: State) -> str:
    if state["current"] < len(state["claims"]):
        return "detective"
    return "reporter"


def reporter(state: State) -> dict:
    statuses = [r["verdict"].status for r in state["results"]]
    print("\n========== REPORT ==========")
    print(f"MATCH: {statuses.count('MATCH')}   MISMATCH: {statuses.count('MISMATCH')}   NOT_FOUND: {statuses.count('NOT_FOUND')}\n")
    for r in state["results"]:
        if r["verdict"].status != "MATCH":
            v = r["verdict"]
            print(f"{v.status}: {r['claim'].text}")
            print(f"  paper:    {v.paper_value}")
            print(f"  code:     {v.code_value}")
            print(f"  searched: {r['where']}")
            print(f'  quote:    "{r["claim"].quote}"  (section {r["claim"].section})\n')
    return {}


builder = StateGraph(State)
builder.add_node("analyst", analyst)
builder.add_node("detective", detective)
builder.add_node("critic", critic)
builder.add_node("save_result", save_result)
builder.add_node("reporter", reporter)

builder.add_edge(START, "analyst")
builder.add_edge("analyst", "detective")
builder.add_edge("detective", "critic")
builder.add_conditional_edges("critic", route_after_critic, ["detective", "save_result"])
builder.add_conditional_edges("save_result", route_after_save, ["detective", "reporter"])
builder.add_edge("reporter", END)
graph = builder.compile()

def start_state() -> dict:
    return {"claims": [], "current": 0, "attempt": 0, "found_code": "", "found_where": "", "verdict": None, "results": []}


if __name__ == "__main__":
    build_index()
    build_paper_index()
    graph.invoke(start_state(), config={"recursion_limit": 100})