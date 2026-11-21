"""Code side: split a repo into functions, classes, module-level code and config files; store in Qdrant."""

import ast
import os
from pathlib import Path

from qdrant_client import QdrantClient, models

from backend.embeddings import embed_documents, embed_query
from backend.settings import (
    EMBED_DIM,
    MAX_CHUNK_CHARS,
    MAX_CODE_CHUNKS,
    MAX_PY_FILES,
    QDRANT_URL,
)

SKIP_DIRS = {
    ".git", ".github", ".venv", "venv", "env", "node_modules", "__pycache__", "build", "dist",
    "site-packages", ".tox", ".mypy_cache", ".pytest_cache", ".eggs", "docs", "doc",
}
TEST_DIRS = {"test", "tests", "testing"}
CONFIG_SUFFIXES = {".yaml", ".yml", ".json", ".toml", ".cfg", ".ini"}
MAX_CONFIG_BYTES = 50_000
CONFIG_WINDOW_LINES = 80
BIG_CLASS_LINES = 120
MODULE_GROUP_LINES = 60

_client: QdrantClient | None = None


def _qdrant() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL)
    return _client


# ---------- Walking the repo ----------

def _iter_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            yield Path(dirpath) / name


def is_test_path(rel: Path) -> bool:
    name = rel.name
    return (
        any(part in TEST_DIRS for part in rel.parts[:-1])
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name == "conftest.py"
    )


def _chunk(rel: Path, kind: str, name: str, start: int, end: int, code: str) -> dict:
    return {
        "name": name,
        "type": kind,
        "file_path": rel.as_posix(),
        "start_line": start,
        "end_line": end,
        "is_test": is_test_path(rel),
        "code": code[:MAX_CHUNK_CHARS],
    }


# ---------- Python files ----------

def _is_docstring(node: ast.stmt) -> bool:
    return isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant) and isinstance(node.value.value, str)


def chunk_python(path: Path, rel: Path) -> list[dict]:
    source = path.read_text(errors="replace")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    chunks: list[dict] = []
    module_nodes: list[ast.stmt] = []

    def flush_module() -> None:
        # Top-level code that isn't a def or class: constants, argparse defaults, `if __name__ == "__main__"`.
        # Hyperparameters often live here.
        if not module_nodes:
            return
        start, end = module_nodes[0].lineno, module_nodes[-1].end_lineno or module_nodes[-1].lineno
        code = "\n".join(source.splitlines()[start - 1 : end])
        chunks.append(_chunk(rel, "module", f"{rel.stem} (module code)", start, end, code))
        module_nodes.clear()

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            flush_module()
            chunks.append(_chunk(rel, "function", node.name, node.lineno, node.end_lineno or node.lineno, ast.get_source_segment(source, node) or ""))
        elif isinstance(node, ast.ClassDef):
            flush_module()
            end = node.end_lineno or node.lineno
            if end - node.lineno <= BIG_CLASS_LINES:
                chunks.append(_chunk(rel, "class", node.name, node.lineno, end, ast.get_source_segment(source, node) or ""))
            else:
                # Large class: one chunk per method, so search can point at the exact method.
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        code = ast.get_source_segment(source, item) or ""
                        chunks.append(_chunk(rel, "method", f"{node.name}.{item.name}", item.lineno, item.end_lineno or item.lineno, code))
        elif isinstance(node, (ast.Import, ast.ImportFrom)) or _is_docstring(node):
            continue
        else:
            module_nodes.append(node)
            span = (node.end_lineno or node.lineno) - module_nodes[0].lineno
            if span >= MODULE_GROUP_LINES:
                flush_module()
    flush_module()
    return chunks


# ---------- Config files ----------

def chunk_config(path: Path, rel: Path) -> list[dict]:
    if path.stat().st_size > MAX_CONFIG_BYTES:
        return []
    lines = path.read_text(errors="replace").splitlines()
    chunks = []
    for start in range(0, len(lines), CONFIG_WINDOW_LINES):
        window = lines[start : start + CONFIG_WINDOW_LINES]
        if any(line.strip() for line in window):
            end = start + len(window)
            chunks.append(_chunk(rel, "config", rel.name, start + 1, end, "\n".join(window)))
    return chunks


def chunk_repo(root: Path) -> tuple[list[dict], dict]:
    chunks: list[dict] = []
    py_files = config_files = 0
    for path in _iter_files(root):
        rel = path.relative_to(root)
        if path.suffix == ".py":
            if py_files >= MAX_PY_FILES:
                continue
            py_files += 1
            chunks += chunk_python(path, rel)
        elif path.suffix in CONFIG_SUFFIXES:
            config_files += 1
            chunks += chunk_config(path, rel)
        if len(chunks) >= MAX_CODE_CHUNKS:
            break
    chunks = chunks[:MAX_CODE_CHUNKS]
    stats = {"python_files": py_files, "config_files": config_files, "chunks": len(chunks)}
    return chunks, stats


# ---------- Qdrant ----------

def build_code_index(chunks: list[dict], collection: str) -> None:
    client = _qdrant()
    texts = [f"{c['type']} {c['name']} in {c['file_path']}\n{c['code']}" for c in chunks]
    vectors = embed_documents(texts)
    if client.collection_exists(collection):
        client.delete_collection(collection)
    client.create_collection(
        collection,
        vectors_config=models.VectorParams(size=EMBED_DIM, distance=models.Distance.COSINE),
    )
    client.create_payload_index(collection, field_name="is_test", field_schema=models.PayloadSchemaType.BOOL)
    for start in range(0, len(chunks), 256):
        client.upsert(
            collection,
            points=[
                models.PointStruct(id=start + i, vector=vector, payload=chunk)
                for i, (chunk, vector) in enumerate(zip(chunks[start : start + 256], vectors[start : start + 256]))
            ],
        )


def search_code(collection: str, query: str, limit: int = 3, skip_tests: bool = True) -> list[dict]:
    test_filter = None
    if skip_tests:
        test_filter = models.Filter(must=[models.FieldCondition(key="is_test", match=models.MatchValue(value=False))])
    hits = _qdrant().query_points(collection, query=embed_query(query), query_filter=test_filter, limit=limit).points
    return [{**h.payload, "score": h.score} for h in hits]


def drop_code_collections(prefix: str) -> None:
    client = _qdrant()
    for c in client.get_collections().collections:
        if c.name.startswith(prefix):
            client.delete_collection(c.name)


def drop_code_index(collection: str) -> None:
    client = _qdrant()
    if client.collection_exists(collection):
        client.delete_collection(collection)
