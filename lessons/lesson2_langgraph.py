from typing import TypedDict
from langgraph.graph import END, START, StateGraph

# NEW: a fake repo. Folder name -> the code inside it.
FAKE_REPO = {
    "models/": "class Transformer(nn.Module): ...",
    "utils/": "def set_seed(seed): ...",
    "training/": "optimizer = AdamW(params, lr=1e-3)",
}
SEARCH_ORDER = ["models/", "utils/", "training/"]   # NEW: where to look, in order


class State(TypedDict):
    claim: str
    attempt: int                                    # NEW: how many searches so far
    found_code: str
    verdict: str


def detective(state: State) -> dict:                # CHANGED: searches one folder per try
    folder = SEARCH_ORDER[state["attempt"]]
    print(f"Detective searches {folder}")
    return {"found_code": FAKE_REPO[folder], "attempt": state["attempt"] + 1}


def critic(state: State) -> dict:                   # CHANGED: can say "not found yet"
    code = state["found_code"]
    print(f"Critic is checking: {code}")
    if "AdamW" not in code:
        return {"verdict": "NOT FOUND YET"}
    if "lr=1e-4" in code:
        return {"verdict": "MATCH"}
    return {"verdict": "MISMATCH"}


def route_after_critic(state: State) -> str:        # NEW: the router
    if state["verdict"] == "NOT FOUND YET" and state["attempt"] < len(SEARCH_ORDER):
        print("Router: not found, send detective back\n")
        return "detective"
    print("Router: done, go to END")
    return END


builder = StateGraph(State)
builder.add_node("detective", detective)
builder.add_node("critic", critic)
builder.add_edge(START, "detective")
builder.add_edge("detective", "critic")
builder.add_conditional_edges("critic", route_after_critic, ["detective", END])   # CHANGED
graph = builder.compile()

result = graph.invoke({"claim": "AdamW, lr=1e-4", "attempt": 0, "found_code": "", "verdict": ""})
print("\nFinal state:", result)