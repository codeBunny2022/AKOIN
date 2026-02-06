"""Configuration for PRA COREP Reporting Assistant."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
# Load .env from project root so OPENAI_API_KEY etc. are available
load_dotenv(BASE_DIR / ".env")
DATA_DIR = BASE_DIR / "data"
CORPUS_DIR = DATA_DIR / "corpus"
INDEX_DIR = BASE_DIR / "index_store"
SCHEMA_DIR = BASE_DIR / "schemas"

INDEX_DIR.mkdir(parents=True, exist_ok=True)
CORPUS_DIR.mkdir(parents=True, exist_ok=True)
SCHEMA_DIR.mkdir(parents=True, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
CHROMA_PERSIST_DIR = str(INDEX_DIR / "chroma")
BM25_INDEX_PATH = INDEX_DIR / "bm25_index.pkl"
CHUNKS_JSON_PATH = INDEX_DIR / "chunks.json"

# RAG
CHUNK_MAX_TOKENS = 400
TOP_K_SPARSE = 10
TOP_K_DENSE = 10
TOP_K_FUSION = 15
TOP_K_FINAL = 8
