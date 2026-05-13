import re
from collections import defaultdict

from backend.core.settings import settings
from backend.models.api import DetectRequest, DetectResponse, DetectionResult, EvidenceItem
from backend.providers.embedding_client import EmbeddingClient
from backend.providers.llm_client import LLMAnalyzer
from backend.storage.chroma_store import ChromaKnowledgeStore


class DetectPipeline:
    def __init__(self) -> None:
        self.embedder = EmbeddingClient()
        self.llm = LLMAnalyzer()
        self.store = ChromaKnowledgeStore()

    def run(self, req: DetectRequest) -> DetectResponse:
        text = self._normalize_text(req.text)
        keyword_top_k = req.keyword_top_k or settings.default_keyword_top_k
        vector_top_k = req.vector_top_k or settings.default_vector_top_k

        extracted_keywords = self._extract_keywords(text)
        keyword_hits = self._keyword_retrieval(extracted_keywords, top_k=keyword_top_k)
        vector_hits = self._vector_retrieval(text, top_k=vector_top_k)
        fused_hits = self._fuse_hits(keyword_hits, vector_hits)

        evidence_context = self._build_evidence_context(fused_hits)
        detection = self._safe_detect(text=text, evidence_context=evidence_context)

        return DetectResponse(
            keyword_hits=keyword_hits if req.return_evidence else [],
            vector_hits=vector_hits if req.return_evidence else [],
            fused_hits=fused_hits if req.return_evidence else [],
            detection=detection,
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            raise ValueError("Input text cannot be empty")
        return normalized

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        words = re.findall(r"[A-Za-z0-9$%]+|[\u4e00-\u9fff]{2,}", text)
        uniq: list[str] = []
        seen: set[str] = set()
        for w in words:
            lw = w.lower()
            if lw not in seen:
                seen.add(lw)
                uniq.append(w)
        return uniq

    def _keyword_retrieval(self, query_keywords: list[str], top_k: int) -> list[EvidenceItem]:
        dataset = self.store.fetch_all()
        ids = dataset.get("ids") or []
        docs = dataset.get("documents") or []
        metadatas = dataset.get("metadatas") or []

        scored: list[EvidenceItem] = []
        for idx, record_id in enumerate(ids):
            metadata = metadatas[idx] if idx < len(metadatas) else {}
            doc = docs[idx] if idx < len(docs) else ""
            keyword_field = str((metadata or {}).get("risk_keywords") or "")
            db_keywords = [k.strip() for k in keyword_field.split("|") if k.strip()]

            matched = [k for k in db_keywords if any(k.lower() in q.lower() or q.lower() in k.lower() for q in query_keywords)]
            if not matched:
                continue

            score = min(1.0, len(set(matched)) / max(1, len(db_keywords)))
            scored.append(
                EvidenceItem(
                    record_id=str(record_id),
                    source=str((metadata or {}).get("source") or "unknown"),
                    summary=str(doc or ""),
                    category=str((metadata or {}).get("category") or "Unknown"),
                    patterns=self._split_pipe_values((metadata or {}).get("patterns")),
                    risk_keywords=db_keywords,
                    score=score,
                    retrieval_mode="keyword",
                    matched_keywords=sorted(set(matched)),
                )
            )

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def _vector_retrieval(self, text: str, top_k: int) -> list[EvidenceItem]:
        query_embedding = self.embedder.embed_text(text)
        result = self.store.query_by_embedding(query_embedding=query_embedding, top_k=top_k)

        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        hits: list[EvidenceItem] = []
        for idx, record_id in enumerate(ids):
            metadata = metadatas[idx] if idx < len(metadatas) else {}
            doc = docs[idx] if idx < len(docs) else ""
            distance = float(distances[idx]) if idx < len(distances) else 1.0
            score = max(0.0, min(1.0, 1.0 - distance))

            hits.append(
                EvidenceItem(
                    record_id=str(record_id),
                    source=str((metadata or {}).get("source") or "unknown"),
                    summary=str(doc or ""),
                    category=str((metadata or {}).get("category") or "Unknown"),
                    patterns=self._split_pipe_values((metadata or {}).get("patterns")),
                    risk_keywords=self._split_pipe_values((metadata or {}).get("risk_keywords")),
                    score=score,
                    retrieval_mode="vector",
                    matched_keywords=[],
                )
            )

        return hits

    def _fuse_hits(self, keyword_hits: list[EvidenceItem], vector_hits: list[EvidenceItem]) -> list[EvidenceItem]:
        merged: dict[str, dict[str, EvidenceItem | float]] = {}

        for item in keyword_hits:
            merged[item.record_id] = {"item": item, "k_score": item.score, "v_score": 0.0}

        for item in vector_hits:
            if item.record_id not in merged:
                merged[item.record_id] = {"item": item, "k_score": 0.0, "v_score": item.score}
            else:
                merged[item.record_id]["v_score"] = item.score
                current = merged[item.record_id]["item"]
                if isinstance(current, EvidenceItem):
                    combined_keywords = sorted(set(current.matched_keywords + item.matched_keywords))
                    current.matched_keywords = combined_keywords

        fused: list[EvidenceItem] = []
        for value in merged.values():
            item = value["item"]
            if not isinstance(item, EvidenceItem):
                continue
            k_score = float(value["k_score"])
            v_score = float(value["v_score"])
            fused_score = 0.6 * v_score + 0.4 * k_score
            item.score = round(fused_score, 6)
            item.retrieval_mode = "hybrid"
            fused.append(item)

        fused.sort(key=lambda x: x.score, reverse=True)
        return fused

    def _build_evidence_context(self, hits: list[EvidenceItem]) -> str:
        if not hits:
            return "No retrieved evidence."

        lines: list[str] = []
        for item in hits:
            lines.append(
                " | ".join(
                    [
                        f"record_id={item.record_id}",
                        f"score={item.score:.4f}",
                        f"source={item.source}",
                        f"category={item.category}",
                        f"summary={item.summary}",
                        f"patterns={', '.join(item.patterns)}",
                        f"risk_keywords={', '.join(item.risk_keywords)}",
                        f"matched_keywords={', '.join(item.matched_keywords)}",
                    ]
                )
            )
        return "\n".join(lines)

    def _safe_detect(self, text: str, evidence_context: str) -> DetectionResult:
        try:
            return self.llm.detect(text=text, evidence_context=evidence_context)
        except Exception as exc:  # noqa: BLE001
            return DetectionResult(
                is_scam=False,
                confidence=0.0,
                reason=f"Detection fallback due to model error: {exc}",
                evidence_refs=[],
            )

    @staticmethod
    def _split_pipe_values(raw_value: object) -> list[str]:
        if raw_value is None:
            return []
        text = str(raw_value)
        return [x.strip() for x in text.split("|") if x.strip()]
