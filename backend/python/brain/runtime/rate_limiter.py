from __future__ import annotations

import time
from collections import defaultdict
from typing import Any


class RateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self.window_seconds
        bucket = self._buckets[key]
        bucket[:] = [t for t in bucket if t > window_start]
        if len(bucket) >= self.max_requests:
            return False
        bucket.append(now)
        return True

    def remaining(self, key: str) -> int:
        now = time.monotonic()
        window_start = now - self.window_seconds
        bucket = self._buckets[key]
        bucket[:] = [t for t in bucket if t > window_start]
        return max(0, self.max_requests - len(bucket))

    def reset(self, key: str) -> None:
        self._buckets.pop(key, None)

    def as_dict(self) -> dict[str, Any]:
        return {
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "active_keys": len(self._buckets),
        }
