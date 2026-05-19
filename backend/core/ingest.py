import uuid
from typing import Iterable

from backend.core.logging_utils import append_jsonl, now_iso
from backend.core.settings import settings
from backend.models.api import IngestItem, IngestResult
from backend.models.knowledge import KnowledgeRecord
from backend.providers.embedding_client import EmbeddingClient
from backend.providers.llm_client import LLMAnalyzer
from backend.storage.chroma_store import ChromaKnowledgeStore


class IngestPipeline:
    def __init__(self, collection_name: str | None = None) -> None:
        self.llm = LLMAnalyzer()
        self.embedder = EmbeddingClient()
        self.store = ChromaKnowledgeStore(collection_name=collection_name)

    def ingest_items(
        self,
        items: Iterable[IngestItem],
        retry_times: int | None = None,
    ) -> tuple[list[IngestResult], list[str], list[str]]:
        retries = settings.ingest_retry_times if retry_times is None else retry_times
        results: list[IngestResult] = []
        errors: list[str] = []
        skipped_messages: list[str] = []

        for item in items:
            ok = False
            last_error = ""
            for attempt in range(retries + 1):
                try:
                    result, skip_reason = self._process_one(item)
                    if skip_reason:
                        skipped_messages.append(skip_reason)
                        append_jsonl(
                            "ingest.jsonl",
                            {
                                "time": now_iso(),
                                "status": "skipped",
                                "source": item.source,
                                "reason": skip_reason,
                            },
                        )
                        ok = True
                        break

                    if result is None:
                        last_error = f"source={item.source}, attempt={attempt + 1}, error=Unexpected empty ingestion result"
                        continue

                    results.append(result)
                    append_jsonl(
                        "ingest.jsonl",
                        {
                            "time": now_iso(),
                            "status": "success",
                            "source": item.source,
                            "record_id": result.record_id,
                            "summary": result.summary,
                            "category": result.category,
                            "risk_keywords": result.risk_keywords,
                        },
                    )
                    ok = True
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = f"source={item.source}, attempt={attempt + 1}, error={exc}"

            if not ok:
                errors.append(last_error)
                append_jsonl(
                    "ingest.jsonl",
                    {
                        "time": now_iso(),
                        "status": "failed",
                        "source": item.source,
                        "error": last_error,
                    },
                )

        return results, errors, skipped_messages

    def _process_one(self, item: IngestItem) -> tuple[IngestResult | None, str | None]:
        analysis = self.llm.analyze(item.text)
        if not analysis.risk_keywords:
            return None, "No scam information extracted; skipped from knowledge base."

        embedding = self.embedder.embed_text(analysis.summary)

        record = KnowledgeRecord(
            record_id=str(uuid.uuid4()),
            source=item.source,
            original_text=item.text,
            analysis=analysis,
            created_at=now_iso(),
        )
        self.store.upsert_record(record, embedding)

        return (
            IngestResult(
                record_id=record.record_id,
                source=record.source,
                summary=record.analysis.summary,
                category=record.analysis.category,
                risk_keywords=record.analysis.risk_keywords,
            ),
            None,
        )
