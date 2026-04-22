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
        "quality_score": record.get("quality_score"),
        "sample_weight": record.get("sample_weight"),
        "ambiguity_label": record.get("ambiguity_label"),
        "runtime_value": record.get("runtime_value"),
        "review_priority": record.get("review_priority"),
        "selected_strategy": record.get("selected_strategy"),
        "executor_used": record.get("executor_used"),
        "execution_status": record.get("execution_status"),
        "strategy_trace_summary": record.get("strategy_trace_summary"),
        "metadata": dict(record.get("metadata") or {}),
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
        "quality_score": record.get("quality_score"),
        "sample_weight": record.get("sample_weight"),
        "ambiguity_label": record.get("ambiguity_label"),
        "runtime_value": record.get("runtime_value"),
        "review_priority": record.get("review_priority"),
        "selected_strategy": record.get("selected_strategy"),
        "executor_used": record.get("executor_used"),
        "execution_status": record.get("execution_status"),
        "strategy_trace_summary": record.get("strategy_trace_summary"),
        "metadata": {
            "quality_score": record.get("quality_score"),
            "review_status": record.get("review_status"),
        },
    }
