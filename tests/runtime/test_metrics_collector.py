from __future__ import annotations

import math
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.metrics_collector import MetricsCollector  # noqa: E402


def test_latency_samples_are_bounded_and_publish_tail_percentiles() -> None:
    collector = MetricsCollector(max_latency_samples=32)
    for duration_ms in range(1, 101):
        collector.record_latency("node_boundary", duration_ms)

    snapshot = collector.snapshot()
    assert snapshot["latency_sample_count"]["node_boundary"] == 32
    assert snapshot["latency_p50_ms"]["node_boundary"] == 84
    assert snapshot["latency_p95_ms"]["node_boundary"] == 99
    assert snapshot["latency_p99_ms"]["node_boundary"] == 100
    assert snapshot["latency_max_ms"]["node_boundary"] == 100


def test_invalid_latency_samples_are_ignored() -> None:
    collector = MetricsCollector()
    for duration_ms in (-1, math.nan, math.inf, -math.inf):
        collector.record_latency("runtime_turn", duration_ms)

    snapshot = collector.snapshot()
    assert "runtime_turn" not in snapshot["latency_sample_count"]
