from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = PROJECT_ROOT / "backend" / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from brain.runtime.learning.learning_safety import build_learning_safety_metadata  # noqa: E402
from brain.runtime.learning.redaction import redact_sensitive_payload  # noqa: E402

from validate_training_candidate import (  # noqa: E402
    EVAL_SCHEMA_VERSION,
    POSITIVE_SCHEMA_VERSION,
    ValidationError,
    validate_training_candidate,
)


def default_source_path(root: Path) -> Path:
    return root / ".logs" / "fusion-runtime" / "learning" / "controlled" / "learning_records.jsonl"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def build_positive_candidate(record: dict[str, Any]) -> dict[str, Any] | None:
    sanitized = redact_sensitive_payload(record)
    safety = dict(sanitized.get("learning_safety") or build_learning_safety_metadata(sanitized))
    sanitized["learning_safety"] = safety
    if not bool(safety.get("positive_training_candidate")):
        return None

    candidate = {
        "schema_version": POSITIVE_SCHEMA_VERSION,
        "id": str(sanitized.get("record_id", "") or ""),
        "source": "controlled_learning_record",
        "input": str(sanitized.get("input_preview", "") or ""),
        "expected_output": str(sanitized.get("notes", "") or ""),
        "runtime_mode": str(sanitized.get("runtime_mode", "") or ""),
        "selected_strategy": str(sanitized.get("selected_strategy", "") or ""),
        "selected_tool": str(sanitized.get("selected_tool", "") or ""),
        "user_visible_success": bool(sanitized.get("success", False)),
        "learning_safety": safety,
        "metadata": {
            "execution_path": str(sanitized.get("execution_path", "") or ""),
            "provider_actual": str(sanitized.get("provider_actual", "") or ""),
        },
    }
    validate_training_candidate(candidate, positive=True)
    return candidate


def build_eval_case(record: dict[str, Any]) -> dict[str, Any] | None:
    sanitized = redact_sensitive_payload(record)
    safety = dict(sanitized.get("learning_safety") or build_learning_safety_metadata(sanitized))
    classification = str(safety.get("learning_classification", "") or "")
    if classification == "positive_training_candidate":
        return None

    case_type = {
        "failure_memory": "runtime_truth_eval_case",
        "routing_eval_case": "routing_eval_case",
        "tool_failure_case": "safety_eval_case",
        "governance_block_case": "governance_eval_case",
    }.get(classification, "diagnostic_memory")
    case = {
        "schema_version": EVAL_SCHEMA_VERSION,
        "id": str(sanitized.get("record_id", "") or ""),
        "source": "controlled_learning_record",
        "case_type": case_type,
        "input": str(sanitized.get("input_preview", "") or ""),
        "expected_behavior": str(safety.get("learning_safety_reason", "preserve diagnostic classification") or ""),
        "runtime_mode": str(sanitized.get("runtime_mode", "") or ""),
        "learning_safety": safety,
    }
    validate_training_candidate(case, positive=False)
    return case


def export_candidates(source: Path, *, positive_output: Path | None = None, eval_output: Path | None = None, write: bool = False) -> dict[str, Any]:
    records = read_jsonl(source)
    positives: list[dict[str, Any]] = []
    eval_cases: list[dict[str, Any]] = []
    rejected = 0

    for record in records:
        try:
            positive = build_positive_candidate(record)
            if positive:
                positives.append(positive)
                continue
            eval_case = build_eval_case(record)
            if eval_case:
                eval_cases.append(eval_case)
            else:
                rejected += 1
        except ValidationError:
            rejected += 1

    if write:
        if positive_output:
            _write_jsonl(positive_output, positives)
        if eval_output:
            _write_jsonl(eval_output, eval_cases)

    return {
        "ok": True,
        "dry_run": not write,
        "source": str(source),
        "records_read": len(records),
        "positive_candidates": len(positives),
        "eval_cases": len(eval_cases),
        "rejected": rejected,
        "positive_output": str(positive_output) if positive_output else "",
        "eval_output": str(eval_output) if eval_output else "",
    }


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dry-run safe Omni training candidate export.")
    parser.add_argument("--source", type=Path, default=default_source_path(PROJECT_ROOT))
    parser.add_argument("--positive-output", type=Path)
    parser.add_argument("--eval-output", type=Path)
    parser.add_argument("--write", action="store_true", help="Write validated JSONL outputs. Default is dry-run.")
    args = parser.parse_args(argv)

    summary = export_candidates(
        args.source,
        positive_output=args.positive_output,
        eval_output=args.eval_output,
        write=args.write,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
