from pathlib import Path

import weaviate
from weaviate.classes.query import MetadataQuery
from fastembed import TextEmbedding
from weaviate.classes.config import Configure, DataType, Property

PAPER = Path("sample/paper.md")
COLLECTION = "PaperChunk"

embedder = TextEmbedding("BAAI/bge-small-en-v1.5")


def chunk_paper(path: Path) -> list[dict]:
    chunks = []
    section = "Title"
    lines = []
    for line in path.read_text().splitlines():
        if line.startswith("#"):
            if lines:
                chunks.append({"section": section, "text": " ".join(lines)})
            section = line.lstrip("# ").strip()
            lines = []
        elif line.strip():
            lines.append(line.strip())
    if lines:
        chunks.append({"section": section, "text": " ".join(lines)})
    return chunks


def build_paper_index() -> None:
    chunks = chunk_paper(PAPER)
    vectors = list(embedder.embed([f"{c['section']}: {c['text']}" for c in chunks]))

    with weaviate.connect_to_local() as client:
        if client.collections.exists(COLLECTION):
            client.collections.delete(COLLECTION)
        client.collections.create(
            COLLECTION,
            vector_config=Configure.Vectors.self_provided(),
            properties=[
                Property(name="section", data_type=DataType.TEXT),
                Property(name="text", data_type=DataType.TEXT),
            ],
        )
        papers = client.collections.use(COLLECTION)
        with papers.batch.dynamic() as batch:
            for chunk, vec in zip(chunks, vectors):
                batch.add_object(properties=chunk, vector=vec.tolist())

    print(f"Stored {len(chunks)} paper sections in Weaviate")


def search_paper(query: str, alpha: float = 0.5, limit: int = 3) -> list[dict]:
    qvec = next(embedder.query_embed(query)).tolist()
    with weaviate.connect_to_local() as client:
        res = client.collections.use(COLLECTION).query.hybrid(
            query=query,
            vector=qvec,
            alpha=alpha,
            limit=limit,
            return_metadata=MetadataQuery(score=True),
        )
    return [{**o.properties, "score": o.metadata.score} for o in res.objects]


if __name__ == "__main__":
    build_paper_index()

    for query in ["0.1", "how fast does the model learn at the start"]:
        print(f"\nSearch: {query!r}")
        for alpha in [0.0, 0.5, 1.0]:
            hits = search_paper(query, alpha=alpha, limit=2)
            found = "  |  ".join(f"{h['section']} ({h['score']:.2f})" for h in hits)
            print(f"  alpha={alpha}:  {found}")