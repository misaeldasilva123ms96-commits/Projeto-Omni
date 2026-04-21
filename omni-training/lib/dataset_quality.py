from __future__ import annotations

import hashlib
from typing import Any


REQUIRED_OIL_KEYS = {
    "user_intent",
    "desired_output",
    "urgency",
    "execution_bias",
    "memory_relevance",
}


def _primary_fields(example: dict[str, Any]) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    instruction = str(
        example.get("user_input")
        or example.get("instruction")
        or ""
    ).strip()
    output = str(
        example.get("assistant_output")
        or example.get("output")
        or example.get("assistant_text")
        or ""
    ).strip()
    oil = dict(example.get("oil") or {})
    runtime_hints = dict(example.get("runtime_hints") or {})
    return instruction, output, oil, runtime_hints


def quality_score(example: dict[str, Any]) -> float:
    instruction, output, oil, runtime_hints = _primary_fields(example)
    score = 0.2
    if instruction:
        score += 0.15
    if len(instruction) >= 24:
        score += 0.1
    if output:
        score += 0.15
    if 80 <= len(output) <= 1800:
        score += 0.15
    elif 30 <= len(output) < 80:
        score += 0.05
    if REQUIRED_OIL_KEYS.issubset(set(oil.keys())):
        score += 0.15
    if isinstance(oil.get("entities"), (dict, list)) and isinstance(oil.get("constraints"), (dict, list)):
        score += 0.05
    if {"strategy", "requires_tools", "requires_node_runtime", "fallback_allowed"}.issubset(set(runtime_hints.keys())):
        score += 0.1
    if str(example.get("review_status", "")).strip().lower() == "approved":
        score += 0.05
    if str(example.get("task_family", "")).strip().lower() in {"coding", "planning", "runtime", "governance", "analysis"}:
        score += 0.05
    if "quality_flags" in example and example.get("quality_flags"):
        score -= min(0.1, 0.03 * len(list(example.get("quality_flags") or [])))
    if len(output.split()) < 8:
        score -= 0.15
    return max(0.0, min(1.0, round(score, 4)))


def duplicate_fingerprint(example: dict[str, Any]) -> str:
    instruction, output, _, _ = _primary_fields(example)
    canonical = "||".join(
        [
            instruction.lower(),
            output.lower(),
            str(example.get("task_family", "")).strip().lower(),
        ]
    )
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()


def find_duplicate_groups(records: list[dict[str, Any]]) -> list[list[str]]:
    groups: dict[str, list[str]] = {}
    for index, record in enumerate(records, start=1):
        rid = str(record.get("id", f"record-{index:04d}"))
        groups.setdefault(duplicate_fingerprint(record), []).append(rid)
    return [ids for ids in groups.values() if len(ids) > 1]


def evaluate_dataset_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {
            "record_count": 0,
            "average_quality_score": 0.0,
            "duplicate_group_count": 0,
            "structure_ratio": 0.0,
            "oil_alignment_ratio": 0.0,
            "coherence_ratio": 0.0,
        }
    scores = [quality_score(record) for record in records]
    structure_ok = 0
    oil_ok = 0
    coherence_ok = 0
    for record in records:
        instruction, output, oil, _ = _primary_fields(record)
        if instruction and output:
            structure_ok += 1
        if REQUIRED_OIL_KEYS.issubset(set(oil.keys())):
            oil_ok += 1
        if len(output.split()) >= 8:
            coherence_ok += 1
    duplicates = find_duplicate_groups(records)
    return {
        "record_count": len(records),
        "average_quality_score": round(sum(scores) / len(scores), 4),
        "duplicate_group_count": len(duplicates),
        "structure_ratio": round(structure_ok / len(records), 4),
        "oil_alignment_ratio": round(oil_ok / len(records), 4),
        "coherence_ratio": round(coherence_ok / len(records), 4),
    }

