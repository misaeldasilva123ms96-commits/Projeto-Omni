from __future__ import annotations

from typing import Any

from dataset_pipeline import DEFAULT_SYSTEM_PROMPT, build_prompt_text


def runtime_hints_from_oil(oil_payload: dict[str, Any], task_family: str) -> dict[str, Any]:
    intent = str(oil_payload.get("user_intent", "")).strip()
    strategy = "DIRECT_RESPONSE"
    requires_tools = False
    requires_node_runtime = False
    if task_family in {"coding", "runtime", "governance"} or intent in {"analyze", "plan"}:
        strategy = "MULTI_STEP_REASONING"
    if task_family in {"coding", "runtime"}:
        requires_tools = True
    if any(term in " ".join([intent, task_family]).lower() for term in ("node", "runtime", "provider")):
        requires_node_runtime = task_family == "runtime"
    if task_family == "governance":
        strategy = "SAFE_FALLBACK" if oil_payload.get("urgency") == "high" else "MULTI_STEP_REASONING"
    return {
        "strategy": strategy if not requires_tools else ("TOOL_ASSISTED" if strategy == "DIRECT_RESPONSE" else strategy),
        "requires_tools": requires_tools,
        "requires_node_runtime": requires_node_runtime,
        "fallback_allowed": True,
    }


def _common_fields(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "quality_score": record.get("quality_score"),
        "sample_weight": record.get("sample_weight"),
        "ambiguity_label": record.get("ambiguity_label"),
        "runtime_value": record.get("runtime_value"),
        "review_priority": record.get("review_priority"),
        "selected_strategy": record.get("selected_strategy") or (record.get("runtime_hints") or {}).get("strategy"),
        "executor_used": record.get("executor_used"),
        "execution_status": record.get("execution_status"),
        "strategy_trace_summary": record.get("strategy_trace_summary"),
        "review_status": record.get("review_status"),
        "quality_flags": list(record.get("quality_flags", []) or []),
        "review_action": str(record.get("review_action", "") or ""),
        "metadata": dict(record.get("metadata") or {}),
    }


def build_sft_record_from_public(record: dict[str, Any]) -> dict[str, Any]:
    oil_payload = dict(record.get("oil") or {})
    prompt_text = build_prompt_text(
        instruction=str(record.get("instruction", "")),
        input_text=str(record.get("input", "")),
        oil_payload=oil_payload,
        system_prompt=DEFAULT_SYSTEM_PROMPT,
    )
    return {
        "id": record["id"],
        "source": record["source"],
        "language": record["language"],
        "task_family": record["task_family"],
        "text": prompt_text + str(record.get("output", "")).strip(),
        "prompt_text": prompt_text,
        "assistant_text": str(record.get("output", "")).strip(),
        "oil": oil_payload,
        "runtime_hints": runtime_hints_from_oil(oil_payload, str(record.get("task_family", "general"))),
        **_common_fields(record),
    }


def build_sft_record_from_curated(record: dict[str, Any]) -> dict[str, Any]:
    prompt_text = build_prompt_text(
        instruction=str(record.get("user_input", "")),
        input_text=str(record.get("context", "")),
        oil_payload=dict(record.get("oil") or {}),
        system_prompt=DEFAULT_SYSTEM_PROMPT,
    )
    return {
        "id": record["id"],
        "source": record["source"],
        "language": record["language"],
        "task_family": record["task_family"],
        "text": prompt_text + str(record.get("assistant_output", "")).strip(),
        "prompt_text": prompt_text,
        "assistant_text": str(record.get("assistant_output", "")).strip(),
        "oil": dict(record.get("oil") or {}),
        "runtime_hints": dict(record.get("runtime_hints") or {}),
        **_common_fields(record),
    }


def filter_sft_records(
    records: list[dict[str, Any]],
    *,
    min_quality_score: float = 0.0,
    allowed_review_statuses: set[str] | None = None,
    source_filters: set[str] | None = None,
    task_family_filters: set[str] | None = None,
) -> list[dict[str, Any]]:
    allowed_review_statuses = {item.lower() for item in (allowed_review_statuses or set()) if str(item).strip()}
    source_filters = {item for item in (source_filters or set()) if str(item).strip()}
    task_family_filters = {item for item in (task_family_filters or set()) if str(item).strip()}
    output: list[dict[str, Any]] = []
    for record in records:
        if float(record.get("quality_score", 0.0) or 0.0) < float(min_quality_score):
            continue
        review_status = str(record.get("review_status", "") or "").strip().lower()
        if allowed_review_statuses and review_status not in allowed_review_statuses:
            continue
        if source_filters and str(record.get("source", "") or "").strip() not in source_filters:
            continue
        if task_family_filters and str(record.get("task_family", "") or "").strip() not in task_family_filters:
            continue
        output.append(record)
    return output


def split_sft_records(
    records: list[dict[str, Any]],
    *,
    train_ratio: float = 0.8,
    validation_ratio: float = 0.1,
) -> dict[str, list[dict[str, Any]]]:
    total = len(records)
    if total == 0:
        return {"train": [], "validation": [], "test": []}
    train_end = max(1, int(total * train_ratio))
    validation_end = train_end + int(total * validation_ratio)
    return {
        "train": records[:train_end],
        "validation": records[train_end:validation_end],
        "test": records[validation_end:],
    }


def build_sft_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    report = {
        "total_records": len(records),
        "by_source": {},
        "by_task_family": {},
        "by_language": {},
        "by_strategy": {},
        "average_quality_score": 0.0,
        "average_sample_weight": 0.0,
    }
    if not records:
        return report
    for record in records:
        source = str(record.get("source", "") or "unknown")
        task_family = str(record.get("task_family", "") or "general")
        language = str(record.get("language", "") or "unknown")
        strategy = str(record.get("selected_strategy", "") or "")
        report["by_source"][source] = int(report["by_source"].get(source, 0)) + 1
        report["by_task_family"][task_family] = int(report["by_task_family"].get(task_family, 0)) + 1
        report["by_language"][language] = int(report["by_language"].get(language, 0)) + 1
        if strategy:
            report["by_strategy"][strategy] = int(report["by_strategy"].get(strategy, 0)) + 1
    report["average_quality_score"] = round(
        sum(float(record.get("quality_score", 0.0) or 0.0) for record in records) / len(records),
        4,
    )
    report["average_sample_weight"] = round(
        sum(float(record.get("sample_weight", 1.0) or 1.0) for record in records) / len(records),
        4,
    )
    return report
