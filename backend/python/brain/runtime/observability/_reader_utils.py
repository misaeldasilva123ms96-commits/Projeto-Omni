from __future__ import annotations

import json
import sqlite3
import time
from collections import deque
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


def read_json_resilient(path: Path, *, retry_delay: float = 0.03) -> dict[str, Any] | list[Any] | None:
    for attempt in range(2):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except json.JSONDecodeError:
            if attempt == 0:
                time.sleep(retry_delay)
                continue
            return None
        except Exception:
            return None
    return None


def read_tail_jsonl(path: Path, *, limit: int, chunk_size: int = 8192, max_bytes: int = 262_144) -> list[dict[str, Any]]:
    if limit <= 0 or not path.exists():
        return []

    collected = bytearray()
    bytes_read = 0
    newline_target = max(8, limit * 3)

    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            position = handle.tell()
            while position > 0 and bytes_read < max_bytes:
                step = min(chunk_size, position, max_bytes - bytes_read)
                position -= step
                handle.seek(position)
                chunk = handle.read(step)
                collected = bytearray(chunk) + collected
                bytes_read += step
                if collected.count(b"\n") >= newline_target:
                    break
    except Exception:
        return []

    results: deque[dict[str, Any]] = deque(maxlen=max(1, limit))
    for raw_line in collected.decode("utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if isinstance(payload, dict):
            results.append(payload)
    return list(results)


@contextmanager
def open_sqlite_readonly(path: Path) -> Iterator[sqlite3.Connection | None]:
    if not path.exists():
        yield None
        return

    try:
        conn = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    except Exception:
        yield None
        return

    try:
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        conn.close()
