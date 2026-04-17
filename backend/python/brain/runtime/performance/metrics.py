from __future__ import annotations

import json
from typing import Any


def estimate_json_bytes(payload: Any) -> int:
    """Bounded size estimate for observability (UTF-8 length of canonical JSON)."""
    try:
        raw = json.dumps(payload, ensure_ascii=False, default=str, separators=(",", ":"))
    except (TypeError, ValueError):
        return 0
    return len(raw.encode("utf-8"))
