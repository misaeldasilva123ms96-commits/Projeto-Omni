from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from common import detect_language, non_empty_text, read_json, read_jsonl, slugify, utc_now_iso, write_json, write_jsonl


DEFAULT_SYSTEM_PROMPT = "Você é Omni, um runtime cognitivo governado."


def load_normalization_rules(path: Path) -> dict[str, Any]:
    return read_json(path)


def pick_first_text(record: dict[str, Any], fields: list[str]) -> str:
    for field in fields:
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if isinstance(record.get("messages"), list):
        messages = [item for item in record["messages"] if isinstance(item, dict)]
        user_parts = [str(item.get("content", "")).strip() for item in messages if str(item.get("role", "")).lower() in {"user", "human"}]
        assistant_parts = [str(item.get("content", "")).strip() for item in messages if str(item.get("role", "")).lower() in {"assistant", "bot"}]
        if fields and fields[0] in {"instruction", "prompt", "question", "query", "user_input", "task", "title", "text"}:
            return next((part for part in user_parts if part), "")
        if fields and fields[0] in {"output", "response", "answer", "completion", "assistant_output", "chosen"}:
            return next((part for part in assistant_parts if part), "")
    return ""


def infer_task_family(text: str, rules: dict[str, Any]) -> str:
    lowered = str(text or "").lower()
    mapping = dict(rules.get("task_family_keywords", {}) or {})
    for family, keywords in mapping.items():
        if any(str(keyword).lower() in lowered for keyword in keywords):
            return str(family)
    return "general"


def filter_raw_records(records: list[dict[str, Any]], rules: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    kept: list[dict[str, Any]] = []
    discarded = 0
    instruction_fields = list(rules.get("instruction_fields", []))
    output_fields = list(rules.get("output_fields", []))
    output_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in rules.get("drop_if_output_matches", [])]
    for record in records:
        instruction = pick_first_text(record, instruction_fields)
        output = pick_first_text(record, output_fields)
        if not instruction or not output:
            discarded += 1
            continue
        if any(pattern.match(output) for pattern in output_patterns):
            discarded += 1
            continue
        kept.append(record)
    return kept, {
        "total_raw": len(records),
        "total_filtered": len(kept),
        "total_discarded": discarded,
    }


def normalize_record(record: dict[str, Any], *, source: str, rules: dict[str, Any], index: int) -> dict[str, Any]:
    instruction = pick_first_text(record, list(rules.get("instruction_fields", [])))
    input_text = pick_first_text(record, list(rules.get("input_fields", [])))
    output = pick_first_text(record, list(rules.get("output_fields", [])))
    combined_text = " ".join(part for part in (instruction, input_text) if part).strip()
    language = detect_language(combined_text or output)
    quality_flags: list[str] = []
    if language == "unknown":
        quality_flags.append("language_unknown")
    if len(instruction) > int(rules.get("max_instruction_chars", 4000)):
        quality_flags.append("instruction_truncated")
        instruction = instruction[: int(rules.get("max_instruction_chars", 4000))]
    if len(output) > int(rules.get("max_output_chars", 12000)):
        quality_flags.append("output_truncated")
        output = output[: int(rules.get("max_output_chars", 12000))]
    if not input_text:
        quality_flags.append("missing_input")
    task_family = infer_task_family(combined_text or output, rules)
    metadata = {
        "original_keys": sorted(list(record.keys())),
        "normalized_at": utc_now_iso(),
        "source_record_id": str(record.get("id", "") or record.get("uuid", "") or ""),
    }
    return {
        "id": str(record.get("id") or record.get("uuid") or f"{slugify(source)}-{index:06d}"),
        "source": source,
        "language": language,
        "instruction": instruction,
        "input": input_text,
        "output": output,
        "task_family": task_family,
        "quality_flags": quality_flags,
        "metadata": metadata,
    }


def normalize_records(records: list[dict[str, Any]], *, source: str, rules: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    normalized = [normalize_record(record, source=source, rules=rules, index=index) for index, record in enumerate(records, start=1)]
    return normalized, {
        "total_filtered": len(records),
        "total_normalized": len(normalized),
        "total_discarded": 0,
    }


def build_prompt_text(
    *,
    instruction: str,
    input_text: str,
    oil_payload: dict[str, Any],
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
) -> str:
    input_block = input_text.strip() or "(none)"
    return (
        "<|system|>\n"
        f"{system_prompt}\n"
        "<|user|>\n"
        f"INPUT: {instruction.strip()}\n"
        f"CONTEXT: {input_block}\n"
        f"OIL: {json.dumps(oil_payload, ensure_ascii=False)}\n"
        "<|assistant|>\n"
    )


def save_report(path: Path, *, step: str, stats: dict[str, Any], source: str) -> None:
    payload = {
        "step": step,
        "source": source,
        "generated_at": utc_now_iso(),
        "stats": stats,
    }
    write_json(path, payload)


def read_records(path: Path) -> list[dict[str, Any]]:
    return read_jsonl(path)


def write_records(path: Path, records: list[dict[str, Any]]) -> int:
    return write_jsonl(path, records)
