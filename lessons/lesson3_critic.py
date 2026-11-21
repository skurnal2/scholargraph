from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

load_dotenv()


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


claim = "We train with the AdamW optimizer using a learning rate of 1e-4"

for file in ["sample/repo/models/tinyformer.py", "sample/repo/training/train.py"]:
    verdict = judge(claim, Path(file).read_text())
    print(f"{file}")
    print(f"  status: {verdict.status}")
    print(f"  paper:  {verdict.paper_value}  |  code: {verdict.code_value}")
    print(f"  reason: {verdict.reason}\n")