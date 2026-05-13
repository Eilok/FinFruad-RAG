import chromadb
from chromadb.api.models.Collection import Collection

from backend.core.settings import settings
from backend.models.knowledge import KnowledgeRecord

import os
os.environ["CHROMA_TELEMETRY_DISABLED"] = "true"

class ChromaKnowledgeStore:
    def __init__(self) -> None:
        self.client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self.collection: Collection = self.client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_record(self, record: KnowledgeRecord, embedding: list[float]) -> None:
        self.collection.upsert(
            ids=[record.record_id],
            documents=[record.analysis.summary],
            embeddings=[embedding],
            metadatas=[
                {
                    "source": record.source,
                    "category": record.analysis.category,
                    "patterns": " | ".join(record.analysis.patterns),
                    "risk_keywords": " | ".join(record.analysis.risk_keywords),
                    "original_text": record.original_text,
                    "created_at": record.created_at,
                }
            ],
        )

    def query_by_embedding(self, query_embedding: list[float], top_k: int) -> dict:
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["metadatas", "documents", "distances"],
        )

    def fetch_all(self) -> dict:
        return self.collection.get(include=["metadatas", "documents"])

    def count(self) -> int:
        return self.collection.count()
