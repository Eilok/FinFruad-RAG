import argparse
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Quick smoke evaluation for pipeline sanity check")
    parser.add_argument("--test-limit", type=int, default=2, help="Test samples per dataset, recommend 1-5")
    parser.add_argument("--train-positive-limit", type=int, default=3, help="Positive train samples per dataset, recommend 1-5")
    parser.add_argument("--keyword-top-k", type=int, default=2, help="BM25 top-k")
    parser.add_argument("--vector-top-k", type=int, default=2, help="Vector top-k")
    parser.add_argument("--collection-name", type=str, default="", help="Optional isolated collection name override")
    args = parser.parse_args()

    cmd = [
        sys.executable,
        "-m",
        "backend.scripts.run_eval",
        "--test-limit",
        str(args.test_limit),
        "--train-positive-limit",
        str(args.train_positive_limit),
        "--keyword-top-k",
        str(args.keyword_top_k),
        "--vector-top-k",
        str(args.vector_top_k),
    ]
    if args.collection_name:
        cmd.extend(["--collection-name", args.collection_name])
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
