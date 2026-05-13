import argparse
import json
from pathlib import Path

from backend.core.ingest import IngestPipeline
from backend.models.api import IngestItem


def load_items(text: str | None, input_file: str | None, source: str) -> list[IngestItem]:
    items: list[IngestItem] = []

    if text:
        items.append(IngestItem(text=text, source=source))

    if input_file:
        path = Path(input_file)
        for line in path.read_text(encoding="utf-8").splitlines():
            content = line.strip()
            if not content:
                continue
            if content.startswith("{"):
                data = json.loads(content)
                items.append(IngestItem(text=str(data.get("text", "")), source=str(data.get("source", source))))
            else:
                items.append(IngestItem(text=content, source=source))

    if not items:
        raise ValueError("No ingestible text provided. Use --text or --input-file")

    return items


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline fraud knowledge base ingestion script")
    parser.add_argument("--text", type=str, default=None, help="Single input text")
    parser.add_argument("--input-file", type=str, default=None, help="Batch input file: jsonl or plain text lines")
    parser.add_argument("--source", type=str, default="manual", help="Source tag")
    parser.add_argument("--retry-times", type=int, default=None, help="Retry attempts")
    args = parser.parse_args()

    items = load_items(args.text, args.input_file, args.source)
    pipeline = IngestPipeline()
    results, errors = pipeline.ingest_items(items=items, retry_times=args.retry_times)

    print(json.dumps({
        "total": len(items),
        "success": len(results),
        "failed": len(errors),
        "errors": errors,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
