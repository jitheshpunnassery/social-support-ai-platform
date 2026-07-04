"""
Qdrant-backed vector store. Used for two things in this solution:
  1. Semantic search over policy/eligibility-criteria documents, so the
     chatbot can answer applicant questions ("why was I declined?", "what
     support am I eligible for?") grounded in actual policy text (RAG).
  2. Similar-precedent lookup: embedding each decided application's feature
     summary so the Decision Agent (or a human reviewer) can retrieve
     similar past cases and their outcomes for consistency checks --
     directly targeting the "Subjective Decision-Making" pain point by
     making precedent comparable rather than tribal knowledge.

A simple hash-based embedding stand-in is used when no local embedding
model is configured, so the interface/collection design is demonstrable
without requiring a GPU or extra model download; swapping in a real local
embedding model (e.g. via Ollama `nomic-embed-text`) is a one-line change
in `_embed`.
"""
import hashlib
import logging

import numpy as np

from config import settings

logger = logging.getLogger(__name__)

EMBED_DIM = 128


def _embed(text: str) -> list:
    """Deterministic lightweight embedding fallback (hashing trick).
    Swap for a real local embedding model in production."""
    vec = np.zeros(EMBED_DIM, dtype=np.float32)
    for token in text.lower().split():
        idx = int(hashlib.md5(token.encode()).hexdigest(), 16) % EMBED_DIM
        vec[idx] += 1.0
    norm = np.linalg.norm(vec)
    return (vec / norm if norm else vec).tolist()


class VectorStore:
    def __init__(self):
        self._client = None
        self._local_index = []  # fallback: list of (id, vector, payload)
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams

            self._client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=1.5)
            self._client.get_collections()
            collections = [c.name for c in self._client.get_collections().collections]
            if settings.QDRANT_COLLECTION not in collections:
                self._client.create_collection(
                    collection_name=settings.QDRANT_COLLECTION,
                    vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
                )
            logger.info("Connected to Qdrant at %s:%s", settings.QDRANT_HOST, settings.QDRANT_PORT)
        except Exception as e:  # noqa: BLE001
            logger.warning("Qdrant unavailable (%s) - using in-memory vector fallback.", e)
            self._client = None

    def upsert(self, point_id: str, text: str, payload: dict):
        vector = _embed(text)
        if self._client is not None:
            from qdrant_client.models import PointStruct
            self._client.upsert(collection_name=settings.QDRANT_COLLECTION,
                                 points=[PointStruct(id=point_id, vector=vector, payload=payload)])
        else:
            self._local_index.append((point_id, np.array(vector), payload))

    def search(self, query: str, top_k: int = 3):
        vector = np.array(_embed(query))
        if self._client is not None:
            hits = self._client.search(collection_name=settings.QDRANT_COLLECTION, query_vector=vector.tolist(), limit=top_k)
            return [{"score": h.score, "payload": h.payload} for h in hits]
        scored = []
        for pid, vec, payload in self._local_index:
            denom = (np.linalg.norm(vec) * np.linalg.norm(vector)) or 1
            sim = float(np.dot(vec, vector) / denom)
            scored.append({"score": sim, "payload": payload})
        return sorted(scored, key=lambda x: -x["score"])[:top_k]


vector_store = VectorStore()
