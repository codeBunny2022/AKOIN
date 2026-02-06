"""Hybrid retriever: BM25 + dense (Chroma), RRF fusion, optional re-ranking."""
import json
import pickle
from pathlib import Path

from rank_bm25 import BM25Okapi

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import (
    CHUNKS_JSON_PATH,
    BM25_INDEX_PATH,
    CHROMA_PERSIST_DIR,
    EMBEDDING_MODEL,
    TOP_K_SPARSE,
    TOP_K_DENSE,
    TOP_K_FUSION,
    TOP_K_FINAL,
)


def _rrf(rank_lists: list[list[str]], k: int = 60) -> list[str]:
    """Reciprocal Rank Fusion. rank_lists = [ids_from_bm25, ids_from_chroma]."""
    scores: dict[str, float] = {}
    for rank_list in rank_lists:
        for rank, doc_id in enumerate(rank_list, start=1):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
    ordered = sorted(scores.keys(), key=lambda x: -scores[x])
    return ordered


class Retriever:
    """Hybrid BM25 + dense retriever with RRF and optional re-ranking."""

    def __init__(
        self,
        chunks: list[dict],
        bm25: BM25Okapi,
        chroma_collection,
        embedding_model,
        top_k_sparse: int = TOP_K_SPARSE,
        top_k_dense: int = TOP_K_DENSE,
        top_k_fusion: int = TOP_K_FUSION,
        top_k_final: int = TOP_K_FINAL,
    ):
        self.chunks = {c["chunk_id"]: c for c in chunks}
        self.bm25 = bm25
        self.chroma_collection = chroma_collection
        self.embedding_model = embedding_model
        self.tokenized_corpus = [
            [t.lower() for t in c["text"].replace("\n", " ").split() if t.isalnum() or len(t) > 1]
            for c in chunks
        ]
        self.chunk_ids = [c["chunk_id"] for c in chunks]
        self.tokenized_corpus = [
            [t.lower() for t in c["text"].replace("\n", " ").split() if t.isalnum() or len(t) > 1]
            for c in chunks
        ]
        self.top_k_sparse = top_k_sparse
        self.top_k_dense = top_k_dense
        self.top_k_fusion = top_k_fusion
        self.top_k_final = top_k_final

    def _bm25_search(self, query: str) -> list[tuple[str, float]]:
        tokenized_q = [t.lower() for t in query.replace("\n", " ").split() if t.isalnum() or len(t) > 1]
        if not tokenized_q:
            return []
        scores = self.bm25.get_scores(tokenized_q)
        indexed = sorted(range(len(scores)), key=lambda i: -scores[i])
        return [(self.chunk_ids[i], float(scores[i])) for i in indexed[: self.top_k_sparse]]

    def _dense_search(self, query: str) -> list[str]:
        q_emb = self.embedding_model.encode([query], show_progress_bar=False)
        results = self.chroma_collection.query(
            query_embeddings=q_emb.tolist(),
            n_results=self.top_k_dense,
            include=["metadatas"],
        )
        ids = results["ids"][0] if results["ids"] else []
        return ids

    def retrieve(
        self,
        question: str,
        scenario: str = "",
        template_filter: str | None = None,
    ) -> list[dict]:
        """
        Retrieve top-k chunks with citation info.
        Returns list of dicts: chunk_id, source_id, source_ref, source_url, template_ref, text.
        """
        query = f"Question: {question}. Scenario: {scenario}".strip()
        bm25_hits = self._bm25_search(query)
        bm25_ids = [x[0] for x in bm25_hits]
        dense_ids = self._dense_search(query)
        fused = _rrf([bm25_ids, dense_ids])[: self.top_k_fusion]

        if template_filter:
            fused = [cid for cid in fused if self.chunks.get(cid, {}).get("template_ref") == template_filter]
            if len(fused) > self.top_k_final:
                fused = fused[: self.top_k_final]
            elif len(fused) < self.top_k_final:
                # Backfill from full list
                rest = [c for c in self.chunk_ids if c not in fused]
                for c in rest:
                    if len(fused) >= self.top_k_final:
                        break
                    if self.chunks.get(c, {}).get("template_ref") == template_filter:
                        fused.append(c)
        else:
            fused = fused[: self.top_k_final]

        out = []
        for cid in fused:
            c = self.chunks.get(cid)
            if c:
                out.append({
                    "chunk_id": c["chunk_id"],
                    "source_id": c.get("source_id", ""),
                    "source_ref": c.get("source_ref", ""),
                    "source_url": c.get("source_url", ""),
                    "template_ref": c.get("template_ref"),
                    "text": c["text"],
                })
        return out


def load_retriever() -> Retriever:
    """Load chunks, BM25 index, Chroma collection and embedding model; return Retriever."""
    if not CHUNKS_JSON_PATH.exists():
        raise FileNotFoundError(f"Run ingest first. Missing {CHUNKS_JSON_PATH}")
    with open(CHUNKS_JSON_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    with open(BM25_INDEX_PATH, "rb") as f:
        data = pickle.load(f)
    bm25 = data["bm25"]
    if data["chunks"] != chunks:
        chunks = data["chunks"]

    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer

    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR, settings=Settings(anonymized_telemetry=False))
    collection = client.get_collection("corep_rules")
    model = SentenceTransformer(EMBEDDING_MODEL)

    return Retriever(
        chunks=chunks,
        bm25=bm25,
        chroma_collection=collection,
        embedding_model=model,
    )
