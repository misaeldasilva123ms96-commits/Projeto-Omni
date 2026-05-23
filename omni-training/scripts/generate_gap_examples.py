from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from common import write_json, write_jsonl  # noqa: E402
from synthetic_examples import generate_synthetic_examples  # noqa: E402
from training_utils import resolve_training_path  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate controlled synthetic examples for known dataset gaps.")
    parser.add_argument("--category", default="fallback_cases")
    parser.add_argument("--limit", type=int, default=16)
    parser.add_argument("--output", default=str(Path(__file__).resolve().parents[1] / "data" / "review_queue" / "gap_examples.jsonl"))
    parser.add_argument("--report", default=str(Path(__file__).resolve().parents[1] / "reports" / "gap_examples_report.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = generate_synthetic_examples(category=str(args.category), limit=max(1, int(args.limit)))
    output_path = resolve_training_path(args.output)
    report_path = resolve_training_path(args.report)
    write_jsonl(output_path, records)
    report = {
        "category": str(args.category),
        "record_count": len(records),
        "output_path": str(output_path),
        "all_sources_controlled": all(str(item.get("source", "") or "") == "synthetic_controlled" for item in records),
    }
    write_json(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
