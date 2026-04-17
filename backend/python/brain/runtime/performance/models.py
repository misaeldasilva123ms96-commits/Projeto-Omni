from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from brain.runtime.learning.models import utc_now_iso


@dataclass(slots=True)
class CompressionStats:
    steps_applied: list[str]
    estimated_bytes_before: int
    estimated_bytes_after: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "steps_applied": list(self.steps_applied),
            "estimated_bytes_before": self.estimated_bytes_before,
            "estimated_bytes_after": self.estimated_bytes_after,
            "estimated_bytes_saved": max(0, self.estimated_bytes_before - self.estimated_bytes_after),
        }


@dataclass(slots=True)
class PerformanceOptimizationTrace:
    trace_id: str
    session_id: str | None
    cache_hit: bool
    cache_key_fingerprint: str
    compression_applied: list[str]
    estimated_bytes_before: int
    estimated_bytes_after: int
    redundant_dict_copies_avoided: int
    degraded: bool
    error: str
    created_at: str = field(default_factory=utc_now_iso)

    def as_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "cache_hit": self.cache_hit,
            "cache_key_fingerprint": self.cache_key_fingerprint,
            "compression_applied": list(self.compression_applied),
            "estimated_bytes_before": self.estimated_bytes_before,
            "estimated_bytes_after": self.estimated_bytes_after,
            "estimated_bytes_saved": max(0, self.estimated_bytes_before - self.estimated_bytes_after),
            "redundant_dict_copies_avoided": self.redundant_dict_copies_avoided,
            "degraded": self.degraded,
            "error": self.error[:500],
            "created_at": self.created_at,
        }


@dataclass(slots=True)
class PerformanceOptimizationResult:
    slim_swarm_context: dict[str, Any]
    trace: PerformanceOptimizationTrace
    stats: CompressionStats
