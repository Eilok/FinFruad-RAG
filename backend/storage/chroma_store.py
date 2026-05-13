import chromadb
from chromadb.api.models.Collection import Collection

from backend.core.settings import settings
from backend.models.knowledge import KnowledgeRecord


class ChromaKnowledgeStore:
    def __init__(self, collection_name: str | None = None) -> None:
        self.client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self.collection_name = collection_name or settings.chroma_collection_name
        self.collection: Collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def reset_collection(self) -> None:
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:  # noqa: BLE001
            pass
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def _rebind_collection(self) -> None:
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_record(self, record: KnowledgeRecord, embedding: list[float]) -> None:
        payload = {
            "ids": [record.record_id],
            "documents": [record.analysis.summary],
            "embeddings": [embedding],
            "metadatas": [
                {
                    "source": record.source,
                    "category": record.analysis.category,
                    "patterns": " | ".join(record.analysis.patterns),
                    "risk_keywords": " | ".join(record.analysis.risk_keywords),
                    "original_text": record.original_text,
                    "created_at": record.created_at,
                }
            ],
        }
        try:
            self.collection.upsert(**payload)
        except Exception:  # noqa: BLE001
            self._rebind_collection()
            self.collection.upsert(**payload)

    def query_by_embedding(self, query_embedding: list[float], top_k: int) -> dict:
        try:
            return self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["metadatas", "documents", "distances"],
            )
        except Exception:  # noqa: BLE001
            self._rebind_collection()
            return self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["metadatas", "documents", "distances"],
            )

    def fetch_all(self) -> dict:
        try:
            return self.collection.get(include=["metadatas", "documents"])
        except Exception:  # noqa: BLE001
            self._rebind_collection()
            return self.collection.get(include=["metadatas", "documents"])

    def count(self) -> int:
        try:
            return self.collection.count()
        except Exception:  # noqa: BLE001
            self._rebind_collection()
            return self.collection.count()
