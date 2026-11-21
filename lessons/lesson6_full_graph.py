import operator
from pathlib import Path
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from tools import Claim, Verdict, extract_claims, judge, read_folder

SEARCH_ORDER = ["models", "utils", "training"]


class State(TypedDict):
    claims: list[Claim]
    current: int
    attempt: int
    found_code: str
    verdict: Verdict | None
    results: Annotated[list[dict], operator.add]


def analyst(state: State) -> dict:
    claims = extract_claims(Path("sample/paper.md").read_text())
    print(f"Analyst found {len(claims)} claims\n")
    return {"claims": claims}


def detective(state: State) -> dict:
    folder = SEARCH_ORDER[state["attempt"]]
    return {"found_code": read_folder(folder), "attempt": state["attempt"] + 1}


def critic(state: State) -> dict:
    claim = state["claims"][state["current"]]
    return {"verdict": judge(claim.text, state["found_code"])}


def route_after_critic(state: State) -> str:
    if state["verdict"].status == "NOT_FOUND" and state["attempt"] < len(SEARCH_ORDER):
        return "detective"
    return "save_result"


def save_result(state: State) -> dict:
    claim = state["claims"][state["current"]]
    verdict = state["verdict"]
    searched = " -> ".join(SEARCH_ORDER[: state["attempt"]])
    print(f"[{state['current'] + 1}/{len(state['claims'])}] {verdict.status:<9} {claim.text}   (searched: {searched})")
    return {
        "results": [{"claim": claim, "verdict": verdict, "folder": SEARCH_ORDER[state["attempt"] - 1]}],
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
            print(f"  paper: {v.paper_value}")
            print(f"  code:  {v.code_value}   (in {r['folder']}/)")
            print(f'  quote: "{r["claim"].quote}"\n')
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

start = {"claims": [], "current": 0, "attempt": 0, "found_code": "", "verdict": None, "results": []}
graph.invoke(start, config={"recursion_limit": 150})