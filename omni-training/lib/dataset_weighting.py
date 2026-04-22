from __future__ import annotations

from typing import Any

from dataset_quality import quality_score


def derive_weight_fields(example: dict[str, Any]) -> dict[str, Any]:
    score = float(example.get("quality_score", 0.0) or 0.0)
    if score <= 0.0:
        score = quality_score(example)
    candidate_strategies = list(example.get("candidate_strategies", []) or [])
    ambiguity_label = "high" if len(candidate_strategies) >= 2 else "low"
    task_family = str(example.get("task_family", "") or "").strip().lower()
    runtime_value = "high" if task_family in {"runtime", "governance", "coding"} else "medium"
    if ambiguity_label == "high":
        runtime_value = "high"
    execution_status = str(example.get("execution_status", "") or "").strip().lower()
    review_status = str(example.get("review_status", "") or "").strip().lower()
    review_priority = (
        "high"
        if ambiguity_label == "high" or score < 0.75 or review_status in {"draft", "weak"} or execution_status in {"fallback", "blocked", "error"}
        else "normal"
    )
    sample_weight = 0.7 + (score * 0.8)
    if ambiguity_label == "high":
        sample_weight += 0.25
    if runtime_value == "high":
        sample_weight += 0.15
    if review_status == "approved":
        sample_weight += 0.1
    if review_status in {"incorrect", "weak"}:
        sample_weight -= 0.25
    if execution_status == "success":
        sample_weight += 0.1
    elif execution_status in {"fallback", "blocked"}:
        sample_weight -= 0.15
    return {
        "quality_score": round(max(0.0, min(1.0, score)), 4),
        "sample_weight": round(max(0.25, min(2.0, sample_weight)), 4),
        "ambiguity_label": ambiguity_label,
        "runtime_value": runtime_value,
        "review_priority": review_priority,
    }


def apply_dataset_weights(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    weighted: list[dict[str, Any]] = []
    for record in records:
        enriched = dict(record)
        enriched.update(derive_weight_fields(enriched))
        weighted.append(enriched)
    return weighted
