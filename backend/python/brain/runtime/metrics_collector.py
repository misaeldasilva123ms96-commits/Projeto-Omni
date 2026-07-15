from __future__ import annotations

import math
import time
from collections import defaultdict, deque
from typing import Any


class MetricsCollector:
    def __init__(self, *, max_latency_samples: int = 2048) -> None:
        self._counts: dict[str, int] = defaultdict(int)
        self._max_latency_samples = max(32, int(max_latency_samples))
        self._latencies: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=self._max_latency_samples)
        )
        self._errors: dict[str, int] = defaultdict(int)
        self._start_time = time.monotonic()

    def increment(self, metric: str, count: int = 1) -> None:
        self._counts[metric] += count

    def record_latency(self, metric: str, duration_ms: float) -> None:
        normalized = float(duration_ms)
        if math.isfinite(normalized) and normalized >= 0:
            self._latencies[metric].append(normalized)

    def record_error(self, metric: str) -> None:
        self._errors[metric] += 1

    def snapshot(self) -> dict[str, Any]:
        def percentile(values: deque[float], fraction: float) -> float:
            if not values:
                return 0.0
            ordered = sorted(values)
            rank = max(0, math.ceil(fraction * len(ordered)) - 1)
            return ordered[rank]

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
                k: percentile(v, 0.50)
                for k, v in self._latencies.items()
            },
            "latency_p95_ms": {
                k: percentile(v, 0.95)
                for k, v in self._latencies.items()
            },
            "latency_p99_ms": {
                k: percentile(v, 0.99)
                for k, v in self._latencies.items()
            },
            "latency_sample_count": {
                k: len(v)
                for k, v in self._latencies.items()
            },
        }

    def reset(self) -> None:
        self._counts.clear()
        self._latencies.clear()
        self._errors.clear()
        self._start_time = time.monotonic()
