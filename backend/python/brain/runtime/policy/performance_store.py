from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brain.runtime.policy.performance_models import PerformanceBucket


def _bucket_key(*, provider: str, model: str, intent: str, strategy: str) -> str:
    return "|".join(
        [
            str(provider or "unknown")[:64],
            str(model or "unknown")[:64],
            str(intent or "unknown")[:120],
            str(strategy or "unknown")[:64],
        ]
    )


class PerformanceStore:
    """Bounded JSON aggregate for provider/tool/strategy outcomes (Phase 41.3)."""

    def __init__(self, root: Path) -> None:
        self._path = root / ".logs" / "fusion-runtime" / "policy" / "performance_state.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"version": 1, "buckets": {}}
        try:
            raw = self._path.read_text(encoding="utf-8").strip()
            data = json.loads(raw) if raw else {}
        except (OSError, json.JSONDecodeError):
            return {"version": 1, "buckets": {}}
        if not isinstance(data, dict):
            return {"version": 1, "buckets": {}}
        buckets = data.get("buckets")
        if not isinstance(buckets, dict):
            buckets = {}
        return {"version": int(data.get("version", 1)), "buckets": buckets}

    def _save(self, payload: dict[str, Any]) -> None:
        try:
            self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            return

    def _deserialize_bucket(self, raw: Any) -> PerformanceBucket:
        b = PerformanceBucket()
        if not isinstance(raw, dict):
            return b
        b.attempts = int(raw.get("attempts", 0) or 0)
        b.successes = int(raw.get("successes", 0) or 0)
        b.failures = int(raw.get("failures", 0) or 0)
        b.fallbacks = int(raw.get("fallbacks", 0) or 0)
        b.latency_sum_ms = int(raw.get("latency_sum_ms", 0) or 0)
        b.latency_samples = int(raw.get("latency_samples", 0) or 0)
        b.quality_sum = float(raw.get("quality_sum", 0.0) or 0.0)
        b.quality_samples = int(raw.get("quality_samples", 0) or 0)
        b.explicit_pos = int(raw.get("explicit_pos", 0) or 0)
        b.explicit_neg = int(raw.get("explicit_neg", 0) or 0)
        b.cost_sum = float(raw.get("cost_sum", 0.0) or 0.0)
        b.cost_samples = int(raw.get("cost_samples", 0) or 0)
        return b

    def _serialize_bucket(self, b: PerformanceBucket) -> dict[str, Any]:
        return {
            "attempts": b.attempts,
            "successes": b.successes,
            "failures": b.failures,
            "fallbacks": b.fallbacks,
            "latency_sum_ms": b.latency_sum_ms,
            "latency_samples": b.latency_samples,
            "quality_sum": b.quality_sum,
            "quality_samples": b.quality_samples,
            "explicit_pos": b.explicit_pos,
            "explicit_neg": b.explicit_neg,
            "cost_sum": b.cost_sum,
            "cost_samples": b.cost_samples,
        }

    def update_from_experience_row(self, row: dict[str, Any]) -> None:
        if not isinstance(row, dict):
            return
        data = self._load()
        buckets: dict[str, Any] = dict(data.get("buckets", {}))
        key = _bucket_key(
            provider=str(row.get("provider_selected", "") or ""),
            model=str(row.get("model_selected", "") or ""),
            intent=str(row.get("normalized_intent", "") or ""),
            strategy=str(row.get("strategy_selected", "") or ""),
        )
        b = self._deserialize_bucket(buckets.get(key))
        b.attempts += 1
        if bool(row.get("success_outcome")):
            b.successes += 1
        else:
            b.failures += 1
        if bool(row.get("fallback_used")):
            b.fallbacks += 1
        lat = row.get("latency_ms")
        if isinstance(lat, int) and lat >= 0:
            b.latency_sum_ms += lat
            b.latency_samples += 1
        q = row.get("response_quality_score")
        if isinstance(q, (int, float)):
            b.quality_sum += float(q)
            b.quality_samples += 1
        fc = str(row.get("feedback_class", "") or "")
        if fc == "positive":
            b.explicit_pos += 1
        elif fc == "negative":
            b.explicit_neg += 1
        ce = row.get("cost_estimate")
        if isinstance(ce, (int, float)):
            b.cost_sum += float(ce)
            b.cost_samples += 1

        buckets[key] = self._serialize_bucket(b)
        # cap bucket keys
        if len(buckets) > 4000:
            keys = list(buckets.keys())[-3500:]
            buckets = {k: buckets[k] for k in keys}
        self._save({"version": 1, "buckets": buckets})

    def top_buckets(self, *, limit: int = 12) -> list[dict[str, Any]]:
        data = self._load()
        buckets = data.get("buckets", {})
        if not isinstance(buckets, dict):
            return []
        ranked: list[tuple[int, str, PerformanceBucket]] = []
        for key, raw in buckets.items():
            b = self._deserialize_bucket(raw)
            ranked.append((b.attempts, str(key), b))
        ranked.sort(reverse=True)
        out: list[dict[str, Any]] = []
        for n, key, b in ranked[:limit]:
            parts = key.split("|", 3)
            prov = parts[0] if len(parts) > 0 else ""
            model = parts[1] if len(parts) > 1 else ""
            intent = parts[2] if len(parts) > 2 else ""
            strat = parts[3] if len(parts) > 3 else ""
            out.append(
                {
                    "provider": prov,
                    "model": model,
                    "intent": intent,
                    "strategy": strat,
                    "metrics": b.as_dict(),
                }
            )
        return out
