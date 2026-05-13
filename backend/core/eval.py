import json
from pathlib import Path
from typing import Any

from backend.core.detect import DetectPipeline
from backend.core.ingest import IngestPipeline
from backend.core.logging_utils import now_iso
from backend.models.api import DetectRequest, DetectionResult, IngestItem
from backend.providers.llm_client import LLMAnalyzer
from backend.storage.chroma_store import ChromaKnowledgeStore

DATASETS = ["job_scams", "sms"]


class EvaluationRunner:
    def __init__(
        self,
        output_dir: Path,
        test_limit: int,
        keyword_top_k: int,
        vector_top_k: int,
        train_positive_limit: int = 0,
        collection_name: str | None = None,
    ) -> None:
        self.output_dir = output_dir
        self.test_limit = test_limit
        self.keyword_top_k = keyword_top_k
        self.vector_top_k = vector_top_k
        self.train_positive_limit = train_positive_limit
        self.collection_name = collection_name

        self.llm = LLMAnalyzer()
        self.detect_pipeline = DetectPipeline(collection_name=collection_name)
        self.ingest_pipeline = IngestPipeline(collection_name=collection_name)
        self.store = ChromaKnowledgeStore(collection_name=collection_name)

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.store.reset_collection()
        self.ingest_pipeline = IngestPipeline(collection_name=self.collection_name)
        self.detect_pipeline = DetectPipeline(collection_name=self.collection_name)
        self._init_live_logs()

        build_stats = self._build_offline_kb()
        no_rag_records, rag_records = self._evaluate_all()

        report = {
            "run_time": now_iso(),
            "test_limit_per_dataset": self.test_limit,
            "train_positive_limit_per_dataset": self.train_positive_limit,
            "keyword_top_k": self.keyword_top_k,
            "vector_top_k": self.vector_top_k,
            "collection_name": self.store.collection_name,
            "build": build_stats,
            "metrics": {
                "no_rag": self._metrics_report(no_rag_records),
                "rag": self._metrics_report(rag_records),
            },
        }
        (self.output_dir / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    def _init_live_logs(self) -> None:
        for filename in ("no_rag_logs.jsonl", "rag_logs.jsonl"):
            path = self.output_dir / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")

    def _build_offline_kb(self) -> dict[str, Any]:
        all_items: list[IngestItem] = []
        per_dataset_counts: dict[str, int] = {}

        for name in DATASETS:
            train_path = Path("data") / name / "train.jsonl"
            rows = self._read_jsonl(train_path)
            scam_rows = [r for r in rows if int(r.get("label", 0)) == 1]
            if self.train_positive_limit > 0:
                scam_rows = scam_rows[: self.train_positive_limit]
            per_dataset_counts[name] = len(scam_rows)
            for row in scam_rows:
                text = str(row.get("text", "")).strip()
                if text:
                    all_items.append(IngestItem(text=text, source=f"{name}:train"))

        results, errors = self.ingest_pipeline.ingest_items(all_items)
        return {
            "total_input": len(all_items),
            "success": len(results),
            "failed": len(errors),
            "errors": errors,
            "per_dataset_input": per_dataset_counts,
            "chroma_count": self.store.count(),
        }

    def _evaluate_all(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        no_rag_records: list[dict[str, Any]] = []
        rag_records: list[dict[str, Any]] = []

        for name in DATASETS:
            test_path = Path("data") / name / "test.jsonl"
            rows = self._read_jsonl(test_path)[: self.test_limit]

            for idx, row in enumerate(rows):
                text = str(row.get("text", "")).strip()
                if not text:
                    continue
                label = int(row.get("label", 0))

                no_rag = self._safe_no_rag_detect(text)
                no_rag_row = self._build_log_row(
                    dataset=name,
                    index=idx,
                    mode="NoRAG",
                    text=text,
                    label=label,
                    detection=no_rag,
                    evidence=[],
                )
                no_rag_records.append(no_rag_row)
                self._append_jsonl(self.output_dir / "no_rag_logs.jsonl", no_rag_row)

                rag_resp = self.detect_pipeline.run(
                    DetectRequest(
                        text=text,
                        keyword_top_k=self.keyword_top_k,
                        vector_top_k=self.vector_top_k,
                        return_evidence=True,
                    )
                )
                evidence = [
                    {
                        "record_id": e.record_id,
                        "source": e.source,
                        "summary": e.summary,
                        "score": e.score,
                        "mode": e.retrieval_mode,
                    }
                    for e in rag_resp.fused_hits
                ]
                rag_row = self._build_log_row(
                    dataset=name,
                    index=idx,
                    mode="RAG",
                    text=text,
                    label=label,
                    detection=rag_resp.detection,
                    evidence=evidence,
                )
                rag_records.append(rag_row)
                self._append_jsonl(self.output_dir / "rag_logs.jsonl", rag_row)

        return no_rag_records, rag_records

    def _safe_no_rag_detect(self, text: str) -> DetectionResult:
        try:
            return self.llm.detect_no_rag(text)
        except Exception as exc:  # noqa: BLE001
            return DetectionResult(
                is_scam=False,
                confidence=0.0,
                reason=f"NoRAG fallback due to model error: {exc}",
                evidence_refs=[],
            )

    @staticmethod
    def _build_log_row(
        dataset: str,
        index: int,
        mode: str,
        text: str,
        label: int,
        detection: DetectionResult,
        evidence: list[dict[str, Any]],
    ) -> dict[str, Any]:
        prediction = 1 if detection.is_scam else 0
        is_correct = int(prediction == label)
        return {
            "time": now_iso(),
            "dataset": dataset,
            "sample_index": index,
            "mode": mode,
            "text": text,
            "label": label,
            "model_answer": {
                "is_scam": detection.is_scam,
                "confidence": detection.confidence,
                "reason": detection.reason,
                "evidence_refs": detection.evidence_refs,
            },
            "prediction": prediction,
            "is_correct": is_correct,
            "retrieved_evidence": evidence,
        }

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
        return rows

    @staticmethod
    def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _metrics_report(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        by_dataset: dict[str, dict[str, float]] = {}
        for name in DATASETS:
            subset = [r for r in rows if r["dataset"] == name]
            by_dataset[name] = self._calc_metrics(subset)

        return {
            "overall": self._calc_metrics(rows),
            "by_dataset": by_dataset,
        }

    @staticmethod
    def _calc_metrics(rows: list[dict[str, Any]]) -> dict[str, float | int]:
        total = len(rows)
        if total == 0:
            return {
                "count": 0,
                "accuracy": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "f1": 0.0,
                "tp": 0,
                "tn": 0,
                "fp": 0,
                "fn": 0,
            }

        tp = sum(1 for r in rows if r["label"] == 1 and r["prediction"] == 1)
        tn = sum(1 for r in rows if r["label"] == 0 and r["prediction"] == 0)
        fp = sum(1 for r in rows if r["label"] == 0 and r["prediction"] == 1)
        fn = sum(1 for r in rows if r["label"] == 1 and r["prediction"] == 0)

        accuracy = (tp + tn) / total
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

        return {
            "count": total,
            "accuracy": round(accuracy, 6),
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
            "tp": tp,
            "tn": tn,
            "fp": fp,
            "fn": fn,
        }
