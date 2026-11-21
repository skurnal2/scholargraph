"""Local embeddings with fastembed. The model is loaded once and shared."""

from functools import lru_cache

from fastembed import TextEmbedding

from backend.settings import EMBED_MODEL


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    return TextEmbedding(EMBED_MODEL)


def embed_documents(texts: list[str]) -> list[list[float]]:
    return [vector.tolist() for vector in _model().embed(texts, batch_size=64)]


def embed_query(text: str) -> list[float]:
    return next(_model().query_embed(text)).tolist()
