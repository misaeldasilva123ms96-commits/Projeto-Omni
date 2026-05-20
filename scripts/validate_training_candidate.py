"""
validate_training_candidate.py — Phase 13 (Roadmap Oficial v2.1)

Validates individual training candidate records against the schema and safety rules.
Use this before ingesting any record into a training pipeline.

Usage:
    python scripts/validate_training_candidate.py --record '{"id": "...", ...}'
    python scripts/validate_training_candidate.py --file data/exports/candidates.jsonl
    python scripts/validate_training_candidate.py --file data/exports/candidates.jsonl --strict
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REQUIRED_FIELDS = [
    "id",
    "runtime_mode",
    "provider_succeeded",
    "fallback_triggered",
    "no_pii_detected",
    "governance_status",
    "user_visible_success",
    "classification",
]

_ALLOWED_CLASSIFICATIONS = {
    "training_candidate",
    "failure_memory",
    "diagnostic_event",
    "routing_eval_case",
}

_POSITIVE_ONLY_RUNTIME_MODES = {
    "FULL_COGNITIVE_RUNTIME",
    "NODE_EXECUTION_SUCCESS",
    "LOCAL_TOOL_SUCCESS",
    "DIRECT_LOCAL_RESPONSE",
}

_BLOCKED_RUNTIME_MODES_FOR_POSITIVE = {
    "MATCHER_SHORTCUT",
    "SAFE_FALLBACK",
    "RULE_BASED_INTENT",
}

_FORBIDDEN_FIELDS = {"raw_input", "raw_output", "token", "key", "password", "secret"}


def validate(record: dict, strict: bool = False) -> list[str]:
    """Return list of validation errors. Empty list = valid."""
    errors: list[str] = []

    # Required fields
    for field in _REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"Missing required field: {field}")

    # Classification
    classification = record.get("classification", "")
    if classification not in _ALLOWED_CLASSIFICATIONS:
        errors.append(f"Invalid classification: {classification!r}. Must be one of {_ALLOWED_CLASSIFICATIONS}")

    # Positive training safety rules
    if classification == "training_candidate":
        if record.get("fallback_triggered"):
            errors.append("training_candidate must have fallback_triggered=false")
        if not record.get("provider_succeeded"):
            errors.append("training_candidate must have provider_succeeded=true")
        if not record.get("no_pii_detected"):
            errors.append("training_candidate must have no_pii_detected=true")
        if record.get("governance_status") != "allowed":
            errors.append("training_candidate must have governance_status=allowed")
        if not record.get("user_visible_success"):
            errors.append("training_candidate must have user_visible_success=true")
        runtime_mode = record.get("runtime_mode", "")
        if runtime_mode in _BLOCKED_RUNTIME_MODES_FOR_POSITIVE:
            errors.append(
                f"training_candidate cannot have runtime_mode={runtime_mode!r}. "
                f"These modes are excluded from positive training."
            )
        if strict and runtime_mode not in _POSITIVE_ONLY_RUNTIME_MODES:
            errors.append(
                f"[strict] training_candidate runtime_mode {runtime_mode!r} is not in "
                f"the explicit allowlist {_POSITIVE_ONLY_RUNTIME_MODES}"
            )

    # Forbidden sensitive fields
    for field in _FORBIDDEN_FIELDS:
        if field in record:
            errors.append(f"Forbidden sensitive field present: {field!r}")

    return errors


def validate_file(path: Path, strict: bool = False) -> tuple[int, int, int]:
    """Validate all records in a JSONL file. Returns (total, valid, invalid)."""
    total = valid = invalid = 0
    with open(path) as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Line {line_no}: JSON error — {e}", file=sys.stderr)
                invalid += 1
                continue

            errors = validate(record, strict=strict)
            if errors:
                record_id = record.get("id", f"line-{line_no}")
                print(f"[INVALID] {record_id}:")
                for err in errors:
                    print(f"  - {err}")
                invalid += 1
            else:
                valid += 1

    return total, valid, invalid


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate training candidate records")
    parser.add_argument("--record", help="JSON string of a single record to validate")
    parser.add_argument("--file", help="JSONL file of records to validate")
    parser.add_argument("--strict", action="store_true",
                        help="Enable strict runtime_mode allowlist check")
    args = parser.parse_args()

    if args.record:
        try:
            record = json.loads(args.record)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON: {e}", file=sys.stderr)
            sys.exit(1)
        errors = validate(record, strict=args.strict)
        if errors:
            print("[INVALID]")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)
        else:
            print("[VALID]")
            sys.exit(0)

    elif args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"[ERROR] File not found: {path}", file=sys.stderr)
            sys.exit(1)
        total, valid, invalid = validate_file(path, strict=args.strict)
        print(f"\nTotal: {total} | Valid: {valid} | Invalid: {invalid}")
        sys.exit(0 if invalid == 0 else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
