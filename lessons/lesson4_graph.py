from pathlib import Path
from typing import Literal, TypedDict

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

load_dotenv()

REPO = Path("sample/repo")
SEARCH_ORDER = ["models", "utils", "training"]


# ---------- LangChain part (same as lesson 3) ----------

class Verdict(BaseModel):
    status: Literal["MATCH", "MISMATCH", "NOT_FOUND"] = Field(
        description="NOT_FOUND if the code does not contain what the claim is about"
    )
    paper_value: str = Field(description="The value the paper states")
    code_value: str = Field(description="The value in the code, or 'none'")
    reason: str = Field(description="One short sentence explaining the verdict")


llm = ChatAnthropic(model="claude-haiku-5-5", max_tokens=4096)
critic_llm = llm.with_structured_output(Verdict, method="json_schema")


def judge(claim: str, code: str) -> Verdict:
    prompt = f"""Check whether this code implements the claim from the paper.

CLAIM: {claim}

CODE:
{code}"""
    return critic_llm.invoke(prompt)


def read_folder(folder: str) -> str:
    text = ""
    for file in sorted((REPO / folder).glob("*.py")):
        text += f"\n# ===== {file} =====\n{file.read_text()}"
    return text


# ---------- LangGraph part ----------

class State(TypedDict):
    claim: str
    attempt: int
    found_code: str
    verdict: Verdict | None


def detective(state: State) -> dict:
    folder = SEARCH_ORDER[state["attempt"]]
    print(f"Detective searches {folder}/")
    return {"found_code": read_folder(folder), "attempt": state["attempt"] + 1}


def critic(state: State) -> dict:
    verdict = judge(state["claim"], state["found_code"])
    print(f"Critic: {verdict.status} - {verdict.reason}")
    return {"verdict": verdict}


def route_after_critic(state: State) -> str:
    if state["verdict"].status == "NOT_FOUND" and state["attempt"] < len(SEARCH_ORDER):
        print("Router: not found, send the detective to the next folder\n")
        return "detective"
    print("Router: done\n")
    return END


builder = StateGraph(State)
builder.add_node("detective", detective)
builder.add_node("critic", critic)
builder.add_edge(START, "detective")
builder.add_edge("detective", "critic")
builder.add_conditional_edges("critic", route_after_critic, ["detective", END])
graph = builder.compile()

claim = "We train with the AdamW optimizer using a learning rate of 1e-4"
result = graph.invoke({"claim": claim, "attempt": 0, "found_code": "", "verdict": None})

v = result["verdict"]
print(f"FINAL: {v.status}  (paper: {v.paper_value} | code: {v.code_value})")