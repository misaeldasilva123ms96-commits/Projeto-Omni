"""Minimal timing and payload-size helpers for audits (Phase 30.12).

Read-only utilities; no runtime behavior hooks.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


def measure_call_ms(fn: Callable[[], T]) -> tuple[T, float]:
    """Return ``(result, elapsed_ms)`` using a monotonic clock."""
    t0 = time.perf_counter()
    out = fn()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return out, elapsed_ms


def json_payload_utf8_bytes(obj: Any, *, compact: bool = True) -> int:
    """UTF-8 byte length of JSON serialization (for payload growth audits)."""
    if compact:
        wire = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    else:
        wire = json.dumps(obj, ensure_ascii=False, indent=2)
    return len(wire.encode("utf-8"))
