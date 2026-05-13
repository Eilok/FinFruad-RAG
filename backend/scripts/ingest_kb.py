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
        raise ValueError("未提供可导入文本，请使用 --text 或 --input-file")

    return items


def main() -> None:
    parser = argparse.ArgumentParser(description="离线诈骗知识库构建脚本")
    parser.add_argument("--text", type=str, default=None, help="单条文本")
    parser.add_argument("--input-file", type=str, default=None, help="批量输入文件，支持jsonl或纯文本")
    parser.add_argument("--source", type=str, default="manual", help="数据来源标识")
    parser.add_argument("--retry-times", type=int, default=None, help="重试次数")
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
