"""Turn user input into local files: the bundled sample, an arXiv PDF, or a cloned GitHub repo."""

import os
import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import httpx

from backend.settings import (
    CLONE_TIMEOUT_S,
    HTTP_TIMEOUT_S,
    MAX_PDF_BYTES,
    SAMPLE_PAPER,
    SAMPLE_REPO,
)

USER_AGENT = "ScholarGraph/0.1 (paper-code verification prototype)"
SAMPLE_WORDS = {"", "sample", "demo"}

ARXIV_NEW_ID = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?")
ARXIV_OLD_ID = re.compile(r"([a-z\-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?")
GITHUB_URL = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


class InputError(Exception):
    """A problem with what the user typed (bad URL, missing paper, private repo...)."""


@dataclass
class PaperSource:
    kind: str  # "sample" or "arxiv"
    label: str  # what the UI shows, e.g. "arXiv 1706.03762"
    title: str
    path: Path
    url: str | None = None


@dataclass
class RepoSource:
    kind: str  # "sample" or "github"
    label: str  # e.g. "owner/repo"
    path: Path
    url: str | None = None


# ---------- Paper ----------

def parse_arxiv_id(text: str) -> str:
    text = text.strip()
    for pattern in (ARXIV_NEW_ID, ARXIV_OLD_ID):
        match = pattern.search(text)
        if match:
            return match.group(1) + (match.group(2) or "")
    raise InputError(
        f"'{text}' doesn't look like an arXiv ID or URL. Try something like 1706.03762 "
        "or https://arxiv.org/abs/1706.03762."
    )


def _arxiv_title(client: httpx.Client, arxiv_id: str) -> str | None:
    try:
        resp = client.get("https://export.arxiv.org/api/query", params={"id_list": arxiv_id})
        resp.raise_for_status()
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = ET.fromstring(resp.text).find("atom:entry", ns)
        title = entry.find("atom:title", ns).text if entry is not None else None
        return " ".join(title.split()) if title else None
    except (httpx.HTTPError, ET.ParseError, AttributeError):
        return None


def resolve_paper(text: str, workdir: Path) -> PaperSource:
    if text.strip().lower() in SAMPLE_WORDS:
        return PaperSource("sample", "sample/paper.md", "TinyFormer (sample paper)", SAMPLE_PAPER)

    arxiv_id = parse_arxiv_id(text)
    url = f"https://arxiv.org/pdf/{arxiv_id}"
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(timeout=HTTP_TIMEOUT_S, follow_redirects=True, headers=headers) as client:
        title = _arxiv_title(client, arxiv_id)
        try:
            resp = client.get(url)
        except httpx.HTTPError as exc:
            raise InputError(f"Couldn't download arXiv {arxiv_id}: {exc}") from exc

    if resp.status_code == 404:
        raise InputError(f"arXiv has no paper with ID {arxiv_id}.")
    if resp.status_code != 200 or not resp.content.startswith(b"%PDF"):
        raise InputError(f"arXiv didn't return a PDF for {arxiv_id} (HTTP {resp.status_code}).")
    if len(resp.content) > MAX_PDF_BYTES:
        raise InputError(f"The PDF for {arxiv_id} is too large to process.")

    path = workdir / "paper.pdf"
    path.write_bytes(resp.content)
    return PaperSource("arxiv", f"arXiv {arxiv_id}", title or f"arXiv {arxiv_id}", path, f"https://arxiv.org/abs/{arxiv_id}")


# ---------- Repo ----------

def resolve_repo(text: str, workdir: Path) -> RepoSource:
    if text.strip().lower() in SAMPLE_WORDS:
        return RepoSource("sample", "sample/repo", SAMPLE_REPO)

    match = GITHUB_URL.match(text.strip())
    if not match:
        raise InputError(
            f"'{text}' isn't a GitHub repository URL. Use the form https://github.com/owner/repo."
        )
    owner, name = match.group(1), match.group(2)
    url = f"https://github.com/{owner}/{name}"
    dest = workdir / "repo"

    # Only public github.com repos over HTTPS; never prompt for credentials.
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    cmd = ["git", "clone", "--depth", "1", "--single-branch", "--no-tags", "--quiet", f"{url}.git", str(dest)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=CLONE_TIMEOUT_S, env=env)
    except subprocess.TimeoutExpired as exc:
        raise InputError(f"Cloning {owner}/{name} took too long. The repo may be too large.") from exc
    if result.returncode != 0:
        raise InputError(f"Couldn't clone {owner}/{name}. Is it a public repository?")

    return RepoSource("github", f"{owner}/{name}", dest, url)
