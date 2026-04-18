from __future__ import annotations

import copy
from typing import Any

from .metrics import estimate_json_bytes
from .models import CompressionStats


def _trunc(s: str, max_len: int) -> str:
    t = str(s or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 3] + "..."


def compress_memory_intelligence(payload: dict[str, Any], *, max_summary: int = 900) -> dict[str, Any]:
    scoring = payload.get("scoring")
    slim_scoring: dict[str, Any] = {}
    if isinstance(scoring, dict):
        for k in ("max_score", "min_score", "mean_score", "selected_count"):
            if k in scoring:
                slim_scoring[k] = scoring[k]
    return {
        "context_id": str(payload.get("context_id", "")),
        "selected_count": int(payload.get("selected_count", 0) or 0),
        "total_candidates": int(payload.get("total_candidates", 0) or 0),
        "sources_used": list(payload.get("sources_used", []) or [])[:12],
        "context_summary": _trunc(str(payload.get("context_summary", "")), max_summary),
        "scoring": slim_scoring,
        "compression": "phase36_memory_intel_v1",
    }


def compress_reasoning_handoff(handoff: dict[str, Any], *, max_summary: int = 600, max_steps: int = 24) -> dict[str, Any]:
    steps = handoff.get("plan_steps", [])
    if not isinstance(steps, list):
        steps = []
    trimmed = [str(s).strip()[:120] for s in steps[:max_steps] if str(s).strip()]
    caps = handoff.get("suggested_capabilities", [])
    if not isinstance(caps, list):
        caps = []
    return {
        "proceed": bool(handoff.get("proceed", False)),
        "mode": str(handoff.get("mode", "")),
        "intent": str(handoff.get("intent", "")),
        "task_type": str(handoff.get("task_type", "")),
        "execution_strategy": str(handoff.get("execution_strategy", "")),
        "reasoning_summary": _trunc(str(handoff.get("reasoning_summary", "")), max_summary),
        "plan_steps": trimmed,
        "suggested_capabilities": [str(c).strip() for c in caps[:16] if str(c).strip()],
        "validation": dict(handoff.get("validation", {}) or {}),
        "governance": dict(handoff.get("governance", {}) or {}),
        "compression": "phase36_reasoning_handoff_v1",
    }


def compress_execution_plan(plan: dict[str, Any], *, max_steps: int = 28, desc_len: int = 180) -> dict[str, Any]:
    steps_in = plan.get("steps", [])
    out_steps: list[dict[str, Any]] = []
    if isinstance(steps_in, list):
        for step in steps_in[:max_steps]:
            if not isinstance(step, dict):
                continue
            out_steps.append(
                {
                    "step_id": str(step.get("step_id", "")),
                    "step_type": str(step.get("step_type", "")),
                    "summary": _trunc(str(step.get("summary", "")), 200),
                    "description": _trunc(str(step.get("description", "")), desc_len),
                    "depends_on": list(step.get("depends_on", []) or [])[:12],
                    "requires_validation": bool(step.get("requires_validation", False)),
                }
            )
    out: dict[str, Any] = {
        "plan_id": str(plan.get("plan_id", "")),
        "execution_ready": bool(plan.get("execution_ready", False)),
        "planning_summary": _trunc(str(plan.get("planning_summary", "")), 400),
        "steps": out_steps,
        "checkpoints": [
            dict(c) for c in (plan.get("checkpoints", []) or [])[:16] if isinstance(c, dict)
        ],
        "fallbacks": [
            dict(f) for f in (plan.get("fallbacks", []) or [])[:8] if isinstance(f, dict)
        ],
        "linked_reasoning": dict(plan.get("linked_reasoning", {}) or {}),
        "compression": "phase36_execution_plan_v1",
    }
    subs = plan.get("subtasks")
    if isinstance(subs, list) and subs:
        slim_sub: list[dict[str, Any]] = []
        for s in subs[:8]:
            if not isinstance(s, dict):
                continue
            slim_sub.append(
                {
                    "id": _trunc(str(s.get("id", "")), 48),
                    "type": str(s.get("type", "")),
                    "parent_step_id": str(s.get("parent_step_id", "")),
                    "depth": int(s.get("depth", 0) or 0),
                    "description": _trunc(str(s.get("description", "")), 140),
                    "depends_on": [str(d)[:40] for d in (s.get("depends_on", []) or [])[:6]],
                }
            )
        out["subtasks"] = slim_sub
        out["subtask_compression"] = "phase38_bounded_v1"
    return out


def compress_planning_trace(pt: dict[str, Any]) -> dict[str, Any]:
    return {
        "trace_id": str(pt.get("trace_id", "")),
        "plan_id": str(pt.get("plan_id", "")),
        "step_count": int(pt.get("step_count", 0) or 0),
        "dependency_edge_count": int(pt.get("dependency_edge_count", 0) or 0),
        "checkpoint_count": int(pt.get("checkpoint_count", 0) or 0),
        "fallback_count": int(pt.get("fallback_count", 0) or 0),
        "execution_ready": bool(pt.get("execution_ready", False)),
        "degraded": bool(pt.get("degraded", False)),
        "fallback_branch_defined": bool(pt.get("fallback_branch_defined", False)),
        "outcome_class": str(pt.get("outcome_class", "")),
        "error": _trunc(str(pt.get("error", "")), 240),
        "compression": "phase36_planning_trace_v1",
    }


def compress_structured_memory(obj: Any, *, max_items: int = 14, str_len: int = 400, depth: int = 0) -> Any:
    if depth > 4:
        return {"note": "depth_truncated"}
    if isinstance(obj, list):
        out: list[Any] = []
        for item in obj[:max_items]:
            if isinstance(item, dict):
                slim = {
                    k: _trunc(str(v), str_len) if isinstance(v, str) else compress_structured_memory(v, depth=depth + 1)
                    for k, v in list(item.items())[:10]
                }
                out.append(slim)
            else:
                out.append(compress_structured_memory(item, max_items=max_items, str_len=str_len, depth=depth + 1))
        return {"items": out, "truncated": len(obj) > max_items, "compression": "phase36_structured_memory_v1"}
    if isinstance(obj, dict):
        return {
            str(k)[:80]: compress_structured_memory(v, max_items=max_items, str_len=str_len, depth=depth + 1)
            for k, v in list(obj.items())[:20]
        }
    if isinstance(obj, str):
        return _trunc(obj, str_len)
    return copy.deepcopy(obj)


def build_slim_swarm_context(
    *,
    budget_dict: dict[str, Any],
    retrieval_dict: dict[str, Any],
    structured_memory: Any,
    memory_intelligence: dict[str, Any],
    reasoning_handoff: dict[str, Any],
    planning_payload: dict[str, Any],
) -> tuple[dict[str, Any], CompressionStats]:
    steps: list[str] = []
    mem_slim = compress_memory_intelligence(memory_intelligence)
    steps.append("memory_intelligence")
    rh_slim = compress_reasoning_handoff(reasoning_handoff)
    steps.append("reasoning_handoff")
    sm_slim = compress_structured_memory(structured_memory)
    steps.append("structured_memory")

    ep_raw = planning_payload.get("execution_plan") if isinstance(planning_payload, dict) else {}
    pt_raw = planning_payload.get("planning_trace") if isinstance(planning_payload, dict) else {}
    ep_slim = compress_execution_plan(dict(ep_raw)) if isinstance(ep_raw, dict) else {}
    pt_slim = compress_planning_trace(dict(pt_raw)) if isinstance(pt_raw, dict) else {}
    if ep_slim:
        steps.append("execution_plan")
    if pt_slim:
        steps.append("planning_trace")

    slim: dict[str, Any] = {
        "context_budget": dict(budget_dict),
        "retrieval_plan": dict(retrieval_dict),
        "structured_memory": sm_slim,
        "reasoning_handoff": rh_slim,
        "memory_intelligence": mem_slim,
        "execution_plan": ep_slim,
        "planning_trace": pt_slim,
        "phase36_boundary": "slim_swarm_context_v1",
    }

    full_reference = {
        "context_budget": budget_dict,
        "retrieval_plan": retrieval_dict,
        "structured_memory": structured_memory,
        "reasoning_handoff": reasoning_handoff,
        "memory_intelligence": memory_intelligence,
        "execution_plan": ep_raw,
        "planning_trace": pt_raw,
    }
    before = estimate_json_bytes(full_reference)
    after = estimate_json_bytes(slim)
    stats = CompressionStats(
        steps_applied=steps,
        estimated_bytes_before=before,
        estimated_bytes_after=after,
    )
    return slim, stats
