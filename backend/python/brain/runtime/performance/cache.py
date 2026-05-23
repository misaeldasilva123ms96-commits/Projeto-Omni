from __future__ import annotations

from collections import OrderedDict
from typing import Any


class BoundedLRUCache:
    """In-process LRU with explicit max size (Phase 36 — string keys only, no cross-process persistence)."""

    def __init__(self, *, max_entries: int) -> None:
        self._max = max(1, int(max_entries or 1))
        self._data: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def get(self, key: str) -> dict[str, Any] | None:
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key: str, value: dict[str, Any]) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        while len(self._data) > self._max:
            self._data.popitem(last=False)

    def clear(self) -> None:
        self._data.clear()
