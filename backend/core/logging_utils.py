import json
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.core.settings import settings


def append_jsonl(filename: str, payload: dict[str, Any]) -> None:
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    target = log_dir / filename
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"
