from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = PROJECT_ROOT / "backend" / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from brain.runtime.error_taxonomy import ERROR_SEVERITY  # noqa: E402
from brain.runtime.learning.redaction import REDACTED_INTERNAL_PAYLOAD, redact_sensitive_text  # noqa: E402


POSITIVE_SCHEMA_VERSION = "omni_training_candidate_v1"
EVAL_SCHEMA_VERSION = "omni_eval_case_v1"

UNSAFE_POSITIVE_MODES = {
    "MATCHER_SHORTCUT",
    "SAFE_FALLBACK",
    "NODE_FALLBACK",
    "PROVIDER_UNAVAILABLE",
    "TOOL_BLOCKED",
}

RAW_KEY_FRAGMENTS = (
    "stack",
    "trace",
    "traceback",
    "stdout",
    "stderr",
    "command",
    "args",
    "argv",
    "env",
    "raw",
    "payload",
    "execution_request",
    "memory_content",
    "memory_raw",
    "provider_raw",
    "tool_raw_result",
    "api_key",
    "token",
    "jwt",
    "secret",
    "password",
    "authorization",
    "bearer",
)

REQUIRED_POSITIVE_FIELDS = {
    "schema_version",
    "id",
    "input",
    "expected_output",
    "runtime_mode",
    "learning_safety",
}

REQUIRED_EVAL_FIELDS = {
    "schema_version",
    "id",
    "input",
    "expected_behavior",
    "case_type",
}


class ValidationError(ValueError):
    pass


def validate_training_candidate(record: Mapping[str, Any], *, positive: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    payload = dict(record or {})
    required = REQUIRED_POSITIVE_FIELDS if positive else REQUIRED_EVAL_FIELDS
    for field in sorted(required):
        if field not in payload:
            errors.append(f"missing_field:{field}")

    if _contains_raw_key(payload):
        errors.append("raw_internal_field_present")
    if _contains_sensitive_text(payload):
        errors.append("sensitive_text_present")

    if positive:
        errors.extend(_validate_positive(payload))
    else:
        if payload.get("schema_version") != EVAL_SCHEMA_VERSION:
            errors.append("invalid_eval_schema_version")

    if errors:
        raise ValidationError(";".join(errors))

    return {"ok": True, "record_id": str(payload.get("id", "")), "positive": positive}


def _validate_positive(payload: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    learning_safety = payload.get("learning_safety") if isinstance(payload.get("learning_safety"), Mapping) else None
    runtime_mode = str(payload.get("runtime_mode", "") or "").strip()
    tool_status = str((learning_safety or {}).get("tool_status", "") or payload.get("tool_status", "") or "").strip().lower()
    governance_status = str((learning_safety or {}).get("governance_status", "") or payload.get("governance_status", "") or "").strip().lower()
    provider_succeeded = (learning_safety or {}).get("provider_succeeded", payload.get("provider_succeeded"))
    fallback_triggered = bool((learning_safety or {}).get("fallback_triggered", payload.get("fallback_triggered", False)))
    error_public_code = str((learning_safety or {}).get("error_public_code", payload.get("error_public_code", "")) or "").strip()
    severity = ERROR_SEVERITY.get(error_public_code, "")

    if payload.get("schema_version") != POSITIVE_SCHEMA_VERSION:
        errors.append("invalid_positive_schema_version")
    if not learning_safety:
        errors.append("missing_learning_safety")
    elif not bool(learning_safety.get("positive_training_candidate")):
        errors.append("learning_safety_not_positive")
    if fallback_triggered:
        errors.append("fallback_positive_rejected")
    if runtime_mode in UNSAFE_POSITIVE_MODES:
        errors.append(f"unsafe_runtime_mode:{runtime_mode}")
    if provider_succeeded is False:
        errors.append("provider_failure_positive_rejected")
    if tool_status in {"failed", "blocked", "denied"}:
        errors.append(f"unsafe_tool_status:{tool_status}")
    if governance_status == "blocked":
        errors.append("governance_block_positive_rejected")
    if severity in {"blocked", "error", "degraded", "critical"}:
        errors.append(f"unsafe_error_severity:{severity}")
    if bool((learning_safety or {}).get("redaction_applied")) and str((learning_safety or {}).get("learning_safety_reason", "")) != "clean_high_confidence_success":
        errors.append("redaction_not_training_quality")
    if not bool(payload.get("user_visible_success", True)):
        errors.append("user_visible_success_required")
    return errors


def _contains_raw_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key or "").lower()
            if any(fragment in normalized for fragment in RAW_KEY_FRAGMENTS):
                return True
            if _contains_raw_key(item):
                return True
    elif isinstance(value, list):
        return any(_contains_raw_key(item) for item in value)
    return False


def _contains_sensitive_text(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_sensitive_text(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_sensitive_text(item) for item in value)
    if isinstance(value, str):
        redacted = redact_sensitive_text(value)
        return redacted != value or REDACTED_INTERNAL_PAYLOAD in value
    return False


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        raw = line.strip()
        if not raw:
            continue
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValidationError(f"line_{line_no}:not_object")
        records.append(payload)
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Omni training candidate or eval JSONL files.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--eval", action="store_true", help="Validate as non-positive eval cases.")
    args = parser.parse_args(argv)

    try:
        records = read_jsonl(args.path)
        for record in records:
            validate_training_candidate(record, positive=not args.eval)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    print(json.dumps({"ok": True, "records": len(records), "positive": not args.eval}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
