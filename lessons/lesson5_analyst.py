from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

load_dotenv()


class Claim(BaseModel):
    category: Literal["optimizer", "hyperparameter", "architecture", "loss", "other"]
    text: str = Field(description="Short version of the claim, e.g. 'AdamW optimizer, learning rate 1e-4'")
    quote: str = Field(description="The exact sentence from the paper that states it")


class ClaimList(BaseModel):
    claims: list[Claim]


llm = ChatAnthropic(model="claude-haiku-5-5", max_tokens=4096)
analyst_llm = llm.with_structured_output(ClaimList, method="json_schema")

paper = Path("sample/paper.md").read_text()

prompt = f"""Extract every specific, checkable implementation claim from this paper:
optimizer, hyperparameters, model architecture, and loss function.
Skip results, benchmarks, and general statements.

PAPER:
{paper}"""

result = analyst_llm.invoke(prompt)

for i, claim in enumerate(result.claims, start=1):
    print(f"{i}. [{claim.category}] {claim.text}")
    print(f'   quote: "{claim.quote}"')