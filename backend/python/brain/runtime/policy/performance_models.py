from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PerformanceBucket:
    attempts: int = 0
    successes: int = 0
    failures: int = 0
    fallbacks: int = 0
    latency_sum_ms: int = 0
    latency_samples: int = 0
    quality_sum: float = 0.0
    quality_samples: int = 0
    explicit_pos: int = 0
    explicit_neg: int = 0
    cost_sum: float = 0.0
    cost_samples: int = 0

    def as_dict(self) -> dict[str, Any]:
        avg_lat = (self.latency_sum_ms / self.latency_samples) if self.latency_samples else None
        avg_q = (self.quality_sum / self.quality_samples) if self.quality_samples else None
        avg_c = (self.cost_sum / self.cost_samples) if self.cost_samples else None
        return {
            "attempts": self.attempts,
            "successes": self.successes,
            "failures": self.failures,
            "fallbacks": self.fallbacks,
            "avg_latency_ms": round(avg_lat, 2) if avg_lat is not None else None,
            "avg_quality_score": round(avg_q, 4) if avg_q is not None else None,
            "explicit_positive_rate": round(self.explicit_pos / max(1, self.attempts), 4),
            "explicit_negative_rate": round(self.explicit_neg / max(1, self.attempts), 4),
            "avg_cost_estimate": round(avg_c, 6) if avg_c is not None else None,
        }
