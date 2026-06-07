from __future__ import annotations

import time
from collections import defaultdict
from typing import Any


class MetricsCollector:
    def __init__(self) -> None:
        self._counts: dict[str, int] = defaultdict(int)
        self._latencies: dict[str, list[float]] = defaultdict(list)
        self._errors: dict[str, int] = defaultdict(int)
        self._start_time = time.monotonic()

    def increment(self, metric: str, count: int = 1) -> None:
        self._counts[metric] += count

    def record_latency(self, metric: str, duration_ms: float) -> None:
        self._latencies[metric].append(duration_ms)

    def record_error(self, metric: str) -> None:
        self._errors[metric] += 1

    def snapshot(self) -> dict[str, Any]:
        uptime_seconds = int(time.monotonic() - self._start_time)
        return {
            "uptime_seconds": uptime_seconds,
            "counts": dict(self._counts),
            "errors": dict(self._errors),
            "latency_avg_ms": {
                k: (sum(v) / len(v)) if v else 0.0
                for k, v in self._latencies.items()
            },
            "latency_max_ms": {
                k: max(v) if v else 0.0
                for k, v in self._latencies.items()
            },
            "latency_p50_ms": {
                k: sorted(v)[len(v) // 2] if v else 0.0
                for k, v in self._latencies.items()
            },
        }

    def reset(self) -> None:
        self._counts.clear()
        self._latencies.clear()
        self._errors.clear()
        self._start_time = time.monotonic()
