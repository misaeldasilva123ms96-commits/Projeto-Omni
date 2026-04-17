from __future__ import annotations

import hashlib
import json
from typing import Any

from .cache import BoundedLRUCache
from .compression import build_slim_swarm_context
from .models import CompressionStats, PerformanceOptimizationResult, PerformanceOptimizationTrace


def _fingerprint_key(
    *,
    session_id: str | None,
    message: str,
    memory_intelligence: dict[str, Any],
    reasoning_handoff: dict[str, Any],
    planning_payload: dict[str, Any],
) -> str:
    ep = planning_payload.get("execution_plan") if isinstance(planning_payload, dict) else {}
    plan_id = str(ep.get("plan_id", "")) if isinstance(ep, dict) else ""
    basis = {
        "session": session_id or "",
        "message": (message or "")[:2400],
        "ctx": str(memory_intelligence.get("context_id", "")),
        "intent": str(reasoning_handoff.get("intent", "")),
        "plan_id": plan_id,
    }
    raw = json.dumps(basis, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class PerformanceEngine:
    """Phase 36 — bounded caching, structured compression, and measurable swarm boundary shaping."""

    def __init__(self, *, max_cache_entries: int = 48) -> None:
        self._slim_cache: BoundedLRUCache = BoundedLRUCache(max_entries=max_cache_entries)

    def optimize_swarm_boundary(
        self,
        *,
        session_id: str | None,
        message: str,
        budget_dict: dict[str, Any],
        retrieval_dict: dict[str, Any],
        structured_memory: Any,
        memory_intelligence: dict[str, Any],
        reasoning_handoff: dict[str, Any],
        planning_payload: dict[str, Any],
    ) -> PerformanceOptimizationResult:
        trace_id = f"perf36-{_fingerprint_key(session_id=session_id, message=message, memory_intelligence=memory_intelligence, reasoning_handoff=reasoning_handoff, planning_payload=planning_payload)[:18]}"
        fp = _fingerprint_key(
            session_id=session_id,
            message=message,
            memory_intelligence=memory_intelligence,
            reasoning_handoff=reasoning_handoff,
            planning_payload=planning_payload,
        )
        degraded = False
        err = ""
        redundant_avoided = 1
        try:
            cached = self._slim_cache.get(fp)
            if cached is not None:
                applied = ["cache_hit_slim_swarm_context"]
                trace = PerformanceOptimizationTrace(
                    trace_id=trace_id,
                    session_id=session_id,
                    cache_hit=True,
                    cache_key_fingerprint=fp[:16],
                    compression_applied=applied,
                    estimated_bytes_before=int(cached.get("__p36_before", 0) or 0),
                    estimated_bytes_after=int(cached.get("__p36_after", 0) or 0),
                    redundant_dict_copies_avoided=redundant_avoided + 1,
                    degraded=False,
                    error="",
                )
                slim = {k: v for k, v in cached.items() if not str(k).startswith("__p36_")}
                stats = CompressionStats(
                    steps_applied=list(applied),
                    estimated_bytes_before=trace.estimated_bytes_before,
                    estimated_bytes_after=trace.estimated_bytes_after,
                )
                return PerformanceOptimizationResult(slim_swarm_context=slim, trace=trace, stats=stats)

            slim, stats = build_slim_swarm_context(
                budget_dict=budget_dict,
                retrieval_dict=retrieval_dict,
                structured_memory=structured_memory,
                memory_intelligence=memory_intelligence,
                reasoning_handoff=reasoning_handoff,
                planning_payload=planning_payload,
            )
            cache_entry = dict(slim)
            cache_entry["__p36_before"] = stats.estimated_bytes_before
            cache_entry["__p36_after"] = stats.estimated_bytes_after
            self._slim_cache.put(fp, cache_entry)

            trace = PerformanceOptimizationTrace(
                trace_id=trace_id,
                session_id=session_id,
                cache_hit=False,
                cache_key_fingerprint=fp[:16],
                compression_applied=list(stats.steps_applied),
                estimated_bytes_before=stats.estimated_bytes_before,
                estimated_bytes_after=stats.estimated_bytes_after,
                redundant_dict_copies_avoided=redundant_avoided,
                degraded=False,
                error="",
            )
            return PerformanceOptimizationResult(slim_swarm_context=slim, trace=trace, stats=stats)
        except Exception as exc:
            degraded = True
            err = str(exc)
            slim_fallback: dict[str, Any] = {
                "context_budget": dict(budget_dict),
                "retrieval_plan": dict(retrieval_dict),
                "structured_memory": structured_memory,
                "reasoning_handoff": dict(reasoning_handoff),
                "memory_intelligence": dict(memory_intelligence),
                "execution_plan": dict(planning_payload.get("execution_plan", {}) or {})
                if isinstance(planning_payload, dict)
                else {},
                "planning_trace": dict(planning_payload.get("planning_trace", {}) or {})
                if isinstance(planning_payload, dict)
                else {},
                "phase36_boundary": "fallback_uncompressed",
            }
            trace = PerformanceOptimizationTrace(
                trace_id=trace_id,
                session_id=session_id,
                cache_hit=False,
                cache_key_fingerprint=fp[:16],
                compression_applied=[],
                estimated_bytes_before=0,
                estimated_bytes_after=0,
                redundant_dict_copies_avoided=0,
                degraded=degraded,
                error=err,
            )
            stats = CompressionStats(steps_applied=[], estimated_bytes_before=0, estimated_bytes_after=0)
            return PerformanceOptimizationResult(slim_swarm_context=slim_fallback, trace=trace, stats=stats)
