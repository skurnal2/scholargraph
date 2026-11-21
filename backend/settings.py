"""All configuration in one place. Values can be overridden with environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_PAPER = ROOT / "sample" / "paper.md"
SAMPLE_REPO = ROOT / "sample" / "repo"

# Services
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
WEAVIATE_HOST = os.getenv("WEAVIATE_HOST", "localhost")
WEAVIATE_PORT = int(os.getenv("WEAVIATE_PORT", "8080"))
WEAVIATE_GRPC_PORT = int(os.getenv("WEAVIATE_GRPC_PORT", "50051"))
FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")

# Models
LLM_MODEL = os.getenv("LLM_MODEL", "claude-haiku-5-5")
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384

# Limits (keep cost and run time predictable on real papers and repos)
MAX_CLAIMS = int(os.getenv("MAX_CLAIMS", "25"))
MAX_ATTEMPTS = 2
MAX_PY_FILES = int(os.getenv("MAX_PY_FILES", "400"))
MAX_CODE_CHUNKS = int(os.getenv("MAX_CODE_CHUNKS", "4000"))
MAX_CHUNK_CHARS = 4000
MAX_PDF_BYTES = 40 * 1024 * 1024
CLONE_TIMEOUT_S = 120
HTTP_TIMEOUT_S = 60

# Each run gets its own collections, named with these prefixes plus a run id.
PAPER_COLLECTION_PREFIX = "SgPaper_"
CODE_COLLECTION_PREFIX = "sg_code_"
