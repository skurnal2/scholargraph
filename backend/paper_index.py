"""Paper side: split the paper into section-labelled chunks, store them in Weaviate, hybrid-search them."""

import re
from pathlib import Path

import pymupdf
import weaviate
from weaviate.classes.config import Configure, DataType, Property
from weaviate.classes.query import MetadataQuery

from backend.embeddings import embed_documents, embed_query
from backend.settings import WEAVIATE_GRPC_PORT, WEAVIATE_HOST, WEAVIATE_PORT
from backend.sources import PaperSource

CHUNK_CHARS = 1200
OVERLAP_LINES = 2

# Section numbers like "3", "3.2", "3.2.1" (first level 1-19), never table values like "23.75".
SECTION_NUMBER = re.compile(r"^(?:[1-9]|1\d)(?:\.\d{1,2}){0,3}\.?$")
NUMBERED_HEADING = re.compile(r"^(?:[1-9]|1\d)(?:\.\d{1,2}){0,3}\.?\s+(?!Figure|Table|Fig\.)[A-Z][A-Za-z][^.!?\[\]]{1,68}$")
NOT_A_TITLE = re.compile(r"^(Figure|Table|Fig\.)|[\[\]]")
NAMED_HEADING = re.compile(
    r"^(abstract|introduction|related work|background|method(s|ology)?|experiments?|"
    r"results|discussion|conclusions?|references|bibliography|acknowledge?ments?|appendix)$",
    re.IGNORECASE,
)
STOP_SECTIONS = re.compile(r"^(references|bibliography)$", re.IGNORECASE)


def _connect():
    return weaviate.connect_to_local(host=WEAVIATE_HOST, port=WEAVIATE_PORT, grpc_port=WEAVIATE_GRPC_PORT)


# ---------- Chunking ----------

def chunk_markdown(path: Path) -> list[dict]:
    """One chunk per '#' section (used for the bundled sample paper)."""
    chunks, section, lines = [], "Title", []
    for line in path.read_text().splitlines():
        if line.startswith("#"):
            if lines:
                chunks.append({"section": section, "text": " ".join(lines)})
            section, lines = line.lstrip("# ").strip(), []
        elif line.strip():
            lines.append(line.strip())
    if lines:
        chunks.append({"section": section, "text": " ".join(lines)})
    return chunks


def _pdf_lines(path: Path) -> list[str]:
    lines: list[str] = []
    with pymupdf.open(path) as doc:
        for page in doc:
            lines += [line.strip() for line in page.get_text().splitlines() if line.strip()]
    return lines


def chunk_pdf(path: Path) -> list[dict]:
    """
    Size-based chunks with a little overlap, each labelled with the most recent
    section heading we could detect. Stops at References so the bibliography
    doesn't pollute search results.
    """
    lines = _pdf_lines(path)
    chunks: list[dict] = []
    section = "Front matter"
    buffer: list[str] = []

    def flush(keep_overlap: bool) -> None:
        nonlocal buffer
        text = " ".join(buffer).strip()
        if len(text) > 80:
            chunks.append({"section": section, "text": text})
        buffer = buffer[-OVERLAP_LINES:] if keep_overlap else []

    i = 0
    while i < len(lines):
        line = lines[i]
        heading = None
        # PDF text often splits "3.2" and "Training" onto separate lines.
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if SECTION_NUMBER.match(line) and nxt[:1].isupper() and len(nxt) < 70 and not NOT_A_TITLE.search(nxt):
            heading = f"{line} {lines[i + 1]}"
            i += 1
        elif (NUMBERED_HEADING.match(line) or NAMED_HEADING.match(line)) and len(line) < 80:
            heading = line

        if heading:
            flush(keep_overlap=False)
            title_only = re.sub(r"^[\d.]+\s*", "", heading)
            if STOP_SECTIONS.match(title_only):
                break
            section = heading
        else:
            buffer.append(line)
            if sum(len(b) + 1 for b in buffer) >= CHUNK_CHARS:
                flush(keep_overlap=True)
        i += 1

    flush(keep_overlap=False)
    return chunks


def load_paper_chunks(source: PaperSource) -> list[dict]:
    if source.kind == "sample":
        return chunk_markdown(source.path)
    return chunk_pdf(source.path)


# ---------- Weaviate ----------

def build_paper_index(chunks: list[dict], collection: str) -> None:
    vectors = embed_documents([f"{c['section']}: {c['text']}" for c in chunks])
    with _connect() as client:
        if client.collections.exists(collection):
            client.collections.delete(collection)
        client.collections.create(
            collection,
            vector_config=Configure.Vectors.self_provided(),
            properties=[
                Property(name="section", data_type=DataType.TEXT),
                Property(name="text", data_type=DataType.TEXT),
            ],
        )
        papers = client.collections.use(collection)
        with papers.batch.dynamic() as batch:
            for chunk, vector in zip(chunks, vectors):
                batch.add_object(properties=chunk, vector=vector)


def search_paper(collection: str, query: str, alpha: float = 0.5, limit: int = 3) -> list[dict]:
    with _connect() as client:
        res = client.collections.use(collection).query.hybrid(
            query=query,
            vector=embed_query(query),
            alpha=alpha,
            limit=limit,
            return_metadata=MetadataQuery(score=True),
        )
    return [{**o.properties, "score": o.metadata.score} for o in res.objects]


def drop_paper_collections(prefix: str) -> None:
    with _connect() as client:
        for name in client.collections.list_all():
            if name.startswith(prefix):
                client.collections.delete(name)


def drop_paper_index(collection: str) -> None:
    with _connect() as client:
        if client.collections.exists(collection):
            client.collections.delete(collection)
