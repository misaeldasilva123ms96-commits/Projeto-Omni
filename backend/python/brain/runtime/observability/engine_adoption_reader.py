from __future__ import annotations

from pathlib import Path
from typing import Any

from brain.runtime.engine_adoption_store import KNOWN_FALLBACK_REASONS, default_engine_adoption_payload

from ._reader_utils import read_json_resilient


def read_engine_adoption(root: Path) -> dict[str, Any]:
    path = root / ".logs" / "fusion-runtime" / "engine_adoption.json"
    payload = read_json_resilient(path)
    normalized = _normalize_engine_adoption(payload)
    counters = normalized["engine_counters"]
    packaged_count = counters["packaged_upstream"]
    fallback_count = counters["authority_fallback"]
    total_requests = packaged_count + fallback_count
    adoption_rate = float(packaged_count / total_requests) if total_requests > 0 else 0.0
    fallback_breakdown = dict(counters["fallback_by_reason"])
    packaged_import_failed = int(fallback_breakdown.get("packaged_import_failed", 0))

    return {
        "scope": normalized["scope"],
        "session_id": normalized["session_id"],
        "packaged_upstream_count": packaged_count,
        "authority_fallback_count": fallback_count,
        "fallback_breakdown": fallback_breakdown,
        "adoption_rate": adoption_rate,
        "promotion_ready": (
            adoption_rate >= 0.80
            and packaged_import_failed == 0
            and total_requests >= 10
        ),
    }


def _normalize_engine_adoption(payload: object) -> dict[str, Any]:
    base = default_engine_adoption_payload()
    if not isinstance(payload, dict):
        return base

    base["scope"] = "session"
    base["session_id"] = str(payload.get("session_id", "")).strip()
    counters = payload.get("engine_counters")
    if not isinstance(counters, dict):
        return base

    base["engine_counters"]["packaged_upstream"] = int(counters.get("packaged_upstream", 0) or 0)
    base["engine_counters"]["authority_fallback"] = int(counters.get("authority_fallback", 0) or 0)
    fallback_by_reason = counters.get("fallback_by_reason")
    if isinstance(fallback_by_reason, dict):
        for reason in KNOWN_FALLBACK_REASONS:
            base["engine_counters"]["fallback_by_reason"][reason] = int(fallback_by_reason.get(reason, 0) or 0)
    return base
