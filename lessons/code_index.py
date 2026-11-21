import ast
from pathlib import Path

from fastembed import TextEmbedding                     # NEW
from qdrant_client import QdrantClient, models          # NEW

REPO = Path("sample/repo")
COLLECTION = "code_chunks"                              # NEW

embedder = TextEmbedding("BAAI/bge-small-en-v1.5")      # NEW
qdrant = QdrantClient(url="http://localhost:6333")      # NEW


def chunk_file(path: Path) -> list[dict]:
    source = path.read_text()
    tree = ast.parse(source)
    chunks = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            chunks.append({
                "name": node.name,
                "type": "class" if isinstance(node, ast.ClassDef) else "function",
                "file_path": str(path.relative_to(REPO)),
                "start_line": node.lineno,
                "end_line": node.end_lineno,
                "is_test": "tests" in path.parts or path.name.startswith("test_"),
                "code": ast.get_source_segment(source, node),
            })
    return chunks


def chunk_repo() -> list[dict]:
    chunks = []
    for file in sorted(REPO.rglob("*.py")):
        chunks += chunk_file(file)
    return chunks


def build_index() -> None:                              # NEW: whole function
    chunks = chunk_repo()
    texts = [f"{c['type']} {c['name']} in {c['file_path']}\n{c['code']}" for c in chunks]
    vectors = list(embedder.embed(texts))

    if qdrant.collection_exists(COLLECTION):
        qdrant.delete_collection(COLLECTION)
    qdrant.create_collection(
        COLLECTION,
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    )
    qdrant.upsert(
        COLLECTION,
        points=[
            models.PointStruct(id=i, vector=vec.tolist(), payload=chunk)
            for i, (chunk, vec) in enumerate(zip(chunks, vectors))
        ],
    )
    print(f"Stored {len(chunks)} code chunks in Qdrant")


def search_code(query: str, limit: int = 3, skip_tests: bool = True) -> list[dict]:
    qvec = next(embedder.query_embed(query)).tolist()

    test_filter = None
    if skip_tests:
        test_filter = models.Filter(
            must=[models.FieldCondition(key="is_test", match=models.MatchValue(value=False))]
        )

    hits = qdrant.query_points(COLLECTION, query=qvec, query_filter=test_filter, limit=limit).points
    return [{**h.payload, "score": h.score} for h in hits]

if __name__ == "__main__":
    build_index()

    query = "AdamW optimizer, learning rate 1e-4"
    for skip in [False, True]:
        print(f"\nSearch: {query!r}   skip_tests={skip}")
        for h in search_code(query, skip_tests=skip):
            print(f"  {h['score']:.3f}  {h['name']:<26} {h['file_path']}:{h['start_line']}-{h['end_line']}")

    query = "Linear learning rate warmup over first 4000 steps"
    print(f"\nSearch: {query!r}")
    for h in search_code(query):
        print(f"  {h['score']:.3f}  {h['name']:<26} {h['file_path']}:{h['start_line']}-{h['end_line']}")