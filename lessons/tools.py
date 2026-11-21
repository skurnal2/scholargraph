from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

load_dotenv()

REPO = Path("sample/repo")
llm = ChatAnthropic(model="claude-haiku-5-5", max_tokens=4096)


# ---------- Paper Analyst ----------

class Claim(BaseModel):
    category: Literal["optimizer", "hyperparameter", "architecture", "loss", "other"]
    text: str = Field(description="Short version of the claim, e.g. 'AdamW optimizer, learning rate 1e-4'")
    quote: str = Field(description="The exact sentence from the paper that states it")
    section: str = Field(description="The section heading the claim comes from, e.g. '4. Training'")

class ClaimList(BaseModel):
    claims: list[Claim]


analyst_llm = llm.with_structured_output(ClaimList, method="json_schema")


def extract_claims(paper: str) -> list[Claim]:
    prompt = f"""Extract every specific, checkable implementation claim from this paper:
optimizer, hyperparameters, model architecture, and loss function.
Skip results, benchmarks, and general statements.

PAPER:
{paper}"""
    return analyst_llm.invoke(prompt).claims


# ---------- Critic ----------

class Verdict(BaseModel):
    status: Literal["MATCH", "MISMATCH", "NOT_FOUND"] = Field(
        description="NOT_FOUND if the code does not contain what the claim is about"
    )
    paper_value: str = Field(description="The value the paper states")
    code_value: str = Field(description="The value in the code, or 'none'")
    reason: str = Field(description="One short sentence explaining the verdict")


critic_llm = llm.with_structured_output(Verdict, method="json_schema")


def judge(claim: str, code: str) -> Verdict:
    prompt = f"""Check whether this code implements the claim from the paper.

CLAIM: {claim}

CODE:
{code}"""
    return critic_llm.invoke(prompt)


# ---------- Detective's helper ----------

def read_folder(folder: str) -> str:
    text = ""
    for file in sorted((REPO / folder).glob("*.py")):
        text += f"\n# ===== {file} =====\n{file.read_text()}"
    return text


if __name__ == "__main__":
    print("tools.py loaded OK")
    print(read_folder("utils"))