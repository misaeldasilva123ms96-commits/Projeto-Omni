from __future__ import annotations

import hashlib
import re
from typing import Any


REQUIRED_OIL_KEYS = {
    "user_intent",
    "desired_output",
    "urgency",
    "execution_bias",
    "memory_relevance",
}
GENERIC_PATTERNS = (
    "depende do contexto",
    "sem mais detalhes",
    "não tenho informação suficiente",
    "it depends",
    "more context is needed",
)


def _primary_fields(example: dict[str, Any]) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    instruction = str(example.get("user_input") or example.get("instruction") or "").strip()
    output = str(example.get("assistant_output") or example.get("output") or example.get("assistant_text") or "").strip()
    oil = dict(example.get("oil") or {})
    runtime_hints = dict(example.get("runtime_hints") or {})
    return instruction, output, oil, runtime_hints


def duplicate_fingerprint(example: dict[str, Any]) -> str:
    instruction, output, _, _ = _primary_fields(example)
    canonical = "||".join(
        [
            re.sub(r"\s+", " ", instruction.lower()),
            re.sub(r"\s+", " ", output.lower()),
            str(example.get("task_family", "")).strip().lower(),
        ]
    )
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()


def quality_assessment(example: dict[str, Any]) -> dict[str, Any]:
    instruction, output, oil, runtime_hints = _primary_fields(example)
    flags: list[str] = []
    positive_flags: list[str] = []
    score = 0.15
    output_lower = output.lower()
    task_family = str(example.get("task_family", "") or "").strip().lower()
    review_status = str(example.get("review_status", "") or "").strip().lower()
    if instruction:
        score += 0.12
        positive_flags.append("has_instruction")
    else:
        flags.append("missing_instruction")
    if len(instruction) >= 24:
        score += 0.08
        positive_flags.append("instruction_has_context")
    if output:
        score += 0.12
        positive_flags.append("has_output")
    else:
        flags.append("missing_output")
    output_word_count = len(output.split())
    if output_word_count < 8:
        score -= 0.18
        flags.append("output_too_short")
    elif output_word_count < 20:
        score -= 0.05
        flags.append("output_somewhat_short")
    elif 20 <= output_word_count <= 280:
        score += 0.12
        positive_flags.append("good_output_length")
    else:
        score += 0.05
    if REQUIRED_OIL_KEYS.issubset(set(oil.keys())):
        score += 0.14
        positive_flags.append("oil_complete")
    else:
        flags.append("oil_incomplete")
    if isinstance(oil.get("entities"), (dict, list)) and isinstance(oil.get("constraints"), (dict, list)):
        score += 0.04
    else:
        flags.append("oil_structure_weak")
    required_runtime = {"strategy", "requires_tools", "requires_node_runtime", "fallback_allowed"}
    if required_runtime.issubset(set(runtime_hints.keys())):
        score += 0.08
        positive_flags.append("runtime_hints_complete")
    else:
        flags.append("runtime_hints_incomplete")
    if task_family in {"coding", "planning", "runtime", "governance", "analysis"}:
        score += 0.06
        positive_flags.append("runtime_relevant")
    runtime_value = str(example.get("runtime_value", "") or "").strip().lower()
    if runtime_value == "high":
        score += 0.06
    if review_status == "approved":
        score += 0.06
        positive_flags.append("approved_example")
    elif review_status in {"draft", "weak"}:
        flags.append("needs_review")
    if any(pattern in output_lower for pattern in GENERIC_PATTERNS):
        score -= 0.15
        flags.append("generic_answer_risk")
    if instruction and output and instruction.lower() == output.lower():
        score -= 0.12
        flags.append("instruction_output_overlap")
    if instruction and output and len(set(instruction.lower().split()) & set(output_lower.split())) <= 1:
        flags.append("weak_input_output_link")
        score -= 0.08
    if bool(example.get("candidate_strategies")) and str(example.get("selected_strategy", "")).strip():
        score += 0.08
        positive_flags.append("ambiguity_resolution_present")
    if str(example.get("execution_status", "")).strip().lower() in {"fallback", "blocked", "error"}:
        flags.append("degraded_execution_case")
        score -= 0.04
    if example.get("quality_flags"):
        flags.extend([str(flag) for flag in list(example.get("quality_flags") or []) if str(flag).strip()])
        score -= min(0.1, 0.02 * len(list(example.get("quality_flags") or [])))

    score = max(0.0, min(1.0, round(score, 4)))
    unique_flags = list(dict.fromkeys(positive_flags + flags))
    if score < 0.45 or "missing_output" in unique_flags or "missing_instruction" in unique_flags:
        review_action = "reject"
    elif score < 0.72 or "generic_answer_risk" in unique_flags or "needs_review" in unique_flags:
        review_action = "review"
    else:
        review_action = "keep"
    return {
        "quality_score": score,
        "quality_flags": unique_flags,
        "review_action": review_action,
    }


def quality_score(example: dict[str, Any]) -> float:
    return float(quality_assessment(example)["quality_score"])


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
            "keep_ratio": 0.0,
            "review_ratio": 0.0,
            "reject_ratio": 0.0,
        }
    assessments = [quality_assessment(record) for record in records]
    duplicates = find_duplicate_groups(records)
    structure_ok = 0
    oil_ok = 0
    coherence_ok = 0
    keep_count = 0
    review_count = 0
    reject_count = 0
    for record, assessment in zip(records, assessments):
        instruction, output, oil, _ = _primary_fields(record)
        if instruction and output:
            structure_ok += 1
        if REQUIRED_OIL_KEYS.issubset(set(oil.keys())):
            oil_ok += 1
        if len(output.split()) >= 8:
            coherence_ok += 1
        if assessment["review_action"] == "keep":
            keep_count += 1
        elif assessment["review_action"] == "review":
            review_count += 1
        else:
            reject_count += 1
    return {
        "record_count": len(records),
        "average_quality_score": round(sum(item["quality_score"] for item in assessments) / len(assessments), 4),
        "duplicate_group_count": len(duplicates),
        "structure_ratio": round(structure_ok / len(records), 4),
        "oil_alignment_ratio": round(oil_ok / len(records), 4),
        "coherence_ratio": round(coherence_ok / len(records), 4),
        "keep_ratio": round(keep_count / len(records), 4),
        "review_ratio": round(review_count / len(records), 4),
        "reject_ratio": round(reject_count / len(records), 4),
    }
