"""
export_training_candidates.py — Phase 13 (Roadmap Oficial v2.1)

Exports records from the learning store that qualify as positive training candidates.
All records pass through the Phase 9 safety filter before export.

Usage:
    python scripts/export_training_candidates.py --output data/exports/candidates.jsonl
    python scripts/export_training_candidates.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend" / "python"))

_ALLOWED_RUNTIME_MODES = {
    "FULL_COGNITIVE_RUNTIME",
    "NODE_EXECUTION_SUCCESS",
    "LOCAL_TOOL_SUCCESS",
    "DIRECT_LOCAL_RESPONSE",
}

_EXCLUDED_RUNTIME_MODES = {
    "MATCHER_SHORTCUT",
    "SAFE_FALLBACK",
    "RULE_BASED_INTENT",
}


def _is_positive_candidate(record: dict) -> bool:
    """Phase 9 safety filter — returns True only if record is safe for training."""
    if record.get("fallback_triggered"):
        return False
    if record.get("runtime_mode") in _EXCLUDED_RUNTIME_MODES:
        return False
    if record.get("provider_succeeded") is False:
        return False
    if record.get("tool_status") in {"failed", "blocked"}:
        return False
    if record.get("governance_status") == "blocked":
        return False
    if not record.get("no_pii_detected", True):
        return False
    if record.get("runtime_mode") not in _ALLOWED_RUNTIME_MODES:
        return False
    return True


def _strip_sensitive_fields(record: dict) -> dict:
    """Remove any fields that must not appear in exported training data."""
    blocked = {"raw_input", "raw_output", "user_id", "session_id", "ip", "token", "key"}
    return {k: v for k, v in record.items() if k not in blocked}


def export_candidates(
    source_path: Path,
    output_path: Path | None,
    dry_run: bool = False,
) -> int:
    """Read source JSONL, filter, and write candidates. Returns count exported."""
    if not source_path.exists():
        print(f"[ERROR] Source file not found: {source_path}", file=sys.stderr)
        return 0

    candidates = []
    skipped = 0

    with open(source_path) as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[WARN] Line {line_no}: JSON parse error — {e}", file=sys.stderr)
                skipped += 1
                continue

            if _is_positive_candidate(record):
                candidates.append(_strip_sensitive_fields(record))
            else:
                skipped += 1

    print(f"[INFO] Total records read: {line_no}")
    print(f"[INFO] Candidates (positive): {len(candidates)}")
    print(f"[INFO] Skipped (unsafe/excluded): {skipped}")

    if dry_run:
        print("[DRY-RUN] No file written.")
        return len(candidates)

    if output_path is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_path = ROOT / "data" / "exports" / f"training_candidates_{ts}.jsonl"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for record in candidates:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"[INFO] Exported to: {output_path}")
    return len(candidates)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export positive training candidates")
    parser.add_argument("--source", default="data/learning/records.jsonl",
                        help="Source JSONL file with learning records")
    parser.add_argument("--output", default=None,
                        help="Output JSONL file (default: auto-timestamped in data/exports/)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Count candidates without writing output file")
    args = parser.parse_args()

    source = ROOT / args.source
    output = Path(args.output) if args.output else None
    count = export_candidates(source, output, dry_run=args.dry_run)
    sys.exit(0 if count >= 0 else 1)


if __name__ == "__main__":
    main()
