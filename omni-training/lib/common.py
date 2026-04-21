from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        records.append(json.loads(stripped))
    return records


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    ensure_parent(path)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def append_markdown_report(path: Path, title: str, stats: dict[str, Any]) -> None:
    ensure_parent(path)
    lines = [f"## {title}", "", f"- generated_at: `{utc_now_iso()}`"]
    for key, value in stats.items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def slugify(value: str) -> str:
    lowered = re.sub(r"[^a-zA-Z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return lowered or "dataset"


def detect_language(text: str) -> str:
    lowered = str(text or "").lower()
    if not lowered.strip():
        return "unknown"
    pt_signals = (" você ", " nao ", " não ", " como ", " explique ", " plano ", " arquitetura ")
    en_signals = (" the ", " explain ", " plan ", " architecture ", " debug ", " output ")
    padded = f" {lowered} "
    if any(sig in padded for sig in pt_signals):
        return "pt"
    if any(sig in padded for sig in en_signals):
        return "en"
    return "unknown"


def non_empty_text(value: Any) -> str:
    text = str(value or "").strip()
    return text
