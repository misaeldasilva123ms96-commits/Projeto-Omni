from __future__ import annotations

import hashlib
import time
from typing import Any


class SemanticCache:
    def __init__(self, max_entries: int = 1024, ttl_seconds: int = 300) -> None:
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, dict[str, Any]] = {}

    def _key(self, message: str, context: dict[str, Any] | None = None) -> str:
        raw = message.strip().lower()
        if context:
            raw += "|" + str(sorted(context.items()))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, message: str, context: dict[str, Any] | None = None) -> str | None:
        key = self._key(message, context)
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() - entry["ts"] > self.ttl_seconds:
            del self._store[key]
            return None
        return entry["response"]

    def set(self, message: str, response: str, context: dict[str, Any] | None = None) -> None:
        key = self._key(message, context)
        if len(self._store) >= self.max_entries:
            oldest = min(self._store.keys(), key=lambda k: self._store[k]["ts"])
            del self._store[oldest]
        self._store[key] = {
            "response": response,
            "ts": time.monotonic(),
        }

    def clear(self) -> None:
        self._store.clear()

    def size(self) -> int:
        return len(self._store)

    def as_dict(self) -> dict[str, Any]:
        return {
            "max_entries": self.max_entries,
            "ttl_seconds": self.ttl_seconds,
            "current_entries": len(self._store),
        }
