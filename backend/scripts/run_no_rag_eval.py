import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.core.logging_utils import now_iso
from backend.models.api import DetectionResult
from backend.providers.llm_client import LLMAnalyzer

DATASETS = ["job_scams", "sms"]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def calc_metrics(rows: list[dict[str, Any]]) -> dict[str, float | int]:
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


def safe_detect_no_rag(llm: LLMAnalyzer, text: str) -> DetectionResult:
    try:
        return llm.detect_no_rag(text)
    except Exception as exc:  # noqa: BLE001
        return DetectionResult(
            is_scam=False,
            confidence=0.0,
            reason=f"NoRAG fallback due to model error: {exc}",
            evidence_refs=[],
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate NoRAG LLM on first n test samples")
    parser.add_argument("--test-limit", type=int, default=50, help="First n samples per dataset")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="",
        help="Output directory. Default: backend/outputs/no_rag_eval/{run_id}",
    )
    args = parser.parse_args()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) if args.output_dir else Path("backend/outputs/no_rag_eval") / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    log_path = output_dir / "no_rag_logs.jsonl"
    log_path.write_text("", encoding="utf-8")

    llm = LLMAnalyzer()
    rows_all: list[dict[str, Any]] = []

    for dataset in DATASETS:
        test_path = Path("data") / dataset / "test.jsonl"
        rows = read_jsonl(test_path)[: args.test_limit]

        for idx, row in enumerate(rows):
            text = str(row.get("text", "")).strip()
            if not text:
                continue
            label = int(row.get("label", 0))

            detection = safe_detect_no_rag(llm, text)
            prediction = 1 if detection.is_scam else 0
            is_correct = int(prediction == label)

            log_row = {
                "time": now_iso(),
                "dataset": dataset,
                "sample_index": idx,
                "mode": "NoRAG",
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
            }
            rows_all.append(log_row)
            append_jsonl(log_path, log_row)

    summary = {
        "run_time": now_iso(),
        "test_limit_per_dataset": args.test_limit,
        "metrics": {
            "overall": calc_metrics(rows_all),
            "by_dataset": {
                dataset: calc_metrics([r for r in rows_all if r["dataset"] == dataset])
                for dataset in DATASETS
            },
        },
        "output_files": {
            "logs": str(log_path),
            "summary": str(output_dir / "summary.json"),
        },
    }

    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output_dir": str(output_dir), "metrics": summary["metrics"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
