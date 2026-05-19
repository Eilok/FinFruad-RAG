import argparse
import json
from datetime import datetime
from pathlib import Path

from backend.core.eval import EvaluationRunner
from backend.core.settings import settings


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG-only automated evaluation")
    parser.add_argument("--test-limit", type=int, default=500, help="Number of test samples per dataset")
    parser.add_argument("--train-positive-limit", type=int, default=0, help="Positive train samples per dataset for KB build; 0 means full")
    parser.add_argument("--keyword-top-k", type=int, default=3, help="BM25 retrieval top-k")
    parser.add_argument("--vector-top-k", type=int, default=3, help="Vector retrieval top-k")
    parser.add_argument("--collection-name", type=str, default="", help="Evaluation collection name. Empty means auto-generated isolated collection.")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="",
        help="Output directory. Default: backend/outputs/rag_eval/{run_id}",
    )
    args = parser.parse_args()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) if args.output_dir else Path("backend/outputs/rag_eval") / run_id
    collection_name = args.collection_name.strip() if args.collection_name else f"{settings.eval_collection_prefix}_{run_id}"

    runner = EvaluationRunner(
        output_dir=output_dir,
        test_limit=args.test_limit,
        keyword_top_k=args.keyword_top_k,
        vector_top_k=args.vector_top_k,
        train_positive_limit=args.train_positive_limit,
        collection_name=collection_name,
        include_no_rag=False,
    )
    report = runner.run()
    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "collection_name": collection_name,
                "metrics": report["metrics"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
