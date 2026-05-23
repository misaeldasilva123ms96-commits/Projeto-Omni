from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def _normalized_source(record: dict[str, Any]) -> str:
    return str(record.get("source", "") or (record.get("metadata") or {}).get("source_name", "unknown")).strip() or "unknown"


def _language(record: dict[str, Any]) -> str:
    return str(record.get("language", "unknown") or "unknown").strip()


def _task_family(record: dict[str, Any]) -> str:
    return str(record.get("task_family", "general") or "general").strip()


def _priority_score(record: dict[str, Any]) -> float:
    quality = float(record.get("quality_score", 0.0) or 0.0)
    sample_weight = float(record.get("sample_weight", 1.0) or 1.0)
    runtime_value = str(record.get("runtime_value", "") or "").strip().lower()
    language = _language(record)
    score = quality + (sample_weight * 0.25)
    if runtime_value == "high":
        score += 0.3
    if language in {"pt", "pt-BR", "pt-br"}:
        score += 0.2
    if str(record.get("review_status", "") or "").strip().lower() == "approved":
        score += 0.15
    if str(record.get("source", "") or "").strip() in {"internal_curated", "runtime_harvest"}:
        score += 0.15
    return round(score, 4)


def mix_dataset_records(
    records: list[dict[str, Any]],
    *,
    max_records: int = 1000,
    language_quota: dict[str, int] | None = None,
    task_family_quota: dict[str, int] | None = None,
    source_quota: dict[str, int] | None = None,
    source_minimums: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    language_quota = dict(language_quota or {})
    task_family_quota = dict(task_family_quota or {})
    source_quota = dict(source_quota or {})
    source_minimums = dict(source_minimums or {})
    ranked = sorted(records, key=_priority_score, reverse=True)
    selected: list[dict[str, Any]] = []
    language_counts: Counter[str] = Counter()
    task_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    selected_ids: set[str] = set()
    for source_name, minimum in source_minimums.items():
        if minimum <= 0:
            continue
        source_ranked = [record for record in ranked if _normalized_source(record) == source_name]
        for record in source_ranked[:minimum]:
            rid = str(record.get("id", "") or "")
            if rid in selected_ids:
                continue
            selected.append(record)
            selected_ids.add(rid)
            source_counts[source_name] += 1
            language_counts[_language(record)] += 1
            task_counts[_task_family(record)] += 1
    for record in ranked:
        if len(selected) >= max(1, max_records):
            break
        rid = str(record.get("id", "") or "")
        if rid in selected_ids:
            continue
        source_name = _normalized_source(record)
        language = _language(record)
        task_family = _task_family(record)
        if source_name in source_quota and source_counts[source_name] >= source_quota[source_name]:
            continue
        if language in language_quota and language_counts[language] >= language_quota[language]:
            continue
        if task_family in task_family_quota and task_counts[task_family] >= task_family_quota[task_family]:
            continue
        selected.append(record)
        selected_ids.add(rid)
        source_counts[source_name] += 1
        language_counts[language] += 1
        task_counts[task_family] += 1
    return selected


def build_mix_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    source_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    task_counts: Counter[str] = Counter()
    strategy_counts: Counter[str] = Counter()
    weights: list[float] = []
    for record in records:
        source_counts[_normalized_source(record)] += 1
        language_counts[_language(record)] += 1
        task_counts[_task_family(record)] += 1
        strategy = str(
            record.get("selected_strategy")
            or (record.get("runtime_hints") or {}).get("strategy")
            or ""
        ).strip()
        if strategy:
            strategy_counts[strategy] += 1
        weights.append(float(record.get("sample_weight", 1.0) or 1.0))
    return {
        "total_records": len(records),
        "by_source": dict(source_counts),
        "by_language": dict(language_counts),
        "by_task_family": dict(task_counts),
        "by_strategy": dict(strategy_counts),
        "average_sample_weight": round(sum(weights) / max(1, len(weights)), 4),
        "average_quality_score": round(
            sum(float(record.get("quality_score", 0.0) or 0.0) for record in records) / max(1, len(records)),
            4,
        ),
    }
