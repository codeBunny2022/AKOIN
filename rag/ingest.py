"""Ingest curated corpus into BM25 and vector indices."""
import json
import pickle
from pathlib import Path

from rank_bm25 import BM25Okapi
import chromadb
from chromadb.config import Settings

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import (
    CORPUS_DIR,
    CHUNKS_JSON_PATH,
    BM25_INDEX_PATH,
    CHROMA_PERSIST_DIR,
    EMBEDDING_MODEL,
)


def load_corpus() -> list[dict]:
    """Load curated rules from JSON. Each item is one chunk with chunk_id, source_ref, text."""
    path = CORPUS_DIR / "curated_rules.json"
    if not path.exists():
        raise FileNotFoundError(f"Corpus not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def tokenize_for_bm25(text: str) -> list[str]:
    """Simple tokenizer: lowercase, split on non-alphanumeric."""
    return [t.lower() for t in text.replace("\n", " ").split() if t.isalnum() or len(t) > 1]


def ingest_corpus() -> list[dict]:
    """
    Load corpus, build BM25 index and Chroma collection, persist chunks and indices.
    Returns list of chunk dicts with chunk_id, source_id, source_ref, source_url, template_ref, text.
    """
    chunks = load_corpus()
    if not chunks:
        raise ValueError("Corpus is empty")

    # Persist chunks for retrieval layer
    CHUNKS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CHUNKS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)

    # BM25: tokenized corpus
    tokenized = [tokenize_for_bm25(c["text"]) for c in chunks]
    bm25 = BM25Okapi(tokenized)
    with open(BM25_INDEX_PATH, "wb") as f:
        pickle.dump({"bm25": bm25, "chunks": chunks}, f)

    # Chroma: embeddings
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBEDDING_MODEL)
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=False).tolist()
    ids = [c["chunk_id"] for c in chunks]

    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR, settings=Settings(anonymized_telemetry=False))
    collection_name = "corep_rules"
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
    collection = client.create_collection(name=collection_name, metadata={"description": "PRA COREP rules"})
    collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=[{
        "source_id": c.get("source_id", ""),
        "source_ref": c.get("source_ref", ""),
        "chunk_id": c["chunk_id"],
        "template_ref": c.get("template_ref") or "",
    } for c in chunks])

    return chunks


if __name__ == "__main__":
    ingest_corpus()
    print("Ingestion complete. Chunks:", len(load_corpus()))
