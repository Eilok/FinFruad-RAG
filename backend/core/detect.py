import re

from backend.core.bm25 import BM25Index, tokenize_for_bm25
from backend.core.settings import settings
from backend.models.api import DetectRequest, DetectResponse, DetectionResult, EvidenceItem
from backend.providers.embedding_client import EmbeddingClient
from backend.providers.llm_client import LLMAnalyzer
from backend.storage.chroma_store import ChromaKnowledgeStore


class DetectPipeline:
    def __init__(self, collection_name: str | None = None) -> None:
        self.embedder = EmbeddingClient()
        self.llm = LLMAnalyzer()
        self.store = ChromaKnowledgeStore(collection_name=collection_name)

    def run(self, req: DetectRequest) -> DetectResponse:
        text = self._normalize_text(req.text)
        keyword_top_k = req.keyword_top_k or settings.default_keyword_top_k
        vector_top_k = req.vector_top_k or settings.default_vector_top_k

        query_tokens = tokenize_for_bm25(text)
        keyword_hits = self._bm25_retrieval(query_tokens, top_k=keyword_top_k)
        vector_hits = self._vector_retrieval(text, top_k=vector_top_k)
        fused_hits = self._fuse_hits(keyword_hits, vector_hits)

        evidence_context, ref_to_record_id = self._build_evidence_context(fused_hits)
        detection = self._safe_detect(text=text, evidence_context=evidence_context)
        detection.evidence_refs = [
            ref_to_record_id.get(ref, ref) for ref in detection.evidence_refs
        ]

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

    def _bm25_retrieval(self, query_tokens: list[str], top_k: int) -> list[EvidenceItem]:
        dataset = self.store.fetch_all()
        ids = dataset.get("ids") or []
        docs = dataset.get("documents") or []
        metadatas = dataset.get("metadatas") or []

        corpus_texts: list[str] = []
        evidence_rows: list[tuple[str, str, dict]] = []

        for idx, record_id in enumerate(ids):
            metadata = metadatas[idx] if idx < len(metadatas) else {}
            summary = str(docs[idx] if idx < len(docs) else "")
            patterns = self._split_pipe_values((metadata or {}).get("patterns"))
            risk_keywords = self._split_pipe_values((metadata or {}).get("risk_keywords"))

            joined = " ".join([summary, " ".join(patterns), " ".join(risk_keywords)]).strip()
            corpus_texts.append(joined)
            evidence_rows.append((str(record_id), summary, metadata or {}))

        tokenized_corpus = [tokenize_for_bm25(doc) for doc in corpus_texts]
        bm25 = BM25Index(tokenized_corpus)

        raw_scores = [bm25.score(query_tokens, i) for i in range(len(evidence_rows))]
        max_score = max(raw_scores) if raw_scores else 0.0

        ranked_indices = sorted(range(len(raw_scores)), key=lambda i: raw_scores[i], reverse=True)
        hits: list[EvidenceItem] = []
        for idx in ranked_indices:
            score = raw_scores[idx]
            if score <= 0:
                continue
            record_id, summary, metadata = evidence_rows[idx]
            risk_keywords = self._split_pipe_values(metadata.get("risk_keywords"))
            matched = [k for k in risk_keywords if any(token in k.lower() or k.lower() in token for token in query_tokens)]
            normalized_score = score / max_score if max_score > 0 else 0.0

            hits.append(
                EvidenceItem(
                    record_id=record_id,
                    source=str(metadata.get("source") or "unknown"),
                    summary=summary,
                    category=str(metadata.get("category") or "Unknown"),
                    patterns=self._split_pipe_values(metadata.get("patterns")),
                    risk_keywords=risk_keywords,
                    score=round(normalized_score, 6),
                    retrieval_mode="bm25",
                    matched_keywords=sorted(set(matched)),
                )
            )
            if len(hits) >= top_k:
                break

        return hits

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

    def _build_evidence_context(self, hits: list[EvidenceItem]) -> tuple[str, dict[str, str]]:
        if not hits:
            return "No retrieved evidence.", {}

        lines: list[str] = []
        ref_map: dict[str, str] = {}
        for idx, item in enumerate(hits, start=1):
            short_ref = str(idx)
            ref_map[short_ref] = item.record_id
            lines.append(
                " | ".join(
                    [
                        f"ref_id={short_ref}",
                        f"score={item.score:.4f}",
                        f"category={item.category}",
                        f"summary={item.summary}",
                    ]
                )
            )
        return "\n".join(lines), ref_map

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
