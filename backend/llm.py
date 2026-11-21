"""LangChain layer: the two Claude calls (extract claims, judge a claim) with structured output."""

from typing import Literal

from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

from backend.settings import LLM_MODEL, MAX_CLAIMS

llm = ChatAnthropic(model=LLM_MODEL, max_tokens=8192)


class Claim(BaseModel):
    category: Literal["optimizer", "hyperparameter", "architecture", "loss", "other"]
    text: str = Field(description="Short version of the claim, e.g. 'AdamW optimizer, learning rate 1e-4'")
    quote: str = Field(description="The exact sentence from the paper that states it")
    section: str = Field(description="The section heading the claim comes from, e.g. '4. Training'")


class ClaimList(BaseModel):
    claims: list[Claim]


class Verdict(BaseModel):
    status: Literal["MATCH", "MISMATCH", "NOT_FOUND"] = Field(
        description="NOT_FOUND if the code shown does not contain the implementation of what the claim is about"
    )
    paper_value: str = Field(description="The value the paper states")
    code_value: str = Field(description="The value in the code, or 'none'")
    reason: str = Field(description="One short sentence explaining the verdict")


_analyst = llm.with_structured_output(ClaimList, method="json_schema")
_critic = llm.with_structured_output(Verdict, method="json_schema")


def extract_claims(paper_text: str) -> list[Claim]:
    prompt = f"""Extract specific, checkable implementation claims from these paper excerpts:
optimizer, hyperparameters (learning rate, batch size, epochs, warmup, weight decay...),
model architecture (layers, heads, dimensions, dropout...), and loss function.
Skip results, benchmarks, dataset statistics and general statements.
Return at most {MAX_CLAIMS} claims, preferring the most concrete values.
The text may come from a PDF, so ignore broken line wraps and stray symbols.

PAPER EXCERPTS:
{paper_text}"""
    return _analyst.invoke(prompt).claims[:MAX_CLAIMS]


def judge(claim: str, code: str) -> Verdict:
    prompt = f"""Check whether this code implements the claim from the paper.
Look at default arguments, values passed at call sites, and config files.
If the code shown is unrelated to the claim, answer NOT_FOUND.

CLAIM: {claim}

CODE:
{code}"""
    return _critic.invoke(prompt)
